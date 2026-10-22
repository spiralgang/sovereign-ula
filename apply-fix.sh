#!/usr/bin/env bash
set -euo pipefail
ROOT="$(pwd)"
BRANCH="${1:-agent/repo-repair}"

echo "Applying Sovereign-ULA fixes into working tree (branch: $BRANCH)..."

git fetch origin
git checkout -B "$BRANCH"

# Write files (here we assume this script sits at repo root and that it contains
# embedded file blobs. For convenience we'll dump the files from a 'files' dir
# that you create by extracting from the zip or by copying from this message.)
# If you saved the patches into ./patches, copy them into place:
if [ -d "./patches" ]; then
  cp -r ./patches/. .
fi

# If the repository already has the target files, replace them; otherwise add
git add -A
git commit -m "repair: workflows, bootstrap, wifi/connectivity" || echo "No changes to commit"

echo "Run validation checks..."
python3 -m py_compile .github/scripts/ai_review.py || {
  echo "python compile failed; inspect .github/scripts/ai_review.py"
  exit 2
}
echo "Python OK"

echo "You can now push and open a PR:"
echo "  git push -u origin $BRANCH"
echo "  gh pr create --fill --title 'repair: workflows, bootstrap, wifi/connectivity' --body 'Auto-applied deterministic fixes (worker) — see commit.'"

echo "Done."
