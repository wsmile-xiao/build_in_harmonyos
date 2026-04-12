#!/bin/sh
# fix_config_h_post.sh - Post-process config.h for HarmonyOS platform
#
# Applies platform-specific fixes to generated config.h:
#   1. Disable I_SHADOW (system shadow.h lacks getspnam declaration)
#   2. Disable HAS_GETSPNAM (same reason)
#   3. Keep MYMALLOC disabled (use system malloc, MYMALLOC crashes)

set -e

FILE="$1"
if [ -z "$FILE" ]; then
    echo "Usage: $0 <config.h_path>"
    exit 1
fi

if [ ! -f "$FILE" ]; then
    echo "Error: $FILE not found"
    exit 1
fi

changes=0

# Fix 1: Comment out I_SHADOW (define with empty value → commented out)
# Pattern: #define I_SHADOW		/**/
if grep -q '^#define I_SHADOW[[:space:]]' "$FILE"; then
    sed -i 's|^#define I_SHADOW[[:space:]]*\(.*\)$|/*#define I_SHADOW	\1 */|' "$FILE"
    changes=$((changes + 1))
    echo "  [FIX] Disabled I_SHADOW (shadow.h incomplete on this platform)"
fi

# Fix 2: Comment out HAS_GETSPNAM
if grep -q '^#define HAS_GETSPNAM[[:space:]]' "$FILE"; then
    sed -i 's|^#define HAS_GETSPNAM[[:space:]]*\(.*\)$|/*#define HAS_GETSPNAM	\1 */|' "$FILE"
    changes=$((changes + 1))
    echo "  [FIX] Disabled HAS_GETSPNAM (getspnam not in system headers)"
fi

echo "Applied $changes platform fixes to $FILE"
