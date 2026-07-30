#!/usr/bin/env bash
set -euo pipefail

function_dir="$1"
work_dir="$2"
rm -rf "$work_dir"
mkdir -p "$work_dir"
cd "$work_dir"
work_dir="$(pwd)"
trap 'rm -rf "$work_dir"' EXIT
mkdir -p "$work_dir/bin" "$work_dir/workspace/src/demo_package"

cat > "$work_dir/bin/colcon" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "$*" = "list --packages-select demo_package --paths-only" ]; then
  printf '%s\n' "$MOCK_PACKAGE_PATH"
  exit 0
fi
exit 1
EOF
chmod +x "$work_dir/bin/colcon"
export PATH="$work_dir/bin:$PATH"
export MOCK_PACKAGE_PATH="$work_dir/workspace/src/demo_package"
export _ARGCOMPLETE=0
export _colcon_cd_root=""

. "$function_dir/colcon_cd.sh"

help_output="$(colcon_cd --help)"
printf '%s\n' "$help_output" | grep -q "usage: colcon_cd"

cd "$work_dir/workspace"
colcon_cd --set >/dev/null
[ "$_colcon_cd_root" = "$work_dir/workspace" ]

colcon_cd demo_package
[ "$(pwd)" = "$work_dir/workspace/src/demo_package" ]

colcon_cd
[ "$(pwd)" = "$work_dir/workspace" ]

colcon_cd --reset
[ "${_colcon_cd_root:-}" = "" ]

if colcon_cd one two >/dev/null 2>&1; then
  exit 1
fi
