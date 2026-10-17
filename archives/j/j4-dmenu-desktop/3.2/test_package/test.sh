#!/data/service/hnp/bin/bash
set -eu

version_output="$(j4-dmenu-desktop --version)"
printf '%s\n' "$version_output" | grep -F "3.2"

help_output="$(j4-dmenu-desktop --help 2>&1)"
printf '%s\n' "$help_output" | grep -F -- "--no-exec"

test_root="${TMPDIR:-$PWD}/j4-dmenu-desktop-test-$$"
mkdir -p "$test_root/data/applications" "$test_root/config" "$test_root/cache"
trap 'rm -rf "$test_root"' EXIT

cat > "$test_root/data/applications/codex-j4.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Codex J4 Test Entry
Exec=/system/bin/true
Terminal=false
EOF

selected="$(XDG_DATA_HOME="$test_root/data" \
  XDG_DATA_DIRS="$test_root/empty" \
  XDG_CONFIG_HOME="$test_root/config" \
  XDG_CACHE_HOME="$test_root/cache" \
  j4-dmenu-desktop --dmenu='head -n 1' --no-exec)"
printf '%s\n' "$selected" | grep -F "/system/bin/true"
printf '%s\n' "J4_DMENU_DESKTOP_TEST_OK"
