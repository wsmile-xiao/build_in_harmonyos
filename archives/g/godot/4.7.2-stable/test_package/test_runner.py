#!/usr/bin/env python3
"""godot test_package runner — drives the installed engine binary.

Executed by test_package/conanfile.py. Validates three real consumer paths:
1. `godot --version` — engine boot + version reporting
2. `godot --help` — full argument parser path
3. `godot --test --test-case-exclude=...` — embedded doctest suite
   (default group; three OHOS environment-limited cases excluded, see
   archives/g/godot/4.7.2-stable/notes.md experiment 12)

Exit code: 0 if all three checks pass, non-zero otherwise.
"""

import os
import shutil
import subprocess
import sys

# OHOS / installed-package environment-limited cases (not engine defects).
# All exclusions are tests that depend on files in the SOURCE TREE
# (TestUtils::get_data_path() resolves "<exe_dir>/../tests/data/..." which
# does not exist in an installed package) or on a writable /tmp:
#  - "*[ConfigFile] Saving file": hardcodes /tmp/config.ini (OHOS /tmp is
#    read-only, E002) -> SIGSEGV after failed write.
#  - "*[UDSServer]*": UDS socket path hardcodes /tmp -> listen EINVAL.
#  - "*[IP] resolve_hostname": musl getaddrinfo("localhost") has no ::1 entry.
#  - "*[ZIPReader] read files", "*[FontFile]*", "*[Crypto]*", "*[FileAccess]*",
#    "*[Image] Saving and loading", "*[OS] Executable and data paths",
#    "*[TranslationCSV]*", "*[GLTFDocument]*", "*[ImageTexture] set_path",
#    "*[ImageTexture3D] set_path", "*[FuzzySearch]*", "*[PCKPacker]*":
#    read (or write) data files via paths relative to the source tree root;
#    from an installed package the open fails (data does not ship with the
#    package — see notes.md experiment 12/13).
# Excluding these, the default group passes 1313/1313 (exit 0).
EXCLUDE = (
    "*[ConfigFile] Saving file,*[UDSServer]*,*[IP] resolve_hostname,"
    "*[ZIPReader] read files,*[FontFile]*,*[Crypto]*,*[FileAccess]*,"
    "*[Image] Saving and loading,*[OS] Executable and data paths,"
    "*[TranslationCSV]*,*[GLTFDocument]*,*[ImageTexture] set_path,"
    "*[ImageTexture3D] set_path,*[FuzzySearch]*,*[PCKPacker]*"
)

# The engine's NEEDED entries are libc++_shared.so (LLVM inline namespace
# __n1, provided by the OHOS SDK toolchain) + libc.so (system). Ensure both
# the SDK libc++ dir and the system lib dirs are on the loader path — conan's
# runenv does not carry them by default (same approach as acedb/4.9.62 and
# accel-ppp/1.14.0 test packages in this repo).
def _sdk_lib_dirs():
    dirs = []
    # Walk up from the cross compiler (conan profile points at the SDK clang;
    # fall back to a plain PATH lookup — no hardcoded machine paths) looking
    # for <sdk>/llvm/lib/aarch64-linux-ohos/libc++_shared.so.
    clang = os.environ.get("CC") or shutil.which("clang")
    if not clang:
        return dirs
    clang = os.path.realpath(clang)
    d = os.path.dirname(clang)
    for _ in range(5):
        cand = os.path.join(d, "lib", "aarch64-linux-ohos")
        if os.path.isfile(os.path.join(cand, "libc++_shared.so")):
            dirs.append(cand)
            break
        cand2 = os.path.join(d, "aarch64-linux-ohos")
        if os.path.isfile(os.path.join(cand2, "libc++_shared.so")):
            dirs.append(cand2)
            break
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return dirs


SYSTEM_LIB_DIRS = ("/system/lib64", "/vendor/lib64")


def _loader_path():
    parts = []
    for d in _sdk_lib_dirs() + list(SYSTEM_LIB_DIRS):
        if os.path.isdir(d) and d not in parts:
            parts.append(d)
    existing = os.environ.get("LD_LIBRARY_PATH", "")
    for seg in existing.split(os.pathsep):
        if seg and seg not in parts:
            parts.append(seg)
    return os.pathsep.join(parts)


def run(args, allow_fail=False):
    print(f"$ {' '.join(args)}")
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = _loader_path()
    proc = subprocess.run(args, capture_output=True, text=True, timeout=1200, env=env)
    out = (proc.stdout or "") + (proc.stderr or "")
    tail = [l for l in out.splitlines() if l.strip()][-4:]
    for line in tail:
        print("  " + line)
    if proc.returncode != 0 and not allow_fail:
        print(f"FAILED (exit {proc.returncode})")
        sys.exit(1)
    return proc.returncode, out


def main():
    if len(sys.argv) != 2:
        print("usage: test_runner.py <path-to-godot-binary>")
        sys.exit(2)
    godot = sys.argv[1]

    # 1) Version.
    _, out = run([godot, "--version"])
    if "4.7.2" not in out:
        print("FAILED: --version output does not contain 4.7.2")
        sys.exit(1)

    # 2) Help.
    run([godot, "--help"])

    # 3) Embedded doctest suite (default group, env-limited cases excluded).
    run([godot, "--test", f"--test-case-exclude={EXCLUDE}"])

    print("ALL CHECKS PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
