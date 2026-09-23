#!/usr/bin/zsh
# oystr 0.2.0 Conan consumer: test PTY file search and stdin search.
set -euo pipefail
work="${TMPDIR:-.}/oystr-test-$$"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work"
printf '%s\n' 'needle appears in this file' > "$work/input.txt"
printf '%s\n' 'no match here' >> "$work/input.txt"
# oystr intentionally treats command-line paths as paths only when stdin is
# a terminal. The worker-provided script utility supplies that PTY.
# Resolve the PTY helper from the test environment or PATH; do not assume a system path.
script_cmd="${SCRIPT:-}"
if [ -z "$script_cmd" ]; then
  # A missing PATH entry is intentionally converted to an empty value; the
  # explicit check below reports the probe failure without masking test errors.
  script_cmd="$(command -v script || true)"
fi
if [ -z "$script_cmd" ] || [ ! -x "$script_cmd" ]; then
  printf '%s\n' 'script utility is unavailable on this worker' >&2
  exit 1
fi
file_output=$(cd "$work" && "$script_cmd" -q -c "oy needle input.txt" "$work/typescript")
case "$file_output" in
  *needle*) : ;;
  *) echo "file search did not report the match" >&2; exit 1 ;;
esac
pipe_output=$(printf '%s\n' 'stream needle match' | oy needle)
case "$pipe_output" in
  *needle*) : ;;
  *) echo "stdin search did not report the match" >&2; exit 1 ;;
esac
printf '%s\n' 'oystr consumer checks passed'
