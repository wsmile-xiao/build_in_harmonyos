#!/usr/bin/env python3
"""Run the pinned NCL upstream fixtures with strict case and command counts.

The upstream Makefiles use a Python 2 driver and include two silent skips:
an absent ~/.ncl_round_triprc and an empty input directory. The driver patch
fixes Python 3 and empty directories; this wrapper supplies pinned fixture
counts and verifies every expected subprocess invocation happened.
"""

import argparse
import glob
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


NEXUS_PATTERNS = ("*.nex", "*.tre")
EXTERNAL_PATTERNS = (
    "*.dat", "*.phy", "*.fasta", "*.txt", "*.fas", "*.nex", "*.tre", "*.aln"
)


class TestFailure(Exception):
    pass


def absolute(path):
    return Path(os.path.abspath(os.fspath(path)))


def require_file(path, label):
    if not path.is_file():
        raise TestFailure(f"{label} is missing: {path}")


def discover(input_path, external):
    if input_path.is_file():
        return [input_path]
    if not input_path.is_dir():
        raise TestFailure(f"input path is missing: {input_path}")
    patterns = EXTERNAL_PATTERNS if external else NEXUS_PATTERNS
    files = [Path(name) for pattern in patterns
             for name in glob.glob(str(input_path / pattern))]
    return sorted(files)


def run_driver(*, name, driver, binary, flags, input_path, expected_dir,
               expected_count, expected_calls_per_case, work_root, results):
    files = discover(input_path, "-e" in flags)
    if len(files) != expected_count or not files:
        raise TestFailure(
            f"{name}: discovered {len(files)} fixture(s), expected {expected_count}"
        )
    if expected_dir is not None:
        if not expected_dir.is_dir():
            raise TestFailure(f"{name}: expected-output directory missing: {expected_dir}")
        missing = [str(expected_dir / item.name) for item in files
                   if not (expected_dir / item.name).is_file()]
        if missing:
            raise TestFailure(f"{name}: expected output missing: {', '.join(missing)}")

    case_dir = work_root / name
    case_dir.mkdir()
    stdout_path = case_dir / "stdout.log"
    stderr_path = case_dir / "stderr.log"
    command = [sys.executable, str(driver), *flags, str(binary), str(input_path)]
    if expected_dir is not None:
        command.append(str(expected_dir))
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        result = subprocess.run(command, cwd=case_dir, stdout=stdout, stderr=stderr,
                                check=False)
    actual_calls = sum(
        line.startswith(f'"{binary}"')
        for line in stderr_path.read_text(encoding="utf-8", errors="replace").splitlines()
    )
    expected_calls = expected_count * expected_calls_per_case
    print(f"{name}: discovered={len(files)} executed={actual_calls} "
          f"expected_executions={expected_calls} rc={result.returncode} "
          f"logs={case_dir}", flush=True)
    item = {"name": name, "discovered": len(files),
            "executed": actual_calls, "returncode": result.returncode,
            "stdout": str(stdout_path), "stderr": str(stderr_path),
            "status": "failed"}
    results.append(item)
    if result.returncode != 0:
        raise TestFailure(f"{name}: upstream driver failed; see {stderr_path}")
    if actual_calls != expected_calls:
        raise TestFailure(
            f"{name}: observed {actual_calls} binary calls, expected {expected_calls}; "
            f"see {stderr_path}"
        )
    item["status"] = "passed"


def run_converter_branch_case(*, converter, source_root, work_root, results):
    name = "converter-branch-length"
    input_path = source_root / "test/2NexmlIn/somebrlens.nex"
    require_file(input_path, name + " input")
    case_dir = work_root / name
    case_dir.mkdir()
    stdout_path = case_dir / "stdout.log"
    stderr_path = case_dir / "stderr.log"
    xml_path = case_dir / "out.xml"
    command = [str(converter), "-q", "-enexml", str(input_path)]
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        result = subprocess.run(command, cwd=case_dir, stdout=stdout, stderr=stderr,
                                check=False)
    print(f"{name}: discovered=1 executed=1 rc={result.returncode} "
          f"logs={case_dir}", flush=True)
    item = {"name": name, "discovered": 1, "executed": 1,
            "returncode": result.returncode, "stdout": str(stdout_path),
            "xml": str(xml_path), "stderr": str(stderr_path), "status": "failed"}
    results.append(item)
    if result.returncode != 0:
        raise TestFailure(f"{name}: converter failed; see {stderr_path}")
    require_file(xml_path, name + " NeXML output")
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as exc:
        raise TestFailure(f"{name}: converter produced invalid XML: {exc}") from exc
    local_name = lambda element: element.tag.rsplit("}", 1)[-1]
    if local_name(root) != "nexml":
        raise TestFailure(f"{name}: XML root is {root.tag}, expected nexml")
    nodes = list(root.iter())
    otu_count = sum(local_name(node) == "otu" for node in nodes)
    tree_count = sum(local_name(node) == "tree" for node in nodes)
    lengths = [float(node.attrib["length"]) for node in nodes
               if local_name(node) == "edge" and "length" in node.attrib]
    if otu_count != 4 or tree_count != 1 or not any(
        math.isclose(length, 0.3, rel_tol=0, abs_tol=1e-9) for length in lengths
    ):
        raise TestFailure(
            f"{name}: expected 4 OTUs, 1 tree and an edge of length 0.3; "
            f"got {otu_count} OTUs, {tree_count} trees, lengths={lengths}"
        )
    item.update({"status": "passed", "otus": otu_count, "trees": tree_count,
                 "edge_lengths": lengths})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--normalizer", required=True, type=Path)
    parser.add_argument("--converter", required=True, type=Path)
    parser.add_argument("--ncltest", required=True, type=Path)
    parser.add_argument("--translate", required=True, type=Path)
    parser.add_argument("--work-dir", type=Path, default=Path(tempfile.gettempdir()),
                        help="Parent directory for retained raw logs (default: system temp)")
    args = parser.parse_args()
    source_root = absolute(args.source_root)
    normalizer = absolute(args.normalizer)
    converter = absolute(args.converter)
    ncltest = absolute(args.ncltest)
    translate = absolute(args.translate)
    driver = source_root / "test/roundTripNCLTest.py"
    for label, path in (("test driver", driver), ("normalizer", normalizer),
                        ("converter", converter), ("ncltest", ncltest),
                        ("translate", translate)):
        require_file(path, label)
    # An H1 run may retain evidence outside the transient Conan build cache.
    base = absolute(os.environ.get("LIBNCL_EVIDENCE_DIR", args.work_dir))
    base.mkdir(parents=True, exist_ok=True)
    work_root = Path(tempfile.mkdtemp(prefix="libncl-upstream-", dir=base))
    print(f"source_root={source_root}\nraw_evidence={work_root}", flush=True)
    results = []
    status = "failed"
    try:
        groups = (
            ("normalizer-characters", normalizer, (), source_root / "data/characters.nex",
             source_root / "test/data", 1, 2),
            ("normalizer-sample-tree", normalizer, (), source_root / "data/sample.tre",
             source_root / "test/data", 1, 2),
            ("normalizer-nts-valid", normalizer, (), source_root / "test/NTSValidIn",
             source_root / "test/NTSValidOut", 31, 2),
            ("normalizer-funky-valid", normalizer, ("-x",), source_root / "test/funkyValidIn",
             source_root / "test/funkyValidOut", 1, 2),
            ("normalizer-external-valid", normalizer, ("-e",),
             source_root / "test/ExternalValidIn", source_root / "test/ExternalValidOut", 10, 2),
            ("normalizer-external-invalid", normalizer, ("-i", "-e"),
             source_root / "test/ExternalInvalidIn", None, 2, 1),
            ("normalizer-nts-invalid", normalizer, ("-i",),
             source_root / "test/NTSInvalidIn", None, 1, 1),
            ("ncltest-old-valid", ncltest, (), source_root / "test/OldValidIn",
             source_root / "test/OldValidOut", 1, 2),
            ("translate-valid", translate, ("-o",), source_root / "test/TranslateIn",
             source_root / "test/TranslateOut", 2, 1),
            ("converter-expected-xml", converter, ("-o", "-y", "-e"),
             source_root / "test/2NexmlIn/relaxedphyliptree_abc.tre",
             source_root / "test/2NexmlOut", 1, 1),
        )
        for name, binary, flags, input_path, expected_dir, count, calls in groups:
            run_driver(name=name, driver=driver, binary=binary, flags=flags,
                       input_path=input_path, expected_dir=expected_dir,
                       expected_count=count, expected_calls_per_case=calls,
                       work_root=work_root, results=results)
        run_converter_branch_case(converter=converter, source_root=source_root,
                                  work_root=work_root, results=results)
        total_discovered = sum(item["discovered"] for item in results)
        total_executed = sum(item["executed"] for item in results)
        if total_discovered != 52 or total_executed != 97:
            raise TestFailure(
                f"total mismatch: discovered={total_discovered}/52, "
                f"executed={total_executed}/97"
            )
        status = "passed"
        return_code = 0
    except (TestFailure, OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr, flush=True)
        return_code = 1
    finally:
        summary = {"status": status, "source_root": str(source_root),
                   "raw_evidence": str(work_root), "groups": results,
                   "total_discovered": sum(item["discovered"] for item in results),
                   "total_executed": sum(item["executed"] for item in results)}
        summary_path = work_root / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"SUMMARY status={status} discovered={summary['total_discovered']} "
              f"executed={summary['total_executed']} details={summary_path}", flush=True)
    return return_code


if __name__ == "__main__":
    sys.exit(main())
