#!/system/bin/sh
set -eu

ai_bin="$(command -v ai)"
test -n "$ai_bin"
if [ -x /system/bin/sh ]; then
    launcher_shell=/system/bin/sh
else
    launcher_shell=/bin/sh
fi

version_output="$("$launcher_shell" "$ai_bin" --version 2>&1)"
printf '%s\n' "$version_output"
test "$version_output" = "0.4.2"

help_output="$("$launcher_shell" "$ai_bin" --help 2>&1)"
printf '%s\n' "$help_output" | grep -F "Usage: ai" >/dev/null
printf '%s\n' "$help_output" | grep -F "Commands:" >/dev/null
printf '%s\n' "$help_output" | grep -F "text [options] [prompt]" >/dev/null
printf '%s\n' "$help_output" | grep -F "image [options] [prompt]" >/dev/null

text_help="$("$launcher_shell" "$ai_bin" text --help 2>&1)"
printf '%s\n' "$text_help" | grep -F -- "--model <model>" >/dev/null

echo "ai-cli 0.4.2 consumer checks: PASS"
