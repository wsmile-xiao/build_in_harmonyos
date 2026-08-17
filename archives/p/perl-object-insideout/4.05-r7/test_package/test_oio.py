#!/usr/bin/env python3
"""Smoke test for perl-object-insideout 4.05-r7.

Called by test_package/conanfile.py via self.run().
Environment variables PERL5LIB and OIO_PM_PATH must be set by the caller.

Tests:
  1. Package structure: Object::InsideOut.pm exists at expected path
  2. Version verification: parse VERSION from .pm file
  3. Package content completeness: all 16 .pm sub-modules present
  4. Runtime module load: loads Object::InsideOut using bundled runtime
     dependencies (Devel::StackTrace, Class::Data::Inheritable,
     Exception::Class) from test_package/perl_lib/, then creates an
     object and verifies field get/set functionality.
"""
import os
import re
import shutil
import subprocess
import sys


# All .pm files that 'make install' produces (from Object-InsideOut-4.05)
EXPECTED_PM_FILES = [
    "Object/InsideOut.pm",
    "Object/InsideOut/Dynamic.pm",
    "Object/InsideOut/Autoload.pm",
    "Object/InsideOut/Universal.pm",
    "Object/InsideOut/Dump.pm",
    "Object/InsideOut/Cumulative.pm",
    "Object/InsideOut/Foreign.pm",
    "Object/InsideOut/Overload.pm",
    "Object/InsideOut/Secure.pm",
    "Object/InsideOut/lvalue.pm",
    "Object/InsideOut/Chained.pm",
    "Object/InsideOut/Metadata.pm",
    "Object/InsideOut/attributes.pm",
    "Object/InsideOut/Util.pm",
    "Object/InsideOut/Exception.pm",
    "Bundle/Object/InsideOut.pm",
]


def find_perl():
    """Find perl executable — OHOS posix_spawn doesn't search PATH (E051)."""
    perl = shutil.which("perl")
    if perl:
        return perl
    for candidate in (
        "/data/service/hnp/bin/perl",
        "/usr/bin/perl",
        "/usr/local/bin/perl",
    ):
        if os.path.isfile(candidate):
            return candidate
    return "perl"


def main():
    oio_pm_path = os.environ.get("OIO_PM_PATH", "")
    perl_bin = find_perl()
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Test 1: Verify Object::InsideOut.pm exists in package
    print("[test] 1/4: Verify package structure")
    if not oio_pm_path:
        print("FAIL: OIO_PM_PATH not set")
        sys.exit(1)
    if not os.path.isfile(oio_pm_path):
        print(f"FAIL: Object::InsideOut.pm not found at {oio_pm_path}")
        sys.exit(1)
    print("PASS: Object::InsideOut.pm found")

    # Test 2: Parse and verify version from .pm file
    print("[test] 2/4: Version verification")
    with open(oio_pm_path, "r") as f:
        content = f.read()
    m = re.search(r'\$VERSION\s*=\s*[\'"]([\d.]+)[\'"]', content)
    if not m:
        print("FAIL: VERSION not found in .pm file")
        sys.exit(1)
    ver = m.group(1)
    if ver != "4.05":
        print(f"FAIL: Version mismatch: expected 4.05, got {ver}")
        sys.exit(1)
    print(f"PASS: Object::InsideOut version {ver}")

    # Test 3: Verify all expected .pm files are present in the package
    print("[test] 3/4: Package content completeness")
    perl5lib = os.environ.get("PERL5LIB", "")
    if not perl5lib:
        print("FAIL: PERL5LIB not set")
        sys.exit(1)
    pkg_lib = None
    for path in perl5lib.split(":"):
        if os.path.isfile(os.path.join(path, "Object", "InsideOut.pm")):
            pkg_lib = path
            break
    if not pkg_lib:
        print(f"FAIL: Cannot find package lib/perl5/ in PERL5LIB={perl5lib}")
        sys.exit(1)
    missing = []
    for rel_path in EXPECTED_PM_FILES:
        full_path = os.path.join(pkg_lib, rel_path)
        if not os.path.isfile(full_path):
            missing.append(rel_path)
    if missing:
        print(f"FAIL: {len(missing)} .pm file(s) missing from package:")
        for f in missing:
            print(f"       - {f}")
        sys.exit(1)
    print(f"PASS: All {len(EXPECTED_PM_FILES)} .pm files present in package")

    # Test 4: Runtime module load test
    # Object::InsideOut has a hard runtime dependency on Exception::Class
    # (which depends on Class::Data::Inheritable and Devel::StackTrace).
    # These are not yet in the Conan registry. The .pm files are bundled
    # in test_package/perl_lib/ to avoid network downloads at test time.
    print("[test] 4/4: Runtime module load test")
    bundled_lib = os.path.join(script_dir, "perl_lib")
    if not os.path.isdir(bundled_lib):
        print(f"FAIL: Bundled dependency lib not found at {bundled_lib}")
        sys.exit(1)

    # Build PERL5LIB: package lib + bundled deps
    all_libs = [pkg_lib, bundled_lib]
    full_perl5lib = ":".join(all_libs)

    # Write Perl test to a temp file to avoid -e quoting issues
    import tempfile
    tmpdir = os.environ.get("TMPDIR", tempfile.gettempdir())
    perl_test = os.path.join(tmpdir, "oio_runtime_test.py.pl")
    perl_code = r'''
package My::Test::OIO;
use Object::InsideOut;
my @data :Field :Get('get_data') :Set('set_data') :Default(0);

package main;
my $obj = My::Test::OIO->new();
$obj->set_data(42);
die "FAIL: get_data=" . $obj->get_data() . " (expected 42)\n"
    unless $obj->get_data() == 42;
$obj->set_data(100);
die "FAIL: get_data=" . $obj->get_data() . " (expected 100)\n"
    unless $obj->get_data() == 100;
print "OK: Object::InsideOut loaded and functional, version $Object::InsideOut::VERSION\n";
'''
    with open(perl_test, "w") as f:
        f.write(perl_code)

    env = {**os.environ, "PERL5LIB": full_perl5lib}
    result = subprocess.run(
        [perl_bin, perl_test],
        capture_output=True, text=True, env=env, timeout=30,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        print(f"FAIL: Module load/functional test failed:\n{output}")
        sys.exit(1)
    print(output, end="")

    print("All tests passed.")


if __name__ == "__main__":
    main()
