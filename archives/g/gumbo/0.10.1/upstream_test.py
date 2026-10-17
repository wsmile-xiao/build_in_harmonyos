"""Build the exact upstream Makefile.am test sources and run every GoogleTest.

GoogleTest is a hash-pinned, test-only source input, not a runtime dependency.
An XML terminal result, rather than a count of source macros, is authoritative.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET


C_SOURCES = ("attribute", "char_ref", "error", "parser", "string_buffer",
             "string_piece", "tag", "tokenizer", "utf8", "util", "vector")
TEST_SOURCES = ("attribute", "char_ref", "parser", "string_buffer", "string_piece",
                "tokenizer", "test_utils", "utf8", "vector")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--compiler", required=True)
    parser.add_argument("--cxx", required=True)
    parser.add_argument("--native-ohos", action="store_true")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    objects = []

    def call(argv, label, timeout=180):
        result = subprocess.run(argv, capture_output=True, timeout=timeout, cwd=source,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        (output / (label + ".stdout")).write_bytes(result.stdout)
        (output / (label + ".stderr")).write_bytes(result.stderr)
        if result.returncode:
            raise RuntimeError(f"{label}: RC={result.returncode}: " +
                               result.stderr.decode(errors="replace")[-4000:])
        return result.stdout

    for name in C_SOURCES:
        obj = output / (name + ".o")
        call([args.compiler, "-O1", "-DNDEBUG", "-c", str(source / "src" / (name + ".c")),
              "-o", str(obj)], "c-" + name)
        objects.append(str(obj))
    includes = ["-I" + str(source), "-I" + str(source / "src"),
                "-I" + str(source / "gtest/include"), "-I" + str(source / "gtest")]
    for name in TEST_SOURCES:
        obj = output / ("test-" + name + ".o")
        call([args.cxx, "-std=c++11", "-O1", "-DNDEBUG", *includes, "-c",
              str(source / "tests" / (name + ".cc")), "-o", str(obj)], "test-" + name)
        objects.append(str(obj))
    for name in ("gtest-all", "gtest_main"):
        obj = output / (name + ".o")
        call([args.cxx, "-std=c++11", "-O1", *includes, "-c",
              str(source / "gtest/src" / (name + ".cc")), "-o", str(obj)], name)
        objects.append(str(obj))
    binary = output / ("gumbo_test.exe" if os.name == "nt" else "gumbo_test")
    call([args.cxx, *objects, "-pthread", "-o", str(binary)], "link")
    if args.native_ohos:
        if os.uname().sysname != "HarmonyOS" or os.uname().machine != "aarch64":
            raise RuntimeError("Not native HarmonyOS/aarch64")
        signer = shutil.which("binary-sign-tool")
        if not signer:
            raise RuntimeError("Native binary-sign-tool required")
        signed = output / "gumbo_test.signed"
        call([signer, "sign", "-selfSign", "1", "-inFile", str(binary),
              "-outFile", str(signed)], "sign")
        signed.chmod(0o700)
        binary = signed
    listing = call([str(binary), "--gtest_list_tests"], "inventory")
    # The upstream framework supplies actual registered IDs including fixtures.
    suite, ids = "", []
    for line in listing.decode().splitlines():
        if line.startswith("  "):
            ids.append(suite + line.strip().split(" #", 1)[0])
        elif line.endswith("."):
            suite = line.strip()
    if not ids or len(ids) != len(set(ids)) or any("DISABLED_" in x for x in ids):
        raise RuntimeError("Empty, duplicate, or disabled upstream inventory")
    (output / "inventory.txt").write_text("UPSTREAM_TEST_COUNT=" + str(len(ids)) +
                                           "\n" + "\n".join(ids) + "\n", encoding="utf-8")
    xml = output / "result.xml"
    stdout = call([str(binary), "--gtest_output=xml:" + str(xml)], "run")
    root = ET.parse(xml).getroot()
    cases = root.findall(".//testcase")
    completed = [x.attrib["classname"] + "." + x.attrib["name"] for x in cases]
    if (sorted(completed) != sorted(ids) or any(x.attrib.get("status") != "run" for x in cases)
            or root.attrib.get("failures") != "0" or root.attrib.get("errors") != "0"
            or any(x.find("failure") is not None for x in cases)):
        raise RuntimeError("Upstream terminal XML/inventory mismatch")
    result = {"total": len(ids), "passed": len(cases), "failed": 0, "skipped": 0}
    (output / "result.json").write_text(json.dumps(result) + "\n", encoding="utf-8")
    print(stdout.decode(errors="replace"))
    print(f"UPSTREAM_TEST_PASS={len(ids)}/{len(ids)}")


if __name__ == "__main__":
    main()
