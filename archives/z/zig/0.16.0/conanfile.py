#!/usr/bin/env python3
"""Conan recipe for Zig 0.16.0.

Zig is consumed by downstream recipes as a build tool. This package keeps the
official distribution layout intact inside bin/ so `tool_requires("zig/0.16.0")`
puts a working `zig` on PATH while preserving Zig's sibling lib/ directory.

The package ID intentionally ignores compiler and build_type: Zig is a prebuilt
application selected by runtime os/arch, so Debug/Release or clang profile
changes must not create dependency gaps for downstream packages.
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class ZigConan(ConanFile):
    name = "zig"
    version = "0.16.0"
    description = "Zig programming language compiler and build tool"
    license = "MIT"
    homepage = "https://ziglang.org/"
    url = "https://ziglang.org/"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def configure(self):
        self.settings.rm_safe("compiler")
        self.settings.rm_safe("build_type")
        self.settings.rm_safe("os.version")

    def package_id(self):
        self.info.settings.rm_safe("compiler")
        self.info.settings.rm_safe("build_type")
        self.info.settings.rm_safe("os.version")

    def _platform_key(self):
        os_name = str(self.settings.os)
        arch = str(self.settings.arch)

        arch_map = {
            "x86_64": "x86_64",
            "x86": "x86",
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "armv7": "arm",
            "riscv64": "riscv64",
            "ppc64le": "powerpc64le",
            "s390x": "s390x",
            "loongarch64": "loongarch64",
        }
        zig_arch = arch_map.get(arch)
        if not zig_arch:
            raise ConanInvalidConfiguration(f"unsupported Zig binary architecture: {arch}")

        if os_name == "OHOS":
            if zig_arch != "aarch64":
                raise ConanInvalidConfiguration("OHOS Zig package is prepared for armv8/aarch64 only")
            return "aarch64-linux"

        if os_name == "Linux":
            key = f"{zig_arch}-linux"
        elif os_name == "Windows":
            key = f"{zig_arch}-windows"
        elif os_name == "Macos":
            key = f"{zig_arch}-macos"
        else:
            raise ConanInvalidConfiguration(f"unsupported Zig binary platform: {os_name}/{arch}")

        if key not in self.conan_data["sources"]:
            raise ConanInvalidConfiguration(
                f"unsupported Zig 0.16.0 prebuilt binary platform: {os_name}/{arch} maps to {key}"
            )
        return key

    def source(self):
        pass

    def build(self):
        key = self._platform_key()
        get(self, **self.conan_data["sources"][key], destination=self.build_folder, keep_permissions=True, strip_root=True)

        zig = os.path.join(self.build_folder, "zig.exe" if str(self.settings.os) == "Windows" else "zig")
        if not os.path.exists(zig):
            raise ConanInvalidConfiguration(f"official Zig archive did not contain expected executable: {zig}")
        lib_dir = os.path.join(self.build_folder, "lib")
        if not os.path.isdir(lib_dir):
            raise ConanInvalidConfiguration("official Zig archive did not contain lib/ directory")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "*", src=self.build_folder, dst=bin_dir)

        if str(self.settings.os) != "Windows":
            zig_bin = os.path.join(bin_dir, "zig")
            if str(self.settings.os) == "OHOS":
                real_zig = os.path.join(bin_dir, "zig-real")
                shutil.move(zig_bin, real_zig)
                os.chmod(real_zig, os.stat(real_zig).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                self._patch_ohos_zig_stdlib(bin_dir)
                self._sign_ohos_executable(real_zig)
                self._write_ohos_sign_helper(os.path.join(bin_dir, "zig-ohos-sign-generated"))
                self._write_ohos_zig_wrapper(zig_bin)
            else:
                os.chmod(zig_bin, os.stat(zig_bin).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def _sign_ohos_executable(self, path):
        signer = self._find_ohos_tool(
            "OHOS_BINARY_SIGN_TOOL",
            "binary-sign-tool",
            "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
        )
        objcopy = self._find_ohos_tool(
            "OHOS_LLVM_OBJCOPY",
            "llvm-objcopy",
            "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
        )

        if objcopy:
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" 2>/dev/null || true')
        if not signer:
            self.output.warning("binary-sign-tool not found; packaged Zig may require manual signing on OHOS")
            return
        self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1')

    def _find_ohos_tool(self, env_name, command, fallback):
        configured = os.environ.get(env_name)
        if configured:
            found = shutil.which(configured)
            if found:
                return found
            if os.path.exists(configured):
                return configured

        found = shutil.which(command)
        if found:
            return found
        if os.path.exists(fallback):
            return fallback
        return None

    def _patch_ohos_zig_stdlib(self, bin_dir):
        threaded = os.path.join(bin_dir, "lib", "std", "Io", "Threaded.zig")
        if not os.path.exists(threaded):
            raise ConanInvalidConfiguration(f"official Zig archive did not contain expected stdlib file: {threaded}")

        with open(threaded, "r", encoding="utf-8", newline="") as stdlib_file:
            content = stdlib_file.read()

        replacements = {
            ".OVERFLOW => |err| errnoBug(err), // We avoid passing too large of a `count`.":
                ".OVERFLOW => return error.Unimplemented, // OHOS may report this for sendfile fallback.",
            ".OVERFLOW => |err| errnoBug(err), // We avoid passing too large a count.":
                ".OVERFLOW => return error.Unimplemented, // OHOS may report this for copy_file_range fallback.",
        }
        patch_count = 0
        for old, new in replacements.items():
            patch_count += content.count(old)
            content = content.replace(old, new)
        if patch_count != 3:
            raise ConanInvalidConfiguration(f"expected 3 OHOS Zig stdlib fallback patches, applied {patch_count}")

        with open(threaded, "w", encoding="utf-8", newline="") as stdlib_file:
            stdlib_file.write(content)

    def _write_executable_script(self, path, content):
        with open(path, "w", encoding="utf-8", newline="\n") as script:
            script.write(content)
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def _write_ohos_sign_helper(self, path):
        self._write_executable_script(
            path,
            """#!/usr/bin/env sh
set -eu

case "${1:-}" in
    --version)
        echo "zig-ohos-sign-generated 0.16.0"
        exit 0
        ;;
    -h|--help)
        echo "usage: zig-ohos-sign-generated [ROOT_OR_FILE ...]"
        exit 0
        ;;
esac

find_tool() {
    configured=$1
    command_name=$2
    fallback=$3

    if [ -n "$configured" ]; then
        found=$(command -v "$configured" 2>/dev/null || true)
        if [ -n "$found" ]; then
            echo "$found"
            return 0
        fi
        if [ -x "$configured" ]; then
            echo "$configured"
            return 0
        fi
    fi

    found=$(command -v "$command_name" 2>/dev/null || true)
    if [ -n "$found" ]; then
        echo "$found"
        return 0
    fi
    if [ -x "$fallback" ]; then
        echo "$fallback"
    fi
}

signer=$(find_tool "${OHOS_BINARY_SIGN_TOOL:-}" binary-sign-tool /storage/Users/currentUser/usr/local/bin/binary-sign-tool)
[ -n "$signer" ] || exit 0

objcopy=$(find_tool "${OHOS_LLVM_OBJCOPY:-}" llvm-objcopy /storage/Users/currentUser/usr/local/bin/llvm-objcopy)

is_elf() {
    [ -f "$1" ] || return 1
    magic=$(dd if="$1" bs=4 count=1 2>/dev/null | od -An -tx1 2>/dev/null | tr -d ' \\n')
    [ "$magic" = "7f454c46" ]
}

sign_one() {
    candidate=$1
    [ -x "$candidate" ] || return 0
    is_elf "$candidate" || return 0
    if [ -n "$objcopy" ]; then
        "$objcopy" --remove-section .codesign "$candidate" 2>/dev/null || true
    fi
    "$signer" sign -inFile "$candidate" -outFile "$candidate" -selfSign 1 >/dev/null 2>&1 || true
}

if [ "$#" -gt 0 ]; then
    roots="$*"
elif [ -n "${ZIG_OHOS_SIGN_ROOTS:-}" ]; then
    roots=$ZIG_OHOS_SIGN_ROOTS
else
    roots=".zig-cache zig-cache zig-out"
fi

for root in $roots; do
    [ -e "$root" ] || continue
    if [ -f "$root" ]; then
        sign_one "$root"
    else
        find "$root" -type f -perm -100 2>/dev/null | while IFS= read -r candidate; do
            sign_one "$candidate"
        done
    fi
done
""",
        )

    def _write_ohos_zig_wrapper(self, path):
        self._write_executable_script(
            path,
            """#!/usr/bin/env sh
set -u

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
real_zig="$script_dir/zig-real"
sign_generated="$script_dir/zig-ohos-sign-generated"
max_retries=${ZIG_OHOS_SIGN_RETRIES:-3}
attempt=0

should_retry_after_signing() {
    grep -Eq 'AccessDenied|Permission denied|failed to spawn build runner' "$1"
}

maybe_sign_after_success() {
    case "${1:-}" in
        build|build-exe|test)
            "$sign_generated" >/dev/null 2>&1 || true
            ;;
    esac
}

while :; do
    stderr_file="${TMPDIR:-.}/zig-ohos-wrapper-$$-$attempt.stderr"
    "$real_zig" "$@" 2>"$stderr_file"
    rc=$?
    cat "$stderr_file" >&2

    if [ "$rc" -eq 0 ]; then
        rm -f "$stderr_file"
        maybe_sign_after_success "${1:-}"
        exit 0
    fi

    if [ "$attempt" -ge "$max_retries" ] || ! should_retry_after_signing "$stderr_file"; then
        rm -f "$stderr_file"
        exit "$rc"
    fi

    rm -f "$stderr_file"
    "$sign_generated" >&2 || true
    attempt=$((attempt + 1))
done
""",
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
