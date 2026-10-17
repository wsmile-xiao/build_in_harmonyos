import pathlib
import re
import subprocess
import sys

source, build = map(pathlib.Path, sys.argv[1:3])
total = 0
for executable, count in (("UrlBuilderTest", 32), ("JsonCreatorTest", 5)):
    header = (source / "tests" / (executable + ".h")).read_text(encoding="utf-8")
    expected = re.findall(r"void\s+(test\w+)\s*\(\s*\)\s*;", header)
    binary = str(build / "tests" / executable)
    listing = subprocess.run([binary, "-functions"], capture_output=True, text=True, timeout=30)
    actual = re.findall(r"^(\w+)\(\)$", listing.stdout, re.M)
    if listing.returncode or len(set(expected)) != count or actual != expected:
        raise RuntimeError(("upstream test inventory mismatch", executable, expected, actual, listing.stderr))
    result = subprocess.run([binary, "-txt"], capture_output=True, text=True, timeout=120)
    print(result.stdout, flush=True)
    print(result.stderr, file=sys.stderr, flush=True)
    passed = re.findall(r"^PASS\s*:\s*(?:\w+::)+(test\w+)\(\)", result.stdout, re.M)
    if result.returncode or passed != expected:
        raise RuntimeError(("upstream test failure", executable, passed))
    for name in passed:
        print("UPSTREAM_CASE", executable + "." + name, "PASSED", flush=True)
    total += len(passed)
if total != 37:
    raise RuntimeError("upstream denominator changed")
print("LIBMYGPO_UPSTREAM_RESULT=37/37", flush=True)
