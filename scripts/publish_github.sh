#!/usr/bin/env bash
# Run in an environment with GitHub CLI installed and already authenticated.
# Creates a PRIVATE repository, pushes code/tables/notebooks, and uploads MRI
# ZIP parts as Release assets. No password or token is stored in this script.
set -euo pipefail
repo_name="${1:-BTomoto/rn-mri-clinical-fusion}"
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
command -v gh >/dev/null || { echo 'Install the official GitHub CLI and authenticate first.'; exit 1; }
gh auth status
if [[ ! -d .git ]]; then
  git init -b main
fi
git add --all
if ! git diff --cached --quiet; then
  git commit -m 'Add public MRI data acquisition, curated tables and executed notebooks'
fi
if gh repo view "$repo_name" >/dev/null 2>&1; then
  if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "https://github.com/${repo_name}.git"
  fi
  git push -u origin HEAD
else
  gh repo create "$repo_name" --private --source . --remote origin --push
fi
shopt -s nullglob
parts=(dist/RN_MRI_part_*.zip)
if (( ${#parts[@]} )); then
  if gh release view data-v0.1 --repo "$repo_name" >/dev/null 2>&1; then
    gh release upload data-v0.1 "${parts[@]}" --repo "$repo_name"
  else
    gh release create data-v0.1 "${parts[@]}" --repo "$repo_name" \
      --title 'Public MRI source data v0.1' --notes-file reports/release_notes.md
  fi
fi
echo "Published repository: $repo_name"
