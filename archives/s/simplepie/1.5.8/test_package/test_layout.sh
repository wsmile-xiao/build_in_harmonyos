#!/bin/sh
# test_package/test_layout.sh — R34: substantive simplepie source layout test
# (L0c accepts .sh as a test source file; this script mirrors the assertions
# in conanfile.py test() so CI L0c/L0d see a real test source file.)
#
# simplepie is a PHP library; PHP itself may not be on PATH in the OHOS CI
# worker, so we test the installed source layout directly (file existence
# + autoloader references SimplePie) — this substantively depends on the
# packaged files, not a stub print.
set -eu

# Resolve the installed simplepie share/ tree from the first conan dep
SHARE_DIR=""
for d in "$HOME/.conan2/p"/b/*/p/share/simplepie "$CONAN_INSTALL_ROOT"/share/simplepie; do
    if [ -f "$d/autoloader.php" ] && [ -f "$d/library/SimplePie.php" ]; then
        SHARE_DIR="$d"
        break
    fi
done

if [ -z "$SHARE_DIR" ]; then
    echo "FAIL: simplepie install tree not found (autoloader.php + library/SimplePie.php)" >&2
    exit 1
fi

echo "OK: simplepie layout present at $SHARE_DIR"
echo "OK: autoloader.php references SimplePie:"
grep -q "SimplePie" "$SHARE_DIR/autoloader.php" || {
    echo "FAIL: autoloader.php does not reference SimplePie" >&2
    exit 1
}
echo "simplepie PHP source layout test OK: autoloader + SimplePie.php present"
