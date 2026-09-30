#!/data/service/hnp/bin/bash
# Consumer smoke test for the installed TinyFugue executable.
set -eu

if ! command -v tf >/dev/null 2>&1; then
    echo "tinyfugue: tf not found in PATH" >&2
    exit 1
fi
echo "tinyfugue: tf found in PATH"

version_output="$(tf --version 2>&1)"
printf '%s\n' "$version_output" | grep -F "TinyFugue version 5.2.2" >/dev/null
echo "tinyfugue: --version reports 5.2.2"

help_output="$(tf --help 2>&1)"
printf '%s\n' "$help_output" | grep -F "Usage:" >/dev/null
echo "tinyfugue: --help reports usage"

# TinyFugue is an interactive terminal client. Upstream CI only runs
# configure, make and make install; it never launches the TUI. Starting the
# client without a controlling terminal can block waiting for input, so the
# consumer test validates the installed executable and its packaged script
# library instead.
test -s "${TFLIBDIR}/stdlib.tf" || {
    echo "tinyfugue: packaged stdlib.tf is missing or empty" >&2
    exit 1
}
echo "tinyfugue: packaged stdlib.tf is non-empty"

tf_lib_count=$(find "${TFLIBDIR}" -maxdepth 1 -name '*.tf' | wc -l | tr -d ' ')
if [ "${tf_lib_count}" -lt 40 ]; then
    echo "tinyfugue: packaged tf-lib is incomplete (${tf_lib_count} .tf files)" >&2
    exit 1
fi

echo "tinyfugue: packaged script library complete (${tf_lib_count} .tf files)"
