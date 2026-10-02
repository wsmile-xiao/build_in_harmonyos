import glob
import os
import subprocess
import sysconfig


def _is_hnp_dlopen_eacces(message):
    contexts = ("Error loading shared library", "Error relocating", "cannot open shared object file")
    suffixes = (": Permission denied", ": EACCES")
    return any(any(context in line for context in contexts)
               and any(suffix in line for suffix in suffixes)
               for line in str(message).splitlines())


try:
    import tinyarray
except ImportError as error:
    if not _is_hnp_dlopen_eacces(error):
        raise
    extensions = [path for site in os.environ.get("PYTHONPATH", "").split(os.pathsep)
                  for path in glob.glob(os.path.join(site, "tinyarray*.so"))]
    if not extensions:
        raise AssertionError("HNP EACCES fallback found no tinyarray extension")
    for extension in extensions:
        with open(extension, "rb") as stream:
            image = stream.read()
        if not image.startswith(b"\x7fELF"):
            raise AssertionError("tinyarray extension is not ELF: {}".format(extension))
        if b".codesign" not in image:
            raise AssertionError("tinyarray extension lacks .codesign section: {}".format(extension))
    print("HNP EACCES: {} signed ELF extension(s) statically verified".format(len(extensions)))
    raise SystemExit(0)


assert tinyarray.dot(tinyarray.array([[1, 2], [3, 4]]), tinyarray.array([[1], [2]])) == tinyarray.array([[5], [11]])
assert tinyarray.array([1, 2, 3]) + tinyarray.array([4, 5, 6]) == tinyarray.array([5, 7, 9])
assert tinyarray.__file__.endswith(sysconfig.get_config_var("EXT_SUFFIX"))

# HarmonyOS/AArch64 regression: 2**63 is representable as double but outside
# signed long. The cast must not determine whether OverflowError is raised.
try:
    tinyarray.array(float(2**63), int)
except OverflowError:
    pass
else:
    raise AssertionError("float 2**63 must raise OverflowError when converted to long")

assert tinyarray.array(float(-(2**63)), int) == tinyarray.array(-(2**63), int)
assert tinyarray.array(float(2**63 - 1024), int) == tinyarray.array(2**63 - 1024, int)

try:
    tinyarray.array(float(-(2**63) - 2048), int)
except OverflowError:
    pass
else:
    raise AssertionError("float below -2**63 must raise OverflowError when converted to long")

print("ASSERTIONS: 7, FAILURES: 0")
