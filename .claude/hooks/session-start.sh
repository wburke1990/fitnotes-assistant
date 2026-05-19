#!/usr/bin/env bash
# SessionStart hook — runs once per Claude session.
#
# Always: wires up core.hooksPath so the project's pre-commit hook fires.
#
# Cloud sessions only: also installs the optional system binaries the
# pre-commit hook expects (gitleaks for secret scanning, shellcheck for
# hook linting) and pre-warms the uv venv. On local machines (Mac/Linux
# workstations), install these yourself — `brew install gitleaks shellcheck`
# or `apt-get install shellcheck` plus the gitleaks release binary.
#
# Idempotent: skips installs that have already succeeded in this container.
# Tolerant: install failures log a warning but do not block the session.

set -u

# Always-on: hook path wiring. Cheap and required for commits to be guarded.
git config core.hooksPath .githooks

# Skip the rest on local machines — apt-get and the Linux gitleaks tarball
# won't work outside the cloud sandbox.
if [[ "${CLAUDE_CODE_REMOTE:-}" != "true" ]]; then
    exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
GITLEAKS_VERSION="8.21.2"

install_gitleaks() {
    if command -v gitleaks >/dev/null 2>&1; then
        return 0
    fi
    local tarball=/tmp/gitleaks.tgz
    if curl -sfL --max-time 30 \
        "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
        -o "$tarball" \
        && tar -xzf "$tarball" -C /tmp gitleaks \
        && mv /tmp/gitleaks /usr/local/bin/gitleaks; then
        rm -f "$tarball"
        return 0
    fi
    rm -f "$tarball"
    return 1
}

install_shellcheck() {
    if command -v shellcheck >/dev/null 2>&1; then
        return 0
    fi
    apt-get install -y -qq shellcheck >/dev/null 2>&1
}

# Pre-warm the uv venv so the pre-commit hook doesn't pay sync cost on the
# first commit of the session.
warm_uv() {
    uv --directory "$PROJECT_DIR/scripts" sync --quiet
}

install_gitleaks || echo "session-start: gitleaks install failed (continuing)" >&2
install_shellcheck || echo "session-start: shellcheck install failed (continuing)" >&2
warm_uv || echo "session-start: uv sync failed (continuing)" >&2

exit 0
