#!/data/service/hnp/bin/bash
set -euo pipefail

cmus_bin=$1
remote_bin=$2
package_dir=$3

version_output=$("$remote_bin" --version)
[[ "$version_output" == *"cmus v2.12.0"* || "$version_output" == *"cmus 2.12.0"* ]]

plugins_output=$("$cmus_bin" --plugins)
[[ "$plugins_output" == *"Input Plugins:"* ]]
[[ "$plugins_output" == *"wav"* ]]
[[ "$plugins_output" == *"cue"* ]]
[[ -x "$package_dir/lib/cmus/ip/wav.so" ]]
[[ -x "$package_dir/lib/cmus/ip/cue.so" ]]
[[ -d "$package_dir/lib/cmus/op" ]]

printf '%s\n' "cmus functional assertions: 7/7 PASS"
