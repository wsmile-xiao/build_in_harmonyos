"""Reproduce the test census of the checksum-pinned libydpdict 1.0.4 release.

This reads literal assignments in this release only. It is not an Automake
interpreter and refuses variable expansion, continuations or repeated assignments.
No archive member is extracted and no build/runtime result is inferred.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

SHA256 = "37dcbc12def981a20728bdcb6a5ff1eef8931f29a0f16852f0b2201ff8563528"


def literal_assignment(text, variable):
    assignments = re.findall(r"^" + re.escape(variable) + r"\s*([+:?]?=)\s*(.*)$", text, re.MULTILINE)
    if not assignments:
        return []
    if len(assignments) != 1 or assignments[0][0] != "=":
        raise ValueError("Unsupported assignment: " + variable)
    value = assignments[0][1]
    if any(char in value for char in "$\\#"):
        raise ValueError("Nonliteral assignment: " + variable)
    return value.split()


def inspect_release(path):
    data = Path(path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        raise ValueError("SHA256 mismatch: " + digest)
    with tarfile.open(path, "r:gz") as archive:
        def read(relative):
            with archive.extractfile("libydpdict-1.0.4/" + relative) as stream:
                return stream.read().decode("utf-8")

        top = read("Makefile.am")
        misc = read("misc/Makefile.am")
        return {
            "sha256": digest,
            "archive_members": len(archive.getmembers()),
            "subdirs": literal_assignment(top, "SUBDIRS"),
            "dist_subdirs": literal_assignment(top, "DIST_SUBDIRS"),
            "misc_in_subdirs": "misc" in literal_assignment(top, "SUBDIRS"),
            "misc_in_dist_subdirs": "misc" in literal_assignment(top, "DIST_SUBDIRS"),
            "check_programs": literal_assignment(misc, "check_PROGRAMS"),
            "tests": literal_assignment(misc, "TESTS"),
            "runtime_result": "not measured by source census",
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-archive", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect_release(args.source_archive), ensure_ascii=False, indent=2))
