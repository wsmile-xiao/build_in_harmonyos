#!/usr/bin/env python3
"""squsq 3.3 case runner — upstream behaviour + OHOS platform cases.

squsq 3.3 ships **no** automated test suite (see
``reports/upstream-test-entry.md`` for the evidence: no ``make check``/``make
test`` target in the distribution port, no test file in the tarball).  The cases
below are therefore derived from the authoritative upstream descriptions of the
programs' behaviour:

  * ``readme``   — the author's change list for SQ and USQ ("Changes to SQ"
                   1..4, "Changes to USQ" 1..4)
  * ``sq.c`` / ``usq.c`` — the on-line usage text and the option handling in
                   ``main()``/``obey()`` (``-``, ``-<n>``, ``-F``, ambiguous
                   name rejection, 8.3 output naming, ``FNM_LEN`` truncation)
  * ``sqio.c`` / ``tr2.c`` / ``utr.c`` — the on-disk Squeeze header layout
                   (``RECOGNIZE`` magic word, CRC word, original file name, then
                   the serialised decode tree)

Every case is executed for real against the packaged ``sq``/``usq`` binaries.
Group ``ohos`` holds the platform-specific checks (HarmonyOS executables must be
aarch64 ELFs carrying the OHOS identity note and, after packaging, a valid
``.codesign`` section — knowledge entry E077).

Usage:
    python3 test_squsq.py <package-bin-dir> [--log <file>]
"""

import argparse
import os
import shutil
import struct
import subprocess
import sys
import tempfile

CASES = []


def case(name, group):
    def decorate(func):
        CASES.append((name, group, func))
        return func

    return decorate


# ─────────────────────────── helpers ───────────────────────────

class Context:
    def __init__(self, bin_dir, work_dir):
        self.bin_dir = bin_dir
        self.work_dir = work_dir

    def binary(self, name):
        return os.path.join(self.bin_dir, name)

    def run(self, name, *args, **kwargs):
        # stdin 必须显式关闭：sq/usq 在*无参数*时会进入上游的交互式提示循环
        # （sq.c main(): "Enter file names, one line at a time, or type <RETURN>
        #  to quit." → getchar()）。若子进程继承到“永不 EOF”的 stdin（CI worker
        # 的 buildbot 管道即如此），该循环会永久阻塞 → 用例超时（CI 实测
        # `TimeoutExpired ... after 120 seconds`，2026-09-24 PR #12396 构建 #59456/#59543）。
        # DEVNULL 等价于用户直接按 <RETURN>/EOF，是上游文档规定的非交互退出路径。
        kwargs.setdefault("stdin", subprocess.DEVNULL)
        return subprocess.run(
            [self.binary(name), *args],
            cwd=kwargs.pop("cwd", self.work_dir),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=kwargs.pop("timeout", 120),
            **kwargs,
        )

    def path(self, name, sub=""):
        directory = os.path.join(self.work_dir, sub) if sub else self.work_dir
        return os.path.join(directory, name)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def write_text(ctx, name, content):
    target = ctx.path(name)
    with open(target, "w", encoding="utf-8", newline="") as stream:
        stream.write(content)
    return target


def write_bytes(ctx, name, content):
    target = ctx.path(name)
    with open(target, "wb") as stream:
        stream.write(content)
    return target


def read_bytes(ctx, name):
    with open(ctx.path(name), "rb") as stream:
        return stream.read()


def clean(ctx, *names):
    for name in names:
        path = ctx.path(name)
        if os.path.exists(path):
            os.remove(path)


def elf_machine(path):
    """Return the e_machine value of an ELF file (pure Python, no toolchain)."""
    with open(path, "rb") as stream:
        data = stream.read(64)
    check(data[:4] == b"\x7fELF", f"{path} is not an ELF file")
    check(data[4] == 2, f"{path} is not ELF64")
    check(data[5] == 1, f"{path} is not little endian")
    return struct.unpack_from("<H", data, 0x12)[0]


def elf_section_names(path):
    """Return the list of section names of an ELF64 little-endian file."""
    with open(path, "rb") as stream:
        data = stream.read()
    check(data[:4] == b"\x7fELF", f"{path} is not an ELF file")
    shoff = struct.unpack_from("<Q", data, 0x28)[0]
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 0x3A)
    check(shoff and shnum, f"{path} has no section header table")

    def header(index):
        base = shoff + index * shentsize
        sh_name, _sh_type = struct.unpack_from("<II", data, base)
        sh_offset, sh_size = struct.unpack_from("<QQ", data, base + 0x18)
        return sh_name, sh_offset, sh_size

    _name, str_offset, str_size = header(shstrndx)
    strings = data[str_offset:str_offset + str_size]
    names = []
    for index in range(shnum):
        sh_name, _offset, _size = header(index)
        end = strings.find(b"\x00", sh_name)
        names.append(strings[sh_name:end].decode("ascii", "replace"))
    return names


# ─────────────────── upstream behaviour cases ───────────────────

@case("sq_prints_version_banner", "upstream")
def sq_prints_version_banner(ctx):
    # 无参数调用会走上游的交互式提示分支（sq.c main()：
    # "Enter file names, one line at a time, or type <RETURN> to quit."）；
    # ctx.run 已把 stdin 置为 DEVNULL（等价按 <RETURN>/EOF），因此这里同时覆盖
    # “提示语正确 + 遇 EOF 立即干净退出”这一上游行为。
    result = ctx.run("sq")
    check(result.returncode == 0, f"sq exit={result.returncode}")
    check(
        "File squeezer version 3.3   10/29/86" in result.stdout,
        "sq banner/version string missing",
    )
    check("R. Greenlaw" in result.stdout, "author credit missing")
    check(
        "Enter file names, one line at a time, or type <RETURN> to quit." in result.stdout,
        "interactive prompt for the no-argument path is missing",
    )


@case("usq_prints_version_banner", "upstream")
def usq_prints_version_banner(ctx):
    result = ctx.run("usq")
    check(result.returncode == 0, f"usq exit={result.returncode}")
    check(
        "File unsqueezer version 3.3   10/29/86" in result.stdout,
        "usq banner/version string missing",
    )
    check(
        "Enter file names, one line at a time, or type <RETURN> to quit." in result.stdout,
        "interactive prompt for the no-argument path is missing",
    )


@case("sq_squeezes_file_to_SQ_extension", "upstream")
def sq_squeezes_file_to_SQ_extension(ctx):
    clean(ctx, "sample.txt", "sample.SQ")
    write_text(ctx, "sample.txt", "The quick brown fox jumps over the lazy dog.\n")
    result = ctx.run("sq", "sample.txt")
    check(result.returncode == 0, f"sq exit={result.returncode}")
    check(
        "sample.txt -> sample.SQ: analyzing, squeezing, done." in result.stdout,
        f"unexpected sq output: {result.stdout!r}",
    )
    check(os.path.isfile(ctx.path("sample.SQ")), "sample.SQ was not created")


@case("sq_header_has_squeeze_magic", "upstream")
def sq_header_has_squeeze_magic(ctx):
    data = read_bytes(ctx, "sample.SQ")
    check(len(data) > 4, "squeezed file is too short")
    magic = struct.unpack_from("<H", data, 0)[0]
    check(magic == 0xFF76, f"RECOGNIZE magic = 0x{magic:04X}, expected 0xFF76")


@case("sq_header_stores_original_name", "upstream")
def sq_header_stores_original_name(ctx):
    data = read_bytes(ctx, "sample.SQ")
    check(b"sample.txt\x00" in data[4:128], "original file name not stored in header")


@case("usq_roundtrip_restores_bytes", "upstream")
def usq_roundtrip_restores_bytes(ctx):
    original = read_bytes(ctx, "sample.txt")
    clean(ctx, "sample.txt")
    result = ctx.run("usq", "sample.SQ")
    check(result.returncode == 0, f"usq exit={result.returncode}")
    check("unsqueezing, done." in result.stdout, f"unexpected usq output: {result.stdout!r}")
    check(os.path.isfile(ctx.path("sample.txt")), "usq did not restore sample.txt")
    check(read_bytes(ctx, "sample.txt") == original, "restored content differs")


@case("usq_output_name_comes_from_header", "upstream")
def usq_output_name_comes_from_header(ctx):
    # The squeezed header carries "sample.txt"; rename the archive and the
    # restored name must still be sample.txt (readme: "The original file name
    # is stored in the squeezed file").
    shutil.copyfile(ctx.path("sample.SQ"), ctx.path("renamed.SQ"))
    clean(ctx, "sample.txt")
    result = ctx.run("usq", "renamed.SQ")
    check("renamed.SQ -> sample.txt:" in result.stdout, f"unexpected: {result.stdout!r}")
    check(os.path.isfile(ctx.path("sample.txt")), "stored name was not used")


@case("sq_replaces_existing_extension", "upstream")
def sq_replaces_existing_extension(ctx):
    # readme/SQ 3.0: "Generalized for UN*X use, changed output file naming".
    # On this build (UNIX macro left undefined, exactly like the FreeBSD port)
    # a file type is replaced: data.bin -> data.SQ.
    clean(ctx, "data.bin", "data.SQ")
    write_text(ctx, "data.bin", "payload\n")
    result = ctx.run("sq", "data.bin")
    check("data.bin -> data.SQ: analyzing, squeezing, done." in result.stdout,
          f"unexpected sq output: {result.stdout!r}")
    check(os.path.isfile(ctx.path("data.SQ")), "data.SQ was not created")
    check(not os.path.isfile(ctx.path("data.bin.SQ")), "name was appended, not replaced")


@case("sq_appends_suffix_when_no_extension", "upstream")
def sq_appends_suffix_when_no_extension(ctx):
    clean(ctx, "plain", "plain.SQ")
    write_text(ctx, "plain", "payload\n")
    result = ctx.run("sq", "plain")
    check("plain -> plain.SQ: analyzing, squeezing, done." in result.stdout,
          f"unexpected sq output: {result.stdout!r}")
    check(os.path.isfile(ctx.path("plain.SQ")), "plain.SQ was not created")


@case("sq_truncates_name_to_FNM_LEN", "upstream")
def sq_truncates_name_to_FNM_LEN(ctx):
    # sq.c: #define FNM_LEN 14 -> 14 - len(".SQ") = 11 characters kept.
    clean(ctx, "abcdefghijklmnop.txt", "abcdefghijk.SQ")
    write_text(ctx, "abcdefghijklmnop.txt", "payload\n")
    result = ctx.run("sq", "abcdefghijklmnop.txt")
    check("abcdefghijklmnop.txt -> abcdefghijk.SQ:" in result.stdout,
          f"unexpected sq output: {result.stdout!r}")
    check(os.path.isfile(ctx.path("abcdefghijk.SQ")), "truncated name not honoured")


@case("sq_rejects_ambiguous_name", "upstream")
def sq_rejects_ambiguous_name(ctx):
    # readme/SQ change 4: "Wildcard input filenames are accepted by this
    # version" — on this Unix build obey() reports them as ambiguous instead.
    clean(ctx, "wild.txt", "wild.SQ")
    write_text(ctx, "wild.txt", "payload\n")
    result = ctx.run("sq", "*.txt")
    check("Ambiguous name *.txt ignored" in result.stdout,
          f"unexpected sq output: {result.stdout!r}")
    check(not os.path.isfile(ctx.path("wild.SQ")), "wildcard input was processed")


@case("usq_rejects_ambiguous_name", "upstream")
def usq_rejects_ambiguous_name(ctx):
    result = ctx.run("usq", "*.SQ")
    check("Can't accept ambiguous name *.SQ" in result.stdout,
          f"unexpected usq output: {result.stdout!r}")


@case("sq_accepts_multiple_files", "upstream")
def sq_accepts_multiple_files(ctx):
    clean(ctx, "m1.txt", "m2.txt", "m1.SQ", "m2.SQ")
    write_text(ctx, "m1.txt", "first\n")
    write_text(ctx, "m2.txt", "second\n")
    result = ctx.run("sq", "m1.txt", "m2.txt")
    check("m1.txt -> m1.SQ: analyzing, squeezing, done." in result.stdout, "m1 not squeezed")
    check("m2.txt -> m2.SQ: analyzing, squeezing, done." in result.stdout, "m2 not squeezed")
    check(os.path.isfile(ctx.path("m1.SQ")) and os.path.isfile(ctx.path("m2.SQ")),
          "not all outputs created")


@case("sq_accepts_debug_option", "upstream")
def sq_accepts_debug_option(ctx):
    # sq.c main(): "Process the parameters in order" — a bare "-" toggles the
    # debug flag (change history 1.5: "Add debugging displays option '-'").
    clean(ctx, "dbg.txt", "dbg.SQ")
    write_text(ctx, "dbg.txt", "payload\n")
    result = ctx.run("sq", "-", "dbg.txt")
    check(result.returncode == 0, f"sq - exit={result.returncode}")
    check("dbg.txt -> dbg.SQ: analyzing, squeezing, done." in result.stdout,
          f"unexpected sq output: {result.stdout!r}")
    check(os.path.isfile(ctx.path("dbg.SQ")), "dbg.SQ was not created")


@case("roundtrip_empty_file", "upstream")
def roundtrip_empty_file(ctx):
    clean(ctx, "empty.txt", "empty.SQ")
    write_bytes(ctx, "empty.txt", b"")
    ctx.run("sq", "empty.txt")
    check(os.path.isfile(ctx.path("empty.SQ")), "empty.SQ was not created")
    clean(ctx, "empty.txt")
    result = ctx.run("usq", "empty.SQ")
    check("unsqueezing, done." in result.stdout, f"unexpected: {result.stdout!r}")
    check(read_bytes(ctx, "empty.txt") == b"", "empty file was not restored")


@case("roundtrip_all_byte_values", "upstream")
def roundtrip_all_byte_values(ctx):
    payload = bytes(range(256)) * 4
    clean(ctx, "bytes.bin", "bytes.SQ")
    write_bytes(ctx, "bytes.bin", payload)
    ctx.run("sq", "bytes.bin")
    clean(ctx, "bytes.bin")
    ctx.run("usq", "bytes.SQ")
    check(read_bytes(ctx, "bytes.bin") == payload, "8-bit data was not preserved")


@case("roundtrip_large_multibuffer_file", "upstream")
def roundtrip_large_multibuffer_file(ctx):
    # 64 KiB exercises the 128-byte output buffer flush path in usq.c and the
    # multi-pass analyse/squeeze path in sq.c.
    payload = bytes((index * 37 + 11) & 0xFF for index in range(65536))
    clean(ctx, "large.bin", "large.SQ")
    write_bytes(ctx, "large.bin", payload)
    ctx.run("sq", "large.bin")
    check(os.path.getsize(ctx.path("large.SQ")) > 0, "large.SQ is empty")
    clean(ctx, "large.bin")
    result = ctx.run("usq", "large.SQ")
    check("unsqueezing, done." in result.stdout, f"unexpected: {result.stdout!r}")
    check(read_bytes(ctx, "large.bin") == payload, "large file was not preserved")


@case("sq_reports_missing_input", "upstream")
def sq_reports_missing_input(ctx):
    clean(ctx, "nosuchfile.txt")
    result = ctx.run("sq", "nosuchfile.txt")
    check("Can't open nosuchfile.txt for input pass 1" in result.stdout,
          f"unexpected sq output: {result.stdout!r}")


@case("usq_reports_not_a_squeezed_file", "upstream")
def usq_reports_not_a_squeezed_file(ctx):
    clean(ctx, "notsqueezed.bin")
    write_text(ctx, "notsqueezed.bin", "not squeeezed at all\n")
    result = ctx.run("usq", "notsqueezed.bin")
    check("notsqueezed.bin is not a squeezed file" in result.stdout,
          f"unexpected usq output: {result.stdout!r}")


@case("usq_reports_missing_input", "upstream")
def usq_reports_missing_input(ctx):
    result = ctx.run("usq", "nosuch.SQ")
    check("Can't open nosuch.SQ" in result.stdout, f"unexpected usq output: {result.stdout!r}")


@case("usq_preview_limits_lines", "upstream")
def usq_preview_limits_lines(ctx):
    # usq.c obey(): "-<n>" sets dispcnt and switches to preview mode, which
    # writes to stdout instead of creating the output file.  readme/USQ 1:
    # "Both regular USQ and the 'preview' option will terminate processing
    #  upon the first decoded CP/M EOF returned."
    clean(ctx, "lines.txt", "lines.SQ", "lines.txt")
    write_text(ctx, "lines.txt", "AAA\nBBB\nCCC\nDDD\n")
    ctx.run("sq", "lines.txt")
    clean(ctx, "lines.txt")
    result = ctx.run("usq", "-2", "lines.SQ")
    check("lines.SQ -> lines.txt:" in result.stdout, f"unexpected: {result.stdout!r}")
    check("AAA" in result.stdout and "BBB" in result.stdout, "first lines not previewed")
    check("CCC" not in result.stdout, "preview did not stop after the line limit")
    check(not os.path.isfile(ctx.path("lines.txt")), "preview must not write the output file")


@case("usq_preview_whole_file_by_default", "upstream")
def usq_preview_whole_file_by_default(ctx):
    result = ctx.run("usq", "-", "lines.SQ")
    for expected in ("AAA", "BBB", "CCC", "DDD"):
        check(expected in result.stdout, f"{expected} missing from default preview")


@case("usq_preview_formfeed_option", "upstream")
def usq_preview_formfeed_option(ctx):
    # usq.c obey(): "-F"/"-f" keeps the preview flag and appends a form feed.
    result = ctx.run("usq", "-F", "lines.SQ")
    check(result.stdout.endswith("\f"), "preview did not end with a form feed")
    check("DDD" in result.stdout, "full preview content missing")


@case("usq_preview_bad_count_is_reported", "upstream")
def usq_preview_bad_count_is_reported(ctx):
    # usq.c obey(): a zero count prints "BAD COUNT <arg>" and leaves dispcnt 0,
    # so the file is decoded normally afterwards.
    clean(ctx, "lines.txt")
    result = ctx.run("usq", "-0", "lines.SQ")
    check("BAD COUNT 0" in result.stdout, f"unexpected usq output: {result.stdout!r}")
    check("unsqueezing, done." in result.stdout, "decode did not continue")
    check(os.path.isfile(ctx.path("lines.txt")), "lines.txt was not written")


# ───────────────────── OHOS platform cases ─────────────────────

@case("ohos_binaries_are_aarch64_elfs", "ohos")
def ohos_binaries_are_aarch64_elfs(ctx):
    for name in ("sq", "usq"):
        path = ctx.binary(name)
        check(os.path.isfile(path), f"{name} is missing from the package")
        machine = elf_machine(path)
        check(machine == 183, f"{name} e_machine={machine}, expected 183 (AArch64)")


@case("ohos_elfs_carry_ohos_identity_note", "ohos")
def ohos_elfs_carry_ohos_identity_note(ctx):
    # The OHOS toolchain stamps every produced ELF with .note.ohos.ident.
    for name in ("sq", "usq"):
        names = elf_section_names(ctx.binary(name))
        check(".note.ohos.ident" in names, f"{name} has no .note.ohos.ident section")


@case("ohos_elfs_are_codesigned", "ohos")
def ohos_elfs_are_codesigned(ctx):
    # E077: HarmonyOS only loads ELF images carrying a valid .codesign section.
    for name in ("sq", "usq"):
        names = elf_section_names(ctx.binary(name))
        check(".codesign" in names, f"{name} has no .codesign section")


# ─────────────────────────── runner ───────────────────────────

def main():
    parser = argparse.ArgumentParser(description="squsq 3.3 case runner")
    parser.add_argument("bin_dir", help="directory holding the packaged sq and usq")
    parser.add_argument("--log", help="write the report to this file as well")
    parser.add_argument("--work-dir", help="scratch directory (default: temporary)")
    args = parser.parse_args()

    bin_dir = os.path.abspath(args.bin_dir)
    work_dir = args.work_dir or tempfile.mkdtemp(prefix="squsq-cases-")
    os.makedirs(work_dir, exist_ok=True)

    lines = []
    passed = failed = skipped = 0

    def emit(text=""):
        print(text, flush=True)
        lines.append(text)

    emit(f"# squsq 3.3 case run — binaries: {bin_dir}")
    emit(f"# scratch dir: {work_dir}")
    emit()

    ctx = Context(bin_dir, work_dir)
    for name, group, func in CASES:
        try:
            func(ctx)
        except AssertionError as error:
            failed += 1
            emit(f"[FAIL] ({group}) {name}: {error}")
        except Exception as error:  # pragma: no cover - diagnostic path
            failed += 1
            emit(f"[ERROR] ({group}) {name}: {type(error).__name__}: {error}")
        else:
            passed += 1
            emit(f"[PASS] ({group}) {name}")

    total = len(CASES)
    emit()
    emit(f"TOTAL {total}  PASSED {passed}  FAILED {failed}  SKIPPED {skipped}")

    if args.log:
        with open(args.log, "w", encoding="utf-8") as stream:
            stream.write("\n".join(lines) + "\n")

    if not args.work_dir:
        shutil.rmtree(work_dir, ignore_errors=True)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
