#!/usr/bin/env sh
set -eu
if (set -o pipefail) 2>/dev/null; then
	set -o pipefail
fi

# conan's VirtualRunEnv resets PATH to only the package's bin/ dir, so standard
# utilities (grep/cat/rm/mkdir/mktemp) are unreachable (Error 127). Restore the
# common OHOS tool dirs so the assertions below can run.
for _tool_dir in /system/bin /usr/bin /bin; do
	case ":${PATH:-}:" in
		*":$_tool_dir:"*) ;;
		*) PATH="${PATH:+$PATH:}$_tool_dir" ;;
	esac
done
export PATH

package_folder="$1"
remind="$package_folder/bin/remind"
rem2ps="$package_folder/bin/rem2ps"

if [ ! -x "$remind" ]; then
	echo "remind is not executable: $remind" >&2
	exit 1
fi

if [ ! -x "$rem2ps" ]; then
	echo "rem2ps is not executable: $rem2ps" >&2
	exit 1
fi

# The test only needs scratch files; write them directly into the
# already-existing, writable $package_folder/bin/ using a unique suffix, so no
# mkdir/mktemp dependency is required.
scratch="$package_folder/bin/.remind-test.$$"
trap 'rm -f "$scratch".*' EXIT HUP INT TERM

# remind -v exits 1 (it prints usage after the version banner); under
# `set -o pipefail` a piped `remind -v | grep` would surface that 1 and
# trip `set -e`. Write to a file first, then grep the file so no pipe is
# involved and remind's non-zero exit is swallowed by redirection.
"$remind" -v >"$scratch.version.out" 2>&1 || true
grep "REMIND 06.02.08" "$scratch.version.out" >/dev/null

cat >"$scratch.basic.rem" <<'EOF'
REM 16 Feb 1991 MSG parser assertion passed
EOF

"$remind" -q "$scratch.basic.rem" 16 Feb 1991 >"$scratch.basic.out"
grep "parser assertion passed" "$scratch.basic.out" >/dev/null

"$remind" -p "$scratch.basic.rem" 16 Feb 1991 | "$rem2ps" >"$scratch.basic.ps"
grep "%!PS-Adobe" "$scratch.basic.ps" >/dev/null

echo "=== remind tests PASSED ==="
