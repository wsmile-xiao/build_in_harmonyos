#!/data/service/hnp/bin/bash
set -euo pipefail

package_folder=${1:?expected Conan package folder}
build_folder=${2:?expected Conan build folder}
package_binary="$package_folder/bin/wtype"
build_binary="$build_folder/wtype"

[[ -f "$package_binary" && -x "$package_binary" ]] || {
    echo "packaged wtype executable is missing or not executable: $package_binary" >&2
    exit 1
}

readelf_bin="${READELF:-/data/service/hnp/bin/readelf}"
elf_header="$("$readelf_bin" -h "$package_binary")"
[[ "$elf_header" == *"Machine:"*"AArch64"* ]] || {
    echo "packaged wtype is not an AArch64 ELF" >&2
    exit 1
}
echo "PASS: packaged wtype is an executable AArch64 ELF"

dynamic_info="$("$readelf_bin" -d "$package_binary")"
[[ "$dynamic_info" == *"Shared library: [libc.so]"* ]] || {
    echo "unexpected runtime dependency in packaged wtype: $dynamic_info" >&2
    exit 1
}
[[ "$dynamic_info" != *"RPATH"* && "$dynamic_info" != *"RUNPATH"* ]] || {
    echo "packaged wtype retains a build or Conan-cache RPATH" >&2
    exit 1
}
echo "PASS: packaged wtype has no Conan-cache runtime path"

machine="$(uname -m)"
[[ "$machine" == "aarch64" || "$machine" == "arm64" ]] || {
    echo "expected HarmonyOS PC ARM64, got: $machine" >&2
    exit 1
}
[[ -x "$build_binary" ]] || {
    echo "wtype build executable is unavailable: $build_binary" >&2
    exit 1
}
echo "PASS: test is running on HarmonyOS PC ARM64 ($machine)"

set +e
output="$("$build_binary" -P NoSuchKeysym_Wtype_Test 2>&1)"
status=$?
set -e

[[ $status -ne 0 ]] || {
    echo "wtype accepted an invalid keysym" >&2
    exit 1
}
[[ "$output" == *"Unknown key 'NoSuchKeysym_Wtype_Test'"* ]] || {
    echo "wtype did not report the invalid keysym: $output" >&2
    exit 1
}
[[ "$output" != *"Wayland connection failed"* ]] || {
    echo "wtype tried to connect to Wayland before validating the keysym" >&2
    exit 1
}
echo "PASS: invalid keysym is rejected before requiring a Wayland compositor"
