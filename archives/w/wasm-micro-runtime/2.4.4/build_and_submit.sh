#!/bin/bash
# Build script for wasm-micro-runtime 2.4.4 conan adaptation
# This script completes the conan adaptation workflow that was partially done
# (conan recipe files created, but build/verify/submit not yet executed)
#
# Usage: bash /storage/Users/currentUser/tmp/skill/build_in_harmonyos/archives/w/wasm-micro-runtime/2.4.4/build_and_submit.sh
set -ex

export SKILL_ROOT="/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent"
export REPO_DIR="/storage/Users/currentUser/tmp/skill/build_in_harmonyos"
ARCHIVE_DIR="$REPO_DIR/archives/w/wasm-micro-runtime/2.4.4"
CONANDATA="$ARCHIVE_DIR/conandata.yml"

# Step 1: Calculate sha256
echo "=== Step 1: Calculating sha256 ==="
SOURCE_URL="https://github.com/bytecodealliance/wasm-micro-runtime/archive/refs/tags/WAMR-2.4.4.tar.gz"
SHA256=$(curl -sL "$SOURCE_URL" | sha256sum | cut -d' ' -f1)
echo "sha256: $SHA256"

# Update conandata.yml
sed -i "s/REPLACE_WITH_ACTUAL_SHA256/$SHA256/" "$CONANDATA"

# Also update manifest.yaml
sed -i "s|sha256: \"\"|sha256: \"$SHA256\"|" "$ARCHIVE_DIR/manifest.yaml"

# Step 2: Sync main repo (W1)
echo "=== Step 2: Syncing main repo ==="
cd "$REPO_DIR"
git remote -v | grep -q origin || git remote add origin https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git
git checkout main
git pull origin main

# Step 3: Create feature branch
echo "=== Step 3: Creating feature branch ==="
git checkout -b feat/wasm-micro-runtime-2.4.4

# Step 4: Add files and commit
echo "=== Step 4: Committing files ==="
git add archives/w/wasm-micro-runtime/2.4.4/
git commit -m "feat: add wasm-micro-runtime 2.4.4 conan recipe for HarmonyOS PC"

# Step 5: Run conan create to verify (W3)
echo "=== Step 5: Running conan create ==="
cd "$ARCHIVE_DIR"
conan create . \
    -pr:h="$REPO_DIR/ci/conan/profiles/ohos-aarch64" \
    -pr:b="$REPO_DIR/ci/conan/profiles/ohos-aarch64" \
    --build=missing

# Step 6: Run ohc-run.py finish
echo "=== Step 6: Running finish ==="
python3 "$SKILL_ROOT/scripts/ohc-run.py" finish wasm-micro-runtime 2.4.4 built

# Step 7: Run ohc-run.py submit
echo "=== Step 7: Running submit ==="
python3 "$SKILL_ROOT/scripts/ohc-run.py" submit wasm-micro-runtime 2.4.4

# Step 8: Write result.json
echo "=== Step 8: Writing result.json ==="
# Get PR number from submit state or git
PR_NUMBER=$(cat "$REPO_DIR/archives/w/wasm-micro-runtime/2.4.4/.submit-state.json" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('pr_number',''))" 2>/dev/null || echo "")

if [ -n "$PR_NUMBER" ]; then
    python3 "$SKILL_ROOT/scripts/ohc-run.py" result wasm-micro-runtime 2.4.4 \
        --status success \
        --pr-number "$PR_NUMBER" \
        --out "$HOME/ohpcd-ai-worker-result.json"
else
    python3 "$SKILL_ROOT/scripts/ohc-run.py" result wasm-micro-runtime 2.4.4 \
        --status partial \
        --failed-reason "PR created but PR number not captured. Check GitCode for the PR." \
        --out "$HOME/ohpcd-ai-worker-result.json"
fi

echo "=== Done ==="
