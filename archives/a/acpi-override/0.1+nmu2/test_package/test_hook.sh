#!/bin/sh
set -eu

# Locate the packaged hook: prefer an explicit ACPI_OVERRIDE_HOOK, then
# search the Conan package cache, then fall back to a sibling layout.
if [ -n "${ACPI_OVERRIDE_HOOK:-}" ]; then
    hook="$ACPI_OVERRIDE_HOOK"
else
    conan_home="${CONAN_HOME:-}"
    if [ -n "$conan_home" ] && [ -d "$conan_home/p/b" ]; then
        hook=$(find "$conan_home/p/b" -path '*/share/initramfs-tools/hooks/acpi-override' -type f 2>/dev/null | head -1)
    else
        hook=""
    fi
    if [ -z "$hook" ]; then
        hook="$(cd "$(dirname "$0")" && pwd)/../share/initramfs-tools/hooks/acpi-override"
    fi
fi

test -f "$hook" || { echo "acpi-override hook not found at $hook" >&2; exit 1; }
sh "$hook" prereqs

# Exercise the packaged hook's normal path with initramfs-tools and cpio
# replaced by deterministic test doubles. This asserts that an ACPI table is
# staged at the kernel-recognized path and passed to early-initramfs handling.
test_root="${TMPDIR:-/tmp}/acpi-override-test-$$"
suffix=0
while ! mkdir "$test_root" 2>/dev/null; do
    suffix=$((suffix + 1))
    test_root="${TMPDIR:-/tmp}/acpi-override-test-$$-$suffix"
done
cleanup() { rm -rf "$test_root"; }
trap cleanup EXIT HUP INT TERM

override_dir="$test_root/override"
fake_bin="$test_root/bin"
mock_functions="$test_root/hook-functions"
mock_hook="$test_root/acpi-override"
table_list="$test_root/cpio-files.txt"
early_image="$test_root/early-initramfs.cpio"
mkdir -p "$override_dir" "$fake_bin"
printf 'test ACPI table\n' > "$override_dir/table.aml"

cat > "$mock_functions" <<'EOF'
prepend_earlyinitramfs() {
    test -s "$1"
    cp "$1" "$ACPI_OVERRIDE_TEST_EARLY_IMAGE"
}
EOF

cat > "$fake_bin/cpio" <<'EOF'
#!/bin/sh
cat > "$ACPI_OVERRIDE_TEST_FILE_LIST"
printf 'mock-cpio-image\n'
EOF
chmod +x "$fake_bin/cpio"

sed -e "s|/usr/share/initramfs-tools/hook-functions|$mock_functions|" \
    -e "s|/var/lib/acpi-override|$override_dir|g" \
    "$hook" > "$mock_hook"

PATH="$fake_bin:$PATH" \
ACPI_OVERRIDE_TEST_FILE_LIST="$table_list" \
ACPI_OVERRIDE_TEST_EARLY_IMAGE="$early_image" \
sh "$mock_hook"

grep -Fx './kernel/firmware/acpi/table.aml' "$table_list" >/dev/null
test -s "$early_image"
echo "functional hook assertion passed"

if [ ! -r /usr/share/initramfs-tools/hook-functions ]; then
    echo "device integration pending: initramfs-tools-core is unavailable"
    exit 0
fi
command -v cpio >/dev/null 2>&1 || {
    echo "device integration pending: cpio is unavailable"
    exit 0
}
sh "$hook"
echo "full initramfs hook execution passed"
