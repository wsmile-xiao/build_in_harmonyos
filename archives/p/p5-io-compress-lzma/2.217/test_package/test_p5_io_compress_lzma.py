import json
import sys
from pathlib import Path


package_folder = Path(sys.argv[1])
perl_lib = Path(sys.argv[2])
expected_modules = [
    perl_lib / "IO" / "Compress" / "Lzma.pm",
    perl_lib / "IO" / "Compress" / "Xz.pm",
    perl_lib / "IO" / "Compress" / "Lzip.pm",
    perl_lib / "IO" / "Uncompress" / "UnLzma.pm",
    perl_lib / "IO" / "Uncompress" / "UnXz.pm",
    perl_lib / "IO" / "Uncompress" / "UnLzip.pm",
]

for path in expected_modules:
    if not path.is_file():
        raise SystemExit(f"missing packaged module: {path}")

lzma_pm = expected_modules[0].read_text(encoding="utf-8")
if "$VERSION = '2.217'" not in lzma_pm:
    raise SystemExit("IO::Compress::Lzma version marker was not packaged")
for adapter in ("Adapter/Lzma.pm", "Adapter/Xz.pm"):
    path = perl_lib / "IO" / "Compress" / adapter
    if not path.is_file():
        raise SystemExit(f"missing packaged compression adapter: {path}")

share = package_folder / "share" / "p5-io-compress-lzma"
upstream_t = share / "t"
expected_t = {
    "000prereq.t",
    "001lzip.t",
    "001lzma.t",
    "001xz.t",
    "010examples-lzma.t",
    "010examples-xz.t",
    "050interop-lzip.t",
    "050interop-lzma.t",
    "050interop-xz.t",
    "050interop-zip-lzma.t",
    "100generic-lzip.t",
    "100generic-lzma.t",
    "100generic-xz.t",
    "101truncate-lzip.t",
    "101truncate-lzma.t",
    "101truncate-xz.t",
    "102tied-lzip.t",
    "102tied-lzma.t",
    "102tied-xz.t",
    "103newtied-lzip.t",
    "103newtied-lzma.t",
    "103newtied-xz.t",
    "104destroy-lzip.t",
    "104destroy-lzma.t",
    "104destroy-xz.t",
    "105oneshot-lzip.t",
    "105oneshot-lzma.t",
    "105oneshot-xz.t",
    "105oneshot-zip-xz.t",
    "106prime-lzip.t",
    "106prime-lzma.t",
    "106prime-xz.t",
    "107multi-lzip.t",
    "107multi-lzma.t",
    "107multi-xz.t",
    "108anyunc-lzip.t",
    "108anyunc-lzma.t",
    "108anyunc-xz.t",
    "110encode-lzip.t",
    "110encode-lzma.t",
    "110encode-xz.t",
    "25interop-io-string.t",
    "999pod.t",
    "meta-json.t",
    "meta-yaml.t",
}
observed_t = {path.name for path in upstream_t.glob("*.t")}
if observed_t != expected_t:
    raise SystemExit(f"unexpected upstream .t test set: {sorted(observed_t)}")

for helper in [
    "Test/More.pm",
    "Test/Simple.pm",
    "Test/Builder.pm",
    "compress/CompTestUtils.pm",
    "compress/generic.pl",
    "compress/interop-io-string.pl",
    "files/lorem.txt",
    "files/winzip-eq-xz.zip",
]:
    path = upstream_t / helper
    if not path.is_file():
        raise SystemExit(f"missing upstream test helper: {helper}")

meta = json.loads((share / "META.json").read_text(encoding="utf-8"))
runtime_requires = meta["prereqs"]["runtime"]["requires"]
for module in ("Compress::Raw::Lzma", "IO::Compress::Base", "IO::Uncompress::Base"):
    if runtime_requires.get(module) != "2.217":
        raise SystemExit(f"META.json missing runtime prerequisite {module}=2.217")

prereq = (upstream_t / "000prereq.t").read_text(encoding="utf-8")
for module in ("Compress::Raw::Lzma", "IO::Compress::Base", "IO::Uncompress::Base"):
    if module not in prereq:
        raise SystemExit(f"upstream prereq test does not check {module}")

print("p5-io-compress-lzma modules and upstream CPAN tests are packaged")
