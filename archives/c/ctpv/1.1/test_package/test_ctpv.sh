#!/usr/bin/env bash
set -euo pipefail

package_dir=$1
bin_dir="$package_dir/bin"
magic_db="$package_dir/share/misc/magic.mgc"
test_root="${TMPDIR:-$(pwd -P)}/ctpv-test-$$"
checks=0

cleanup() {
    rm -rf "$test_root"
}
trap cleanup EXIT INT TERM

mkdir -p "$test_root/home" "$test_root/config" "$test_root/cache" "$test_root/ohos-tmp"
export HOME="$test_root/home"
export XDG_CONFIG_HOME="$test_root/config"
export XDG_CACHE_HOME="$test_root/cache"
export MAGIC="$magic_db"
export SHELL=sh

ok() {
    checks=$((checks + 1))
    printf 'ok %d - %s\n' "$checks" "$1"
}

fail() {
    printf 'not ok %d - %s\n' "$((checks + 1))" "$1" >&2
    exit 1
}

wait_for_one_byte() {
    local path=$1
    local attempt
    for attempt in {1..40}; do
        if [[ -f "$path" && $(wc -c < "$path") -eq 1 ]]; then
            return 0
        fi
        sleep 0.05
    done
    return 1
}

[ -x "$bin_dir/ctpv" ] || fail "ctpv is installed and executable"
ok "ctpv is installed and executable"

clear_id=clear-command-test
clear_state="$test_root/ohos-tmp/ctpvfifo.$clear_id"
: > "$clear_state"
TMPDIR="$test_root/ohos-tmp" PATH="$bin_dir:$PATH" "$bin_dir/ctpvclear" "$clear_id"
ok "ctpvclear launches the packaged clear command"

quit_pid=99999999
quit_state="$test_root/ohos-tmp/ctpvfifo.$quit_pid"
: > "$quit_state"
TMPDIR="$test_root/ohos-tmp" PATH="$bin_dir:$PATH" "$bin_dir/ctpvquit" "$quit_pid"
wait_for_one_byte "$quit_state" || fail "ctpvquit dispatches after its process exits"
ok "ctpvquit dispatches after its process exits"

version_output=$("$bin_dir/ctpv" --version)
[[ "$version_output" == *"ctpv version 1.1"* ]] || fail "ctpv reports version 1.1"
ok "ctpv reports version 1.1"

help_output=$("$bin_dir/ctpv" --help)
[[ "$help_output" == *"Usage:"* && "$help_output" == *"Options:"* ]] || fail "ctpv help is available"
ok "ctpv help is available"

list_output=$("$bin_dir/ctpv" -l)
[[ "$list_output" == *"List of available previews:"* && "$list_output" == *"cat"* ]] || fail "ctpv lists built-in previews"
ok "ctpv lists built-in previews"

printf 'HarmonyOS ctpv preview payload\n' > "$test_root/sample.txt"
mime_output=$("$bin_dir/ctpv" -m "$test_root/sample.txt")
[[ "$mime_output" == *".txt text/plain"* ]] || fail "ctpv identifies text MIME type"
ok "ctpv identifies text MIME type"

preview_output=$(env -u SHELL PATH="$bin_dir:$PATH" "$bin_dir/ctpv" "$test_root/sample.txt" 80 20 0 0)
[[ "$preview_output" == *"HarmonyOS ctpv preview payload"* ]] || fail "ctpv renders a text preview with shell fallback"
ok "ctpv renders a text preview with shell fallback"

ln -s "$test_root/sample.txt" "$test_root/sample-link.txt"
link_output=$(env -u SHELL PATH="$bin_dir:$PATH" "$bin_dir/ctpv" "$test_root/sample-link.txt" 80 20 0 0)
[[ "$link_output" == *"Symlink points to:"* && "$link_output" == *"sample.txt"* ]] || fail "ctpv reports symlink targets"
ok "ctpv reports symlink targets"

if "$bin_dir/ctpv" -m "$test_root/missing" >/dev/null 2>&1; then
    fail "ctpv rejects missing input files"
fi
ok "ctpv rejects missing input files"

[ -f "$XDG_CONFIG_HOME/ctpv/config" ] || fail "ctpv creates its XDG configuration file"
ok "ctpv creates its XDG configuration file"

fifo_id=ohos-tmpdir-test
fifo_path="$test_root/ohos-tmp/ctpvfifo.$fifo_id"
: > "$fifo_path"
TMPDIR="$test_root/ohos-tmp" env -u SHELL PATH="$bin_dir:$PATH" "$bin_dir/ctpv" -e "$fifo_id"
wait_for_one_byte "$fifo_path" || fail "HarmonyOS TMPDIR is used for IPC state"
ok "HarmonyOS TMPDIR is used for IPC state"

printf '1..%d\n' "$checks"
[[ "$checks" -eq 12 ]] || fail "expected 12 assertions"
