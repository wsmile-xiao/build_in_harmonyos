"""Consumer smoke test for the packaged CPython extension modules."""
import glob
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def uses_readonly_hnp_runtime():
    public_home = os.environ.get("HNP_PUBLIC_HOME")
    platlib = sysconfig.get_path("platlib")
    if not public_home or not platlib:
        return False
    public_home = os.path.realpath(public_home)
    platlib = os.path.realpath(platlib)
    return platlib == public_home or platlib.startswith(public_home + os.sep)


def is_native_loader_denial(error):
    detail = str(error).lower()
    return ".so" in detail and (
        "permission denied" in detail or "operation not permitted" in detail
    )


package_folder = sys.argv[1]
packages = glob.glob(os.path.join(package_folder, "lib", "python*", "site-packages", "libscrc"))
require(len(packages) == 1, "expected one packaged libscrc Python package")

def verify_extensions_static():
    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    require(readelf is not None, "E212 fallback requires llvm-readelf or readelf")
    extensions = sorted(glob.glob(os.path.join(packages[0], "_*.so")))
    require(len(extensions) == 7, "expected seven packaged extensions, found {}".format(len(extensions)))
    suffix = sysconfig.get_config_var("EXT_SUFFIX")
    for path in extensions:
        name = os.path.basename(path)
        module = name.split(".", 1)[0]
        require(suffix and name.endswith(suffix), "{} does not match active CPython ABI {}".format(name, suffix))
        with open(path, "rb") as stream:
            require(stream.read(4) == b"\x7fELF", "{} is not ELF".format(name))
        result = subprocess.run([readelf, "-h", "--dyn-syms", path],
                                capture_output=True, text=True)
        require(result.returncode == 0, "readelf failed for {}: {}".format(name, result.stderr.strip()))
        require("AArch64" in result.stdout, "{} is not an AArch64 extension".format(name))
        require(re.search(r"\bPyInit_{}\b".format(re.escape(module)), result.stdout) is not None,
                "{} lacks its CPython initialization symbol".format(name))
    print("CONSUMER_STATIC_CHECKS: PASS=7/7")

# Exercise the consumer API from the active interpreter's supported native-
# module directory. HNP workers have a read-only platlib and E212/E502 block
# dlopen from user paths, so only that environment uses the explicit ELF check.
tmp_root = sysconfig.get_path("platlib")
if not tmp_root or not os.path.isdir(tmp_root) or not os.access(tmp_root, os.W_OK | os.X_OK):
    if not uses_readonly_hnp_runtime():
        raise PermissionError("active Python platlib is unavailable or not writable: {}".format(tmp_root))
    verify_extensions_static()
    print("E212/E502: CPython runtime tests NOT RUN (HNP platlib is read-only; worker blocks dlopen from user paths)")
    print("CONSUMER_TESTS: NOT_RUN=2 (E212/E502 HNP loader policy)")
    print("CONSUMER_RUNTIME_TESTS: NOT_RUN=2")
    sys.exit(0)
tmp = tempfile.mkdtemp(prefix="libscrc-consumer-", dir=tmp_root)
print("CONSUMER_TMPDIR: {}".format(tmp_root))
try:
    shutil.copytree(packages[0], os.path.join(tmp, "libscrc"))
    sys.path.insert(0, tmp)
    try:
        import libscrc
    except (ImportError, OSError) as exc:
        if uses_readonly_hnp_runtime() and is_native_loader_denial(exc):
            print("E212/E502: CPython runtime tests NOT RUN (HNP worker denied dlopen: {})".format(exc))
            verify_extensions_static()
            print("CONSUMER_TESTS: NOT_RUN=2 (E212/E502 HNP loader policy)")
            print("CONSUMER_RUNTIME_TESTS: NOT_RUN=2")
            sys.exit(0)
        raise

    require(libscrc.modbus(b"123456789") == 0x4B37, "CRC-16/MODBUS vector mismatch")
    require(libscrc.crc32(b"123456789") == 0xCBF43926, "CRC-32/ISO-HDLC vector mismatch")
    print("CONSUMER_TESTS: PASS=2/2 FAIL=0")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
