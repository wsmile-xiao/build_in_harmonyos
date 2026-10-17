#!/usr/bin/env python3
"""Consumer-side acceptance test for the packaged ofhttp 1.5.7 executable.

Driven by test_package/conanfile.py.  Two layers, both on the real artifact:

  A. Packaged-artifact assertions (no execution) -- these read the bytes that
     ``package()`` actually shipped, 6 checks:
       1. bin/ofhttp exists, is a real file and keeps its executable bit (the
          mode bits are read directly, not through os.access(), which reports
          X_OK for a 0644 file when the test happens to run as uid 0)
       2. bin/ofhttp is a 64-bit little-endian ELF whose e_machine is AArch64
          (183) and whose e_type is EXEC/DYN, i.e. the packaged binary really is
          the OHOS aarch64 program and not a host leftover
       3. ... whose DT_NEEDED list carries no libobjfw*/libobjfwtls/libssl/
          libcrypto/libstdc++/libgcc_s, so the recipe's "ofhttp ships as a
          self-contained executable" claim is checked instead of merely asserted
       4. share/ofhttp/localization/{localizations.json,de.json} are shipped and
          are well-formed ObjFW localizations carrying the message ids ofhttp
          actually renders (they are JS object literals, not JSON)
       5. share/man/man1/ofhttp.1 is shipped and is the ofhttp man page
       6. licenses/{COPYING,COPYING.LESSER} are shipped with real license text

  B. Runtime assertions (only when the host can execute the target) -- these run
     the shipped binary against a real loopback HTTP server, 5 checks:
       1. ``--version``  -> exit 0, and stdout carries the four literal lines of
          upstream version() while stderr stays empty, because version() writes
          to OFStdOut only
       2. ``--help``     -> exit 0, stdout carries all 14 upstream options with
          their original column alignment, and the stderr usage banner echoes
          argv[0] verbatim -- so it names the very path that was executed, which
          a stub emitting a fixed banner cannot reproduce
       3. real HTTP GET  -> a loopback server serves a binary payload; the bytes
                             written by ofhttp must match it exactly (binary safe)
       4. real ``-H``    -> a custom request header must reach the server
       5. status handling-> a 404 must fail by default and succeed with
                             ``--ignore-status``

``--self-test`` proves none of the above is a no-op, in two independent ways:

  * every *artifact* assertion is handed a copy of the *real* package broken in
    exactly one way and has to reject it;
  * every *runtime* assertion is pointed at two impostors that both exit 0 --
    one that prints nothing, and one that prints a byte-correct copy of the
    --version banner but on the wrong stream -- and has to reject both.

An assertion that accepts a broken artifact or a non-ofhttp binary is reported
as an error, so the consumer test cannot silently degrade into a smoke test.

``--no-run`` stops after the artifact layer, for hosts that cannot execute the
target (cross-building OHOS from x86_64).

A non-zero exit code (including an assertion) fails the conan test.
"""

import http.server
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading

TIMEOUT = 90

# Deterministic payload covering every byte value (NUL and >0x7F included) so a
# text-mode or truncation bug in the transfer shows up as a content mismatch.
# len(PAYLOAD) == 256*8 + 19*4 == 2128.
PAYLOAD = bytes(range(256)) * 8 + b"ofhttp-test-payload\n" * 4
PROBE_VALUE = "ofhttp-1.5.7-probe-4f2c"

# ELF constants (see elf(5)).
EM_AARCH64 = 183
ELFCLASS64 = 2
ELFDATA2LSB = 1
ET_EXEC = 2
ET_DYN = 3
PT_LOAD = 1
PT_DYNAMIC = 2
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_STRSZ = 10

# Nothing from the Objective-C runtime, OpenSSL or the GNU runtime may survive as
# a *dynamic* dependency: ofhttp is packaged as a self-contained executable.
FORBIDDEN_NEEDED_PREFIXES = (
    "libobjfw", "libobjfwtls", "libssl", "libcrypto", "libstdc++", "libgcc_s",
)

# Messages ofhttp actually renders through OF_LOCALIZED, verified against
# utils/ofhttp/OFHTTP.m and utils/ofhttp/ProgressBar.m of the 1.5.7 tree.
# Chosen to span the code paths the runtime checks drive: --help (usage/
# full_usage/unknown_option), -H (invalid_input_header), the TLS build
# (no_tls_support), the download outcome (download_failed/download_done) and the
# progress bar (progress_bytes). All of them are present in the shipped de.json.
REQUIRED_MESSAGES = (
    "usage",
    "full_usage",
    "unknown_option",
    "invalid_input_header",
    "no_tls_support",
    "download_failed",
    "download_done",
    "progress_bytes",
)

MAN_PAGE_HEADER = ".TH ofhttp"

# --version / --help output, verified against a real build of the very same
# tarball (sha256 2febf4c2..., utils/ofhttp/OFHTTP.m version()/help()).
# version() writes three literal lines to stdout and nothing to stderr; help()
# writes the option table to stdout and the usage banner to stderr, where the
# banner renders argv[0] verbatim -- so it must echo back the path we invoked.
VERSION_BANNER = (
    "ofhttp 1.5.7",
    "(ObjFW 1.5.7)",
    "<https://objfw.nil.im/>",
    "Licensed under the LGPL 3.0 <https://www.gnu.org/licenses/lgpl-3.0.html>",
)
HELP_OPTIONS = (
    "-b  --body=",
    "-c  --continue",
    "-f  --force",
    "-h  --help",
    "-H  --header=",
    "-m  --method=",
    "-o  --output=",
    "-O  --detect-filename",
    "-P  --proxy=",
    "-q  --quiet",
    "-v  --verbose",
    "--insecure",
    "--ignore-status",
    "--version",
)
# The part of the usage line that does not depend on argv[0]: help() renders
# "Usage: %[prog] -[cehHmoOPqv] iri1 [iri2 ...]" and %[prog] is the full path.
HELP_USAGE_TAIL = "-[cehHmoOPqv] iri1 [iri2 ...]"

LICENSES = (
    ("COPYING", "GNU GENERAL PUBLIC LICENSE"),
    ("COPYING.LESSER", "GNU LESSER GENERAL PUBLIC LICENSE"),
)


# --------------------------------------------------------------- ELF reading


class ElfError(Exception):
    """Raised when a file is not a well formed 64-bit little-endian ELF."""


def _cstr(blob, offset):
    end = blob.find(b"\0", offset)
    if end < 0:
        raise ElfError(f"unterminated string at offset {offset}")
    return blob[offset:end].decode("utf-8", "replace")


def _vaddr_to_offset(vaddr, loads):
    for base, offset, size in loads:
        if base <= vaddr < base + size:
            return offset + (vaddr - base)
    raise ElfError(f"virtual address 0x{vaddr:x} is outside every PT_LOAD segment")


def read_elf(path):
    """Return ``(e_machine, e_type, sorted DT_NEEDED)`` of the ELF at ``path``.

    Parsed straight from the bytes on purpose: the test must not depend on
    binutils being present on the OHOS CI worker.
    """
    with open(path, "rb") as handle:
        blob = handle.read()

    if len(blob) < 64 or blob[:4] != b"\x7fELF":
        raise ElfError(f"{path} is not an ELF file (magic={blob[:4]!r})")
    if blob[4] != ELFCLASS64:
        raise ElfError(f"{path} is not ELF64 (EI_CLASS={blob[4]})")
    if blob[5] != ELFDATA2LSB:
        raise ElfError(f"{path} is not little endian (EI_DATA={blob[5]})")

    e_type, e_machine = struct.unpack_from("<HH", blob, 16)
    e_phoff, = struct.unpack_from("<Q", blob, 32)
    e_phentsize, e_phnum = struct.unpack_from("<HH", blob, 54)

    loads = []
    dynamic = None
    for index in range(e_phnum):
        base = e_phoff + index * e_phentsize
        if base + 56 > len(blob):
            raise ElfError(f"{path}: program header {index} runs past end of file")
        p_type, _flags = struct.unpack_from("<II", blob, base)
        p_offset, p_vaddr, _paddr, p_filesz = struct.unpack_from("<QQQQ", blob, base + 8)
        if p_type == PT_DYNAMIC:
            dynamic = (p_offset, p_filesz)
        elif p_type == PT_LOAD and p_filesz:
            loads.append((p_vaddr, p_offset, p_filesz))

    needed = []
    if dynamic is not None:
        needed = _read_dynamic_strings(blob, dynamic, loads, path)
    return e_machine, e_type, sorted(needed)


def _read_dynamic_strings(blob, dynamic, loads, path):
    p_offset, p_filesz = dynamic
    if p_offset + p_filesz > len(blob):
        raise ElfError(f"{path}: PT_DYNAMIC runs past end of file")
    entries = []
    strtab_vaddr = None
    strsz = 0
    for pos in range(p_offset, p_offset + p_filesz, 16):
        d_tag, d_val = struct.unpack_from("<qQ", blob, pos)
        if d_tag == DT_NULL:
            break
        entries.append((d_tag, d_val))
        if d_tag == DT_STRTAB:
            strtab_vaddr = d_val
        elif d_tag == DT_STRSZ:
            strsz = d_val
    if strtab_vaddr is None:
        return []
    strtab_off = _vaddr_to_offset(strtab_vaddr, loads)
    if strtab_off + strsz > len(blob):
        raise ElfError(f"{path}: .dynstr runs past end of file")
    table = blob[strtab_off:strtab_off + strsz]
    return [_cstr(table, d_val) for d_tag, d_val in entries if d_tag == DT_NEEDED]


def build_synthetic_elf(needed, e_machine=EM_AARCH64, e_type=ET_DYN):
    """A minimal but *well formed* ELF64 whose DT_NEEDED is exactly ``needed``.

    Used only by ``--self-test`` to hand the runtime-dependency check an
    artifact that is structurally valid but semantically wrong, so the check
    has to reject it for the right reason.
    """
    dynstr = b"\0"
    offsets = []
    for name in needed:
        offsets.append(len(dynstr))
        dynstr += name.encode() + b"\0"

    ehsize, phentsize = 64, 56
    phoff = ehsize
    dynstr_off = phoff + 2 * phentsize
    dynstr_off += (-dynstr_off) % 8
    dynamic_off = dynstr_off + len(dynstr)
    dynamic_off += (-dynamic_off) % 8

    dynamic = b""
    for offset in offsets:
        dynamic += struct.pack("<qQ", DT_NEEDED, offset)
    dynamic += struct.pack("<qQ", DT_STRTAB, dynstr_off)  # vaddr == file offset
    dynamic += struct.pack("<qQ", DT_STRSZ, len(dynstr))
    dynamic += struct.pack("<qQ", DT_NULL, 0)
    total = dynamic_off + len(dynamic)

    header = b"\x7fELF" + bytes([ELFCLASS64, ELFDATA2LSB, 1, 0]) + b"\0" * 8
    header += struct.pack("<HHI", e_type, e_machine, 1)
    header += struct.pack("<QQQ", 0, phoff, 0)          # e_entry, e_phoff, e_shoff
    header += struct.pack("<IHHHHHH", 0, ehsize, phentsize, 2, 0, 0, 0)

    phdrs = struct.pack("<II", PT_LOAD, 5) + struct.pack("<QQQQQQ", 0, 0, 0, total, total, 0x1000)
    phdrs += struct.pack("<II", PT_DYNAMIC, 6) + struct.pack(
        "<QQQQQQ", dynamic_off, dynamic_off, dynamic_off, len(dynamic), len(dynamic), 8)

    blob = bytearray(total)
    blob[0:len(header)] = header
    blob[phoff:phoff + len(phdrs)] = phdrs
    blob[dynstr_off:dynstr_off + len(dynstr)] = dynstr
    blob[dynamic_off:dynamic_off + len(dynamic)] = dynamic
    return bytes(blob)


# ------------------------------------------------------- A: artifact asserts


def check_executable_present(package_folder):
    executable = os.path.join(package_folder, "bin", "ofhttp")
    assert os.path.isfile(executable), f"ofhttp binary not packaged: {executable}"
    assert not os.path.islink(executable), f"bin/ofhttp must be a real file: {executable}"
    # Read the mode bits instead of os.access(): a root-run test (uid 0) would
    # get X_OK from os.access() even with mode 0644, which would make this
    # assertion a no-op locally while still holding on the CI worker.
    mode = os.stat(executable).st_mode
    assert mode & 0o111, f"ofhttp binary lost its executable bits (mode={mode & 0o777:04o}): {executable}"
    return executable


def check_elf_target(executable):
    e_machine, e_type, _needed = read_elf(executable)
    assert e_machine == EM_AARCH64, (
        f"packaged bin/ofhttp has e_machine={e_machine}, expected AArch64 "
        f"({EM_AARCH64}) for os=OHOS arch=armv8"
    )
    assert e_type in (ET_EXEC, ET_DYN), (
        f"packaged bin/ofhttp has e_type={e_type}, expected ET_EXEC or ET_DYN"
    )
    return (f"64-bit little-endian AArch64 ELF, e_type={e_type}, "
            f"e_machine={e_machine}")


def check_no_runtime_dependency(executable):
    _e_machine, _e_type, needed = read_elf(executable)
    leaked = [lib for lib in needed
              if lib.startswith(FORBIDDEN_NEEDED_PREFIXES)]
    assert not leaked, (
        "ofhttp must ship as a self-contained executable, but DT_NEEDED leaks "
        f"{leaked}; full list: {needed}"
    )
    return f"DT_NEEDED={needed} carries no libobjfw*/libobjfwtls/libssl/libcrypto/libstdc++"


def check_localization(package_folder):
    root = os.path.join(package_folder, "share", "ofhttp", "localization")

    index_path = os.path.join(root, "localizations.json")
    assert os.path.isfile(index_path), f"localization index not packaged: {index_path}"
    index_body = _objfw_object_body(index_path)
    # localizations.json maps a language name to a locale code. ofhttp ships
    # exactly one translation (German), so all three upstream spellings of it
    # must resolve to "de".
    for language in ("de", "deutsch", "german"):
        assert re.search(
            r"%s\s*:\s*\{\s*\"\"\s*:\s*\"de\"" % re.escape(language), index_body), (
            f"localizations.json does not map the {language!r} language to the de "
            f"locale: {index_body[:200]}"
        )

    de_path = os.path.join(root, "de.json")
    assert os.path.isfile(de_path), f"German translation not packaged: {de_path}"
    de_keys = _objfw_object_body(de_path)
    missing = [key for key in REQUIRED_MESSAGES if not re.search(
        r"(?m)^\s*%s\s*:" % re.escape(key), de_keys)]
    assert not missing, (
        f"de.json is missing {missing}, which ofhttp renders via OF_LOCALIZED; "
        f"it has {_objfw_keys(de_keys)}"
    )
    return (f"localizations.json maps de/deutsch/german -> de; de.json carries "
            f"{len(_objfw_keys(de_keys))} messages incl. {'/'.join(REQUIRED_MESSAGES)}")


def _strip_c_comments(text):
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def _objfw_object_body(path):
    """ObjFW localization files are JavaScript object literals, not JSON.

    They carry a ``/* ... */`` licence header, unquoted keys and trailing
    commas, so ``json.load`` rejects them; parse them the way the format
    actually is instead of pretending they are JSON.
    """
    with open(path, "r", encoding="utf-8") as handle:
        body = _strip_c_comments(handle.read()).strip()
    assert body.startswith("{") and body.endswith("}"), (
        f"{path} is not an ObjFW localization object literal "
        f"(starts {body[:1]!r}, ends {body[-1:]!r})"
    )
    return body


def _objfw_keys(body):
    return sorted(set(re.findall(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", body)))


def check_man_page(package_folder):
    man_page = os.path.join(package_folder, "share", "man", "man1", "ofhttp.1")
    assert os.path.isfile(man_page), f"man page not packaged: {man_page}"
    with open(man_page, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    assert MAN_PAGE_HEADER in text, (
        f"packaged man page lacks the upstream {MAN_PAGE_HEADER!r} header: {man_page}")
    return f"share/man/man1/ofhttp.1 carries the upstream {MAN_PAGE_HEADER!r} roff header ({len(text)} bytes)"


def check_licenses(package_folder):
    details = []
    for name, needle in LICENSES:
        path = os.path.join(package_folder, "licenses", name)
        assert os.path.isfile(path), f"license not packaged: {path}"
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        assert needle in text, f"{name} does not contain {needle!r}: {path}"
        assert len(text) > 1000, f"{name} is suspiciously short ({len(text)} bytes): {path}"
        details.append(f"{name}={len(text)}B")
    return "licenses/ carry the real LGPL text (" + ", ".join(details) + ")"


# Each entry: (label, check, argument selector). ``check`` receives the package
# folder unless ``wants_executable`` is set, in which case it receives the path
# of bin/ofhttp -- the same way the real conanfile.py resolves the deliverable.
ARTIFACT_CHECKS = (
    ("bin/ofhttp is a real file with its executable bits", check_executable_present, False),
    ("bin/ofhttp is an aarch64 ELF", check_elf_target, True),
    ("bin/ofhttp has no leaked runtime dependency", check_no_runtime_dependency, True),
    ("localization data is a usable ObjFW localization", check_localization, False),
    ("share/man/man1/ofhttp.1 is the ofhttp man page", check_man_page, False),
    ("licenses are shipped", check_licenses, False),
)


def run_artifact_checks(package_folder):
    executable = check_executable_present(package_folder)
    results = []
    for label, check, wants_executable in ARTIFACT_CHECKS:
        detail = check(executable if wants_executable else package_folder)
        results.append((label, detail))
    return executable, results


# ---------------------------------------------------------- B: runtime asserts


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def _respond(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/payload.bin":
            self._respond(200, PAYLOAD, "application/octet-stream")
        elif self.path == "/echo":
            # Echo back the custom header so the client can prove it was sent.
            received = self.headers.get("X-Ofhttp-Probe", "")
            self._respond(200, received.encode("utf-8"), "text/plain")
        else:
            self._respond(404, b"not found\n", "text/plain")

    def log_message(self, *args):
        pass


def _run(executable, args, workdir):
    # ofhttp renders its messages through OF_LOCALIZED. Pin the locale to C so
    # the assertions below always see the built-in English fallbacks instead of
    # a translation (the tarball only ships a de.json, but a worker whose locale
    # maps onto "de" would otherwise fail the text assertions).
    env = dict(os.environ, LC_ALL="C", LANG="C", LC_MESSAGES="C")
    return subprocess.run(
        [executable, *args],
        cwd=workdir,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )


def check_version(executable, workdir):
    result = _run(executable, ["--version"], workdir)
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"ofhttp --version failed: rc={result.returncode}\n{output}"
    missing = [line for line in VERSION_BANNER if line not in result.stdout]
    assert not missing, (
        f"ofhttp --version banner is missing {missing}; upstream version() writes "
        f"them to stdout verbatim:\n{result.stdout}"
    )
    # version() writes to OFStdOut only, so anything on stderr is not its banner.
    assert not result.stderr.strip(), (
        f"ofhttp --version wrote to stderr, which upstream version() never does: "
        f"{result.stderr!r}"
    )
    return ("ofhttp --version prints the full upstream banner (ofhttp 1.5.7 / "
            "ObjFW 1.5.7 / project URL / LGPL line) on stdout and nothing on stderr")


def check_help(executable, workdir):
    result = _run(executable, ["--help"], workdir)
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"ofhttp --help failed: rc={result.returncode}\n{output}"
    # The 14-entry option table, with upstream's column spacing, on stdout.
    missing = [option for option in HELP_OPTIONS if option not in result.stdout]
    assert not missing, (
        f"ofhttp --help option table is missing {missing}; upstream help() writes "
        f"the table to stdout:\n{result.stdout}"
    )
    # The usage banner goes to stderr and renders argv[0] verbatim, so it has
    # to name the exact path that was executed -- something a fixed banner
    # emitted by a stub cannot reproduce.
    assert result.stderr.startswith("Usage: "), (
        f"ofhttp --help did not open its usage banner on stderr: {result.stderr!r}"
    )
    assert HELP_USAGE_TAIL in result.stderr, (
        f"ofhttp --help usage banner lacks {HELP_USAGE_TAIL!r}: {result.stderr!r}"
    )
    assert executable in result.stderr, (
        "ofhttp --help usage banner must echo the program path that was invoked; "
        f"expected {executable!r} inside {result.stderr!r}"
    )
    return (f"ofhttp --help prints all {len(HELP_OPTIONS)} upstream options on stdout "
            "and echoes the invoked path in the stderr usage banner")


def check_download(executable, workdir, base_url):
    target = os.path.join(workdir, "downloaded.bin")
    result = _run(executable, ["-o", target, f"{base_url}/payload.bin"], workdir)
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"ofhttp download failed: rc={result.returncode}\n{output}"
    assert os.path.isfile(target), f"ofhttp did not create {target}:\n{output}"
    with open(target, "rb") as handle:
        written = handle.read()
    assert written == PAYLOAD, (
        f"downloaded payload mismatch: {len(written)} bytes written, "
        f"{len(PAYLOAD)} expected; first difference at "
        f"{next((i for i, (a, b) in enumerate(zip(written, PAYLOAD)) if a != b), 'end')}"
    )
    return f"ofhttp downloaded all {len(PAYLOAD)} binary bytes byte-for-byte"


def check_header(executable, workdir, base_url):
    target = os.path.join(workdir, "echo.txt")
    result = _run(
        executable,
        ["-H", f"X-Ofhttp-Probe: {PROBE_VALUE}", "-o", target, f"{base_url}/echo"],
        workdir,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"ofhttp -H request failed: rc={result.returncode}\n{output}"
    assert os.path.isfile(target), f"ofhttp did not create {target}:\n{output}"
    with open(target, "r", encoding="utf-8") as handle:
        received = handle.read()
    assert received == PROBE_VALUE, (
        f"custom request header was not delivered: sent {PROBE_VALUE!r}, server saw {received!r}"
    )
    return "ofhttp delivered a custom -H request header to the server"


def check_status_handling(executable, workdir, base_url):
    strict = _run(executable, ["-o", os.path.join(workdir, "strict.out"), f"{base_url}/missing"], workdir)
    assert strict.returncode != 0, (
        f"ofhttp returned {strict.returncode} for HTTP 404 without --ignore-status:\n"
        f"{strict.stdout}{strict.stderr}"
    )

    lenient_target = os.path.join(workdir, "lenient.out")
    lenient = _run(
        executable,
        ["--ignore-status", "-o", lenient_target, f"{base_url}/missing"],
        workdir,
    )
    output = lenient.stdout + lenient.stderr
    assert lenient.returncode == 0, (
        f"ofhttp --ignore-status still failed on HTTP 404: rc={lenient.returncode}\n{output}"
    )
    assert os.path.isfile(lenient_target), f"ofhttp did not create {lenient_target}:\n{output}"
    return "ofhttp fails on HTTP 404 but honours --ignore-status"


def run_runtime_checks(executable, workdir):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        return [
            check_version(executable, workdir),
            check_help(executable, workdir),
            check_download(executable, workdir, base_url),
            check_header(executable, workdir, base_url),
            check_status_handling(executable, workdir, base_url),
        ]
    finally:
        server.shutdown()
        server.server_close()


# ------------------------------------------------------- C: runtime falsifying


# A binary that exits 0 and prints nothing is the exact shape a hollow consumer
# test accepts. Pointing the runtime assertions at such a stub proves they look
# at what ofhttp actually does rather than at its exit status.
#
# The stub is a two-line POSIX shell script so it needs no compiler on the OHOS
# worker; the interpreters are probed in the order the CI image provides them.
STUB_SHELL_CANDIDATES = (
    "/data/service/hnp/bin/bash",   # the HNP bash the ohos-aarch64 profile pins
    "/system/bin/sh",
    "/bin/bash",
    "/bin/sh",
)


def _find_shell():
    for candidate in STUB_SHELL_CANDIDATES:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    found = shutil.which("sh")
    if found:
        return found
    raise AssertionError(
        "cannot build the runtime-proof stub: none of "
        f"{list(STUB_SHELL_CANDIDATES)} exists and 'sh' is not on PATH"
    )


# Two adversarial stubs, both of which "succeed" in the loosest sense:
#   silent   -- exits 0 and says nothing.  This is the shape a hollow consumer
#               test accepts, and the one every runtime assertion must reject.
#   liar     -- exits 0 and prints a byte-correct copy of the --version banner,
#               but on stderr instead of stdout.  It exists so the proof is not
#               only about exit codes: a check that merely looked for "ofhttp
#               1.5.7" somewhere in the combined output would accept this, so
#               it also pins which stream ofhttp actually writes to.
STUB_SCRIPTS = (
    ("silent", "exit 0\n"),
    ("banner-on-stderr",
     "echo 'ofhttp 1.5.7 (ObjFW 1.5.7) <https://objfw.nil.im/>' >&2\n"
     "echo 'Copyright (c) 2008-2026 Jonathan Schleifer <js@nil.im>' >&2\n"
     "echo 'Licensed under the LGPL 3.0"
     " <https://www.gnu.org/licenses/lgpl-3.0.html>' >&2\n"
     "exit 0\n"),
)


def _write_stub(directory, label, body):
    """Write an executable that exits 0 and keeps stdout empty."""
    path = os.path.join(directory, "ofhttp-stub-" + label)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("#!%s\n%s" % (_find_shell(), body))
    os.chmod(path, 0o755)
    # Prove the stub is really runnable before blaming the assertions for it:
    # an environment that cannot execute a shebang script cannot falsify
    # anything, and that must surface as a failure rather than a silent pass.
    # The contract is rc==0 with empty stdout, which both stubs satisfy.
    probe = subprocess.run([path, "--version"], capture_output=True, text=True,
                           timeout=TIMEOUT, check=False)
    if probe.returncode != 0 or probe.stdout:
        raise AssertionError(
            f"the {label} runtime-proof stub is not a clean 'succeeds on stdout' "
            f"impostor (rc={probe.returncode}, stdout={probe.stdout!r}); the host "
            "cannot execute a shebang script, so the runtime assertions cannot "
            "be falsified here"
        )
    return path


# (description, check(executable, workdir, base_url)). check_version and
# check_help take no base_url; wrap them so every entry has one shape.
RUNTIME_CHECKS = (
    ("ofhttp --version reports the ofhttp banner",
     lambda exe, wd, _url: check_version(exe, wd)),
    ("ofhttp --help lists the option set",
     lambda exe, wd, _url: check_help(exe, wd)),
    ("a download writes exactly the bytes the server served", check_download),
    ("-H delivers the custom request header", check_header),
    ("HTTP 404 fails unless --ignore-status", check_status_handling),
)
RUNTIME_CHECK_COUNT = len(RUNTIME_CHECKS)


def selftest_runtime_checks():
    """Every runtime assertion must reject a binary that is not ofhttp."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    tmp = tempfile.mkdtemp(prefix="ofhttp-runtime-selftest-")
    failures = []
    total = 0
    try:
        workdir = os.path.join(tmp, "wd")
        os.makedirs(workdir, exist_ok=True)
        for label, body in STUB_SCRIPTS:
            stub = _write_stub(tmp, label, body)
            for description, check in RUNTIME_CHECKS:
                total += 1
                try:
                    check(stub, workdir, base_url)
                except Exception as error:  # noqa: BLE001 - any rejection counts
                    print(f"  ok: rejected runtime [{label}] {description} -> "
                          f"{str(error).splitlines()[0][:80]}")
                else:
                    failures.append(f"{getattr(check, '__name__', check)} accepted "
                                    f"the {label} stub: {description}")
                    print(f"  FAIL: {description} accepted the {label} stub -- "
                          "ASSERTION IS A NO-OP")
    finally:
        server.shutdown()
        server.server_close()
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        raise AssertionError("; ".join(failures))
    print(f"ofhttp runtime proof: {total}/{total} runtime assertions rejected "
          f"every stub ({', '.join(label for label, _ in STUB_SCRIPTS)})")
    return total


# ----------------------------------------------------------------- self-test


def _mutations(package_folder):
    """(label, check, wants_executable, [break-one-thing steps])."""

    def remove(*parts):
        def step(root):
            os.remove(os.path.join(root, *parts))
        return step

    def write(rel, data, mode=None):
        def step(root):
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb" if isinstance(data, bytes) else "w") as handle:
                handle.write(data)
            if mode is not None:
                os.chmod(path, mode)
        return step

    def chmod_executable(mode):
        def step(root):
            os.chmod(os.path.join(root, "bin", "ofhttp"), mode)
        return step

    cases = [
        ("bin/ofhttp missing", check_executable_present, False, [remove("bin", "ofhttp")]),
        ("bin/ofhttp executable bits stripped",
         check_executable_present, False, [chmod_executable(0o644)]),
        ("bin/ofhttp is a shell script, not an ELF",
         check_elf_target, True, [write("bin/ofhttp", b"#!/bin/sh\nexit 0\n", 0o755)]),
        ("bin/ofhttp is an x86-64 ELF",
         check_elf_target, True,
         [write("bin/ofhttp", build_synthetic_elf(["libc.so"], e_machine=62), 0o755)]),
        ("bin/ofhttp links libobjfw at runtime",
         check_no_runtime_dependency, True,
         [write("bin/ofhttp", build_synthetic_elf(["libc.so", "libobjfw.so.1"]), 0o755)]),
        ("bin/ofhttp links libssl at runtime",
         check_no_runtime_dependency, True,
         [write("bin/ofhttp", build_synthetic_elf(["libc.so", "libssl.so", "libcrypto.so"]), 0o755)]),
        ("localization index no longer maps German",
         check_localization, False,
         [write("share/ofhttp/localization/localizations.json",
                "/* header */\n{ fr: { \"\": \"fr\" },\n}\n")]),
        ("localization index is not an object literal",
         check_localization, False,
         [write("share/ofhttp/localization/localizations.json", "not an object\n")]),
        ("de.json is not an object literal",
         check_localization, False,
         [write("share/ofhttp/localization/de.json", "/* header */\nusage: \"x\",\n")]),
        ("de.json lost the TLS message ofhttp renders",
         check_localization, False,
         [write("share/ofhttp/localization/de.json",
                "/* header */\n{\n usage: \"x\",\n full_usage: [\"y\"],\n}\n")]),
        ("man page is wget's, not ofhttp's",
         check_man_page, False, [write("share/man/man1/ofhttp.1", ".TH wget 1\n")]),
        ("COPYING.LESSER missing",
         check_licenses, False, [remove("licenses", "COPYING.LESSER")]),
        ("COPYING is not a license",
         check_licenses, False, [write("licenses/COPYING", "hello")]),
    ]
    return cases


def selftest(package_folder):
    """Every assertion must reject a copy of the real package broken in one way."""
    failures = []
    cases = _mutations(package_folder)
    for description, check, wants_executable, steps in cases:
        tmp = tempfile.mkdtemp(prefix="ofhttp-selftest-")
        broken = os.path.join(tmp, "pkg")
        try:
            shutil.copytree(package_folder, broken, symlinks=True)
            for step in steps:
                step(broken)
            target = os.path.join(broken, "bin", "ofhttp") if wants_executable else broken
            try:
                check(target)
            except Exception as error:  # noqa: BLE001 - any rejection counts
                print(f"  ok: rejected [{description}] -> {str(error).splitlines()[0][:88]}")
            else:
                failures.append(f"{check.__name__} accepted a package broken by: {description}")
                print(f"  FAIL: {check.__name__} accepted [{description}] -- ASSERTION IS A NO-OP")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    runtime_rejections = selftest_runtime_checks()

    if failures:
        raise AssertionError("; ".join(failures))
    print(f"ofhttp test_package self-test: {len(cases)}/{len(cases)} broken packages + "
          f"{runtime_rejections}/{runtime_rejections} runtime stubs, "
          f"every assertion rejected its own")


# ----------------------------------------------------------------------- main


def main():
    argv = sys.argv[1:]
    flags = [arg for arg in argv if arg.startswith("--")]
    positional = [arg for arg in argv if not arg.startswith("--")]
    if not positional:
        sys.stderr.write(__doc__)
        return 2
    package_folder = os.path.abspath(positional[0])

    if "--self-test" in flags:
        selftest(package_folder)
        return 0

    # Keep scratch files inside the test build folder: the CI worker runs with a
    # restricted TMPDIR, and mktemp-style dirs are exactly what the HMDFS
    # permission issue hits.
    workdir = os.path.join(os.getcwd(), "ofhttp_test_tmp")
    os.makedirs(workdir, exist_ok=True)

    executable, results = run_artifact_checks(package_folder)
    for label, detail in results:
        print(f"  ok: {label} -- {detail}")

    if "--no-run" in flags:
        print(f"ofhttp test_package: {len(results)} packaged-artifact checks passed "
              f"against {package_folder}; runtime checks skipped because the host "
              f"cannot execute os=OHOS arch=armv8 binaries")
        return 0
    for line in run_runtime_checks(executable, workdir):
        print("  ok: " + line)
    # Both counts come from the lists that were actually iterated, so a check
    # added to ARTIFACT_CHECKS/RUNTIME_CHECKS can never leave a stale number in
    # the summary (which is the line a reviewer reads as the pass rate).
    print(f"ofhttp test_package: {len(results)} artifact checks + "
          f"{RUNTIME_CHECK_COUNT} runtime checks passed against {executable}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
