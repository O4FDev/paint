#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")/.."
[ "${MINYAR_CONFIRM_PUBLISH:-}" = github.com/O4FDev/paint ] || {
    echo 'Set MINYAR_CONFIRM_PUBLISH=github.com/O4FDev/paint to create and publish this repository.' >&2
    exit 2
}
[ -z "$(git status --porcelain)" ] || { echo 'Commit the working tree before publishing.' >&2; exit 2; }
[ "$(git rev-parse v0.1.0)" = "$(git rev-parse HEAD)" ] || { echo 'HEAD must be the reviewed v0.1.0 release.' >&2; exit 2; }
gh repo create O4FDev/paint --public --source . --remote origin
git push --set-upstream origin main --tags
