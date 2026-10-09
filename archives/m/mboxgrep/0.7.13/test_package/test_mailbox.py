"""Dependency-free installed-binary consumer test on HarmonyOS PC."""

import os
import subprocess
import sys
import tempfile


MBOX = (
    "From first@example.invalid Tue Sep 29 12:00:00 2026\n"
    "Subject: Alpha\n"
    "From: first@example.invalid\n"
    "\n"
    "first body needle\n"
    "\n"
    "From second@example.invalid Tue Sep 29 12:01:00 2026\n"
    "Subject: Beta\n"
    "From: second@example.invalid\n"
    "\n"
    "second body only\n"
    "\n"
)


def run(binary, *args):
    return subprocess.run(
        [binary, *args], capture_output=True, text=True, check=False
    )


def main(binary):
    version = run(binary, "--version")
    assert version.returncode == 0 and "mboxgrep 0.7.13" in version.stdout, version

    with tempfile.TemporaryDirectory(
        prefix="mboxgrep-consumer-", dir="/data/storage/el2/base/cache"
    ) as work:
        mailbox = os.path.join(work, "two-messages.mbox")
        with open(mailbox, "w", encoding="ascii", newline="\n") as stream:
            stream.write(MBOX)

        count = run(binary, "-c", "needle", mailbox)
        assert count.returncode == 0 and count.stdout.strip() == "1", count

        extended = run(binary, "-E", "-c", "Alpha|Beta", mailbox)
        assert extended.returncode == 0 and extended.stdout.strip() == "2", extended

        headers = run(binary, "-H", "-c", "Alpha", mailbox)
        assert headers.returncode == 0 and headers.stdout.strip() == "1", headers

        unsupported = run(binary, "-P", "-c", "Alpha", mailbox)
        assert unsupported.returncode == 2 and "Perl" in unsupported.stderr, unsupported

    print("PASS: installed mboxgrep 0.7.13, POSIX patterns and PCRE2 boundary")


if __name__ == "__main__":
    main(sys.argv[1])
