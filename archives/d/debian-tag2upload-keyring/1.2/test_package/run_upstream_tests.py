#!/usr/bin/env python3
"""Execute the upstream autopkgtest `debian/tests/verify-one` unmodified.

The single upstream test is run from a byte-identical copy of the upstream
script, and it is pointed at the *packaged* keyring: the script resolves the
keyring as "$PWD/debian-tag2upload.pgp", so the package's own
share/keyrings/debian-tag2upload.pgp is staged under that name. The upstream
script therefore performs a real end-to-end check of the delivered artifact —
no upstream file is patched, no assertion is replaced, and the only substitution
is the missing `rsop` binary, which rsop.py implements.

A pass alone would not prove the substitution can fail, so four mutated inputs
are pushed through the same unmodified script and every one of them must be
rejected: a tampered tag object (changes the signed plaintext), a tampered
signature MPI, a keyring whose RSA modulus was replaced, and an empty keyring.

Every one of those checks is counted and the count is printed, at the same
granularity the other two programs use (each mutation control is one
assertion, not one rolled-up aggregate), so the totals quoted in
MANIFEST.yml are measured rather than hand-derived.
"""

import base64
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from rsop import dearmor  # noqa: E402

UPSTREAM = HERE / "upstream"
RSOP = HERE / "rsop.py"
PINS = HERE / "upstream-test.sha256"
KEYRING_NAME = "debian-tag2upload.pgp"
ENV_KEYRING_DIR = "OPENPGP_KEYRING_DIR"


class RunError(Exception):
    pass


class Counter:
    """Counts the checks this program makes, at one assertion per check.

    Counted individually on purpose: each mutation control below is a separate
    assertion, matching how test_verify.py and test_consumer_e2e.py count
    theirs, so the three programs' totals can be added up honestly.
    """

    def __init__(self):
        self.assertions = 0

    def check(self, condition, message):
        self.assertions += 1
        if not condition:
            raise RunError(message)


def read_pins():
    pins = {}
    for line in PINS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, name = line.split(None, 1)
        pins[name.strip()] = digest
    return pins


def check_pins(counter):
    pins = read_pins()
    counter.check(bool(pins), "no pinned hashes found in %s" % PINS.name)
    for name, expected in sorted(pins.items()):
        path = UPSTREAM / name
        counter.check(path.is_file(), "upstream input %s is missing" % name)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        counter.check(
            actual == expected,
            "upstream input %s drifted: sha256 %s, expected %s"
            % (name, actual, expected))
    return pins


def locate_keyring(counter):
    keyring_dir = os.environ.get(ENV_KEYRING_DIR)
    counter.check(
        bool(keyring_dir),
        "%s is not set: package_info() must inject it so the upstream "
        "test consumes the delivered artifact" % ENV_KEYRING_DIR)
    path = pathlib.Path(keyring_dir) / KEYRING_NAME
    counter.check(path.is_file(), "no keyring at %s" % path)
    return path


def make_rsop_wrapper(bin_dir, interpreter):
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "rsop"
    wrapper.write_text(
        '#!/bin/sh\nexec "%s" "%s" "$@"\n' % (interpreter, RSOP),
        encoding="utf-8")
    wrapper.chmod(0o755)
    return wrapper


def stage(work_dir, keyring_bytes, tag_object_bytes):
    root = work_dir / "root"
    tmp = work_dir / "apkgtest"
    for directory in (root, tmp):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)
    (root / "test-tag-object").write_bytes(tag_object_bytes)
    (root / KEYRING_NAME).write_bytes(keyring_bytes)
    (root / "debian" / "tests").mkdir(parents=True)
    shutil.copyfile(UPSTREAM / "debian" / "tests" / "verify-one",
                    root / "debian" / "tests" / "verify-one")
    (root / "debian" / "tests" / "verify-one").chmod(0o755)
    return root, tmp


def run_upstream_verify_one(bash, root, tmp, bin_dir, expect_pass, counter=None):
    env = dict(os.environ)
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    env["AUTOPKGTEST_TMP"] = str(tmp)
    # The upstream script resolves the keyring as "$PWD/debian-tag2upload.pgp",
    # so $PWD must name the staged directory. On the OHOS worker filesystem
    # getcwd() can fail ("cannot access parent directories: Not supported"),
    # and bash then keeps whatever PWD it inherited, which silently points the
    # upstream script at the wrong tree. Passing PWD explicitly makes the
    # script correct whether or not getcwd() works.
    env["PWD"] = str(root)
    proc = subprocess.run(
        [str(bash), "debian/tests/verify-one"],
        cwd=str(root), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = proc.stdout.decode("utf-8", "replace")
    passed = proc.returncode == 0 and output.rstrip().endswith("ok.")
    if counter is not None:
        # A control run is asserted by the caller (it must be rejected *and* the
        # rejection must come from the verifier), so only the real run is
        # counted here.
        counter.check(
            expect_pass == passed,
            ("upstream debian/tests/verify-one failed:\n%s" if expect_pass else
             "upstream debian/tests/verify-one accepted a tampered input, so "
             "the check is vacuous:\n%s") % output)
    if expect_pass and not passed:
        raise RunError("upstream debian/tests/verify-one failed:\n%s" % output)
    if not expect_pass and passed:
        raise RunError("upstream debian/tests/verify-one accepted a "
                       "tampered input, so the check is vacuous:\n%s" % output)
    return proc.returncode, output


def assert_script_saw_staged_root(output, root, counter):
    """The upstream script resolves the keyring as "$PWD/debian-tag2upload.pgp".
    `set -x` echoes that assignment, so a wrong $PWD is visible here rather than
    surfacing later as a confusing "No such file" from perl."""
    resolved = []
    for line in output.splitlines():
        text = line.strip()
        if text.startswith("+ root="):
            resolved.append(text[len("+ root="):].strip())
    counter.check(
        bool(resolved),
        "upstream script never echoed `root=` under set -x, so the assertion "
        "that it saw the staged directory cannot be made")
    if resolved and resolved[0] != str(root):
        raise RunError("upstream script resolved root=%r, expected %r; $PWD did "
                       "not reach the staged directory" % (resolved[0], str(root)))


def split_fixture(tag_object_bytes):
    marker = b"-----BEGIN PGP SIGNATURE-----"
    index = tag_object_bytes.find(marker)
    if index < 0:
        raise RunError("test-tag-object carries no armored signature")
    return tag_object_bytes[:index], tag_object_bytes[index:]


def tamper_plaintext(tag_object_bytes):
    head, signature = split_fixture(tag_object_bytes)
    needle = b"dgit-test-dummy"
    if needle not in head:
        raise RunError("unexpected fixture layout: tag marker not found")
    return head.replace(needle, b"dgit-test-dumyy", 1) + signature


def armor_crc24(data):
    crc = 0xB704CE
    for byte in data:
        crc ^= byte << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= 0x1864CFB
    return crc & 0xFFFFFF


def rearmor(binary, label):
    """Re-encode as ASCII armor. `label` is the part after "PGP ", so a
    detached signature takes "SIGNATURE" and the header reads
    `-----BEGIN PGP SIGNATURE-----`."""
    encoded = base64.b64encode(binary).decode("ascii")
    lines = [encoded[i:i + 64] for i in range(0, len(encoded), 64)]
    crc = base64.b64encode(armor_crc24(binary).to_bytes(3, "big")).decode()
    return ("-----BEGIN PGP %s-----\n\n%s\n=%s\n-----END PGP %s-----\n"
            % (label, "\n".join(lines), crc, label)).encode("ascii")


def tamper_fixture_signature(tag_object_bytes):
    head, armor_block = split_fixture(tag_object_bytes)
    binary = dearmor(armor_block)
    mutated = bytearray(binary)
    position = len(mutated) - 40
    mutated[position] ^= 0x01
    # The label must stay exactly "SIGNATURE": the upstream splitter matches
    # ^-----BEGIN PGP SIGNATURE-----$ verbatim, so a doubled "PGP PGP SIGNATURE"
    # would leave signature.asc unwritten and the control would then "fail"
    # because the file is missing rather than because the MPI is rejected.
    return head + rearmor(bytes(mutated), "SIGNATURE")


def tamper_keyring_modulus(keyring_bytes):
    index = 0
    while index < len(keyring_bytes):
        ctb = keyring_bytes[index]
        if not ctb & 0x80:
            raise RunError("keyring header 0x%02x has bit 7 clear" % ctb)
        if ctb & 0x40:
            tag = ctb & 0x3F
            index += 1
            first = keyring_bytes[index]
            if first < 192:
                length, index = first, index + 1
            elif first < 224:
                length = ((first - 192) << 8) + keyring_bytes[index + 1] + 192
                index += 2
            else:
                length = int.from_bytes(keyring_bytes[index + 1:index + 5],
                                        "big")
                index += 5
        else:
            tag = (ctb & 0x3C) >> 2
            length_type = ctb & 0x03
            index += 1
            if length_type == 0:
                length, index = keyring_bytes[index], index + 1
            elif length_type == 1:
                length = int.from_bytes(keyring_bytes[index:index + 2], "big")
                index += 2
            else:
                length = int.from_bytes(keyring_bytes[index:index + 4], "big")
                index += 4
        body_start = index
        if tag == 6:
            bits = int.from_bytes(keyring_bytes[body_start + 6:body_start + 8],
                                  "big")
            value_len = (bits + 7) // 8
            value_start = body_start + 8
            if value_len < 8 or value_start + value_len > len(keyring_bytes):
                raise RunError("unexpected keyring modulus layout")
            position = value_start + value_len // 2
            mutated = bytearray(keyring_bytes)
            mutated[position] ^= 0x01
            return bytes(mutated)
        index = body_start + length
    raise RunError("no public-key packet in the keyring")


def assert_rejected_by_verification(output, name, counter):
    """A control must be refused by the verifier, not by some incidental
    breakage. Without this a malformed fixture (a missing signature file, an
    unreadable path) would satisfy "the run failed" while proving nothing about
    signature checking."""
    counter.check(
        "No such file or directory" not in output,
        "mutation control %r failed on a missing file rather than on signature "
        "verification:\n%s" % (name, output))
    counter.check(
        "rsop: verification failed" in output,
        "mutation control %r did not reach the verifier's own rejection:\n%s"
        % (name, output))


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: run_upstream_tests.py <workdir> <bash>\n")
        return 2
    work_dir, bash = pathlib.Path(argv[1]), argv[2]
    interpreter = sys.executable
    counter = Counter()
    try:
        pins = check_pins(counter)
        keyring_path = locate_keyring(counter)
        keyring_bytes = keyring_path.read_bytes()
        tag_object_bytes = (UPSTREAM / "test-tag-object").read_bytes()

        bin_dir = work_dir / "bin"
        make_rsop_wrapper(bin_dir, interpreter)

        root, tmp = stage(work_dir, keyring_bytes, tag_object_bytes)
        code, output = run_upstream_verify_one(
            bash, root, tmp, bin_dir, True, counter)
        assert_script_saw_staged_root(output, root, counter)
        verdict = [line for line in output.splitlines()
                   if line.startswith("rsop: good signature")]
        counter.check(
            bool(verdict),
            "upstream test exited 0 but rsop reported no good signature:\n%s"
            % output)

        cases = [
            ("tag-object-plaintext-tampered",
             tamper_plaintext(tag_object_bytes), keyring_bytes),
            ("signature-mpi-tampered",
             tamper_fixture_signature(tag_object_bytes), keyring_bytes),
            ("keyring-rsa-modulus-replaced",
             tag_object_bytes, tamper_keyring_modulus(keyring_bytes)),
            ("keyring-empty", tag_object_bytes, b""),
        ]
        controls = []
        for name, fixture_bytes, keyring in cases:
            case_root, case_tmp = stage(work_dir, keyring, fixture_bytes)
            try:
                _, control_output = run_upstream_verify_one(
                    bash, case_root, case_tmp, bin_dir, False)
            except RunError as exc:
                raise RunError("mutation control %r did not fail: %s"
                               % (name, exc))
            assert_rejected_by_verification(control_output, name, counter)
            controls.append(name)
    except (RunError, OSError) as exc:
        sys.stderr.write("TAG2UPLOAD_UPSTREAM_TEST_FAIL: %s\n" % exc)
        return 1

    print("TAG2UPLOAD_UPSTREAM_TEST_PASS upstream_test=debian/tests/verify-one "
          "assertions=%d script_sha256=%s fixture_sha256=%s control_sha256=%s"
          % (counter.assertions,
             pins["debian/tests/verify-one"],
             pins["test-tag-object"], pins["debian/tests/control"]))
    print("  keyring: %s" % keyring_path)
    print("  verifier: rsop.py (pure-python RFC 4880 + RSA PKCS#1 v1.5) "
          "replacing the absent rsop binary")
    print("  %s" % verdict[0])
    print("  mutation controls rejected: %s" % ", ".join(controls))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
