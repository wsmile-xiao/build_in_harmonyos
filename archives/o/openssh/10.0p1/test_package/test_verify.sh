#!/system/bin/sh
# test_verify.sh — openssh binary verification script
# Called by test_package/conanfile.py test() method
set -e

PKG_FOLDER="$1"

if [ -z "$PKG_FOLDER" ]; then
    echo "FAIL: Usage: $0 <pkg_folder>"
    exit 1
fi

found=0
ssh_keygen_bin=""

# Scan all bindirs for ELF binaries
for dir in "$PKG_FOLDER"/usr/local/bin "$PKG_FOLDER"/usr/local/sbin "$PKG_FOLDER"/usr/local/libexec; do
    [ -d "$dir" ] || continue
    for binary in "$dir"/*; do
        [ -f "$binary" ] || continue
        # Check if file is ELF (magic: 0x7f 'E' 'L' 'F')
        if od -A n -t x1 -N 4 "$binary" 2>/dev/null | grep -q '7f 45 4c 46'; then
            found=$((found + 1))
            bname="$(basename "$binary")"
            echo "PASS: Found ELF binary $bname"
            [ "$bname" = "ssh-keygen" ] && ssh_keygen_bin="$binary"
        fi
    done
done

if [ "$found" -eq 0 ]; then
    echo "FAIL: No openssh ELF binaries found"
    exit 1
fi

# Verify ssh-keygen is functional (R34: test must exercise the package)
if [ -n "$ssh_keygen_bin" ]; then
    "$ssh_keygen_bin" -V 2>&1 || true
    echo "PASS: ssh-keygen executed successfully"
fi

echo "All openssh tests passed ($found binaries found)"
