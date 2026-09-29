#!/usr/bin/env python3
"""test_package consumer test for ml-dtypes 0.5.4 on HarmonyOS PC.

Imports the packaged ``ml_dtypes`` (wrapper + signed C++ extension) and really
exercises its API.  7 independent checkpoints; any failure exits with code 1.

Checkpoints
-----------
1. ``ml_dtypes`` imports and reports the expected version
2. ``bfloat16`` construction + NumPy array round-trip
3. ``float8_e4m3fn`` round-trip (incl. non-finite handling)
4. ``int4`` / ``uint4`` round-trip
5. ``finfo`` / ``iinfo`` reflection
6. dtype interop: cast to/from ``numpy`` and use in a NumPy ufunc
7. **HarmonyOS-only check**: the extension module is a *signed* OHOS aarch64 ELF
   (``…aarch64-linux-ohos.so`` platform tag + ELF magic + ``.codesign`` section),
   which is what makes ``dlopen`` succeed on HarmonyOS (E077 / ML-0043).
"""

import os
import sys

import numpy as np

failures = []


def check(name, cond, detail=""):
    print("%s: %s%s" % ("PASS" if cond else "FAIL", name,
                        ("  [%s]" % detail) if detail else ""))
    if not cond:
        failures.append(name)


# 1. import + version
import ml_dtypes  # noqa: E402  (import after numpy on purpose)

check("import_ml_dtypes", ml_dtypes.__version__ == "0.5.4",
      "version=%s" % ml_dtypes.__version__)

# 2. bfloat16 round-trip
bf = ml_dtypes.bfloat16
a = np.array([1.0, -2.5, 0.0, 255.0], dtype=bf)
check("bfloat16_roundtrip",
      list(np.array(a, dtype=np.float32)) == [1.0, -2.5, 0.0, 255.0],
      str(a.astype(np.float32).tolist()))

# 3. float8_e4m3fn round-trip
f8 = ml_dtypes.float8_e4m3fn
b = np.array([1.0, -0.5, 448.0], dtype=f8)
check("float8_e4m3fn_roundtrip",
      list(np.array(b, dtype=np.float32)) == [1.0, -0.5, 448.0],
      str(b.astype(np.float32).tolist()))

# 4. int4 / uint4 round-trip
i4, u4 = ml_dtypes.int4, ml_dtypes.uint4
c = np.array([-8, -1, 0, 7], dtype=i4)
d = np.array([0, 1, 15], dtype=u4)
check("int4_uint4_roundtrip",
      list(c.astype(np.int8)) == [-8, -1, 0, 7] and
      list(d.astype(np.uint8)) == [0, 1, 15],
      "%s / %s" % (c.astype(np.int8).tolist(), d.astype(np.uint8).tolist()))

# 5. finfo / iinfo reflection
check("finfo_iinfo",
      ml_dtypes.finfo(bf).dtype == np.dtype(bf) and
      ml_dtypes.iinfo(i4).min == -8 and ml_dtypes.iinfo(i4).max == 7,
      "finfo=%s iinfo=[%s,%s]" % (ml_dtypes.finfo(bf).dtype,
                                  ml_dtypes.iinfo(i4).min, ml_dtypes.iinfo(i4).max))

# 6. NumPy interop (cast + ufunc)
e = np.arange(4, dtype=np.float32).astype(bf)
promoted = (e.astype(np.float32) + 1.0)
check("numpy_interop",
      promoted.dtype == np.float32 and promoted.tolist() == [1.0, 2.0, 3.0, 4.0],
      str(promoted.tolist()))

# 7. HarmonyOS-only: signed OHOS aarch64 ELF extension module
ext_path = getattr(sys.modules["ml_dtypes._ml_dtypes_ext"], "__file__", "")
base = os.path.basename(ext_path)
raw = b""
if ext_path and os.path.isfile(ext_path):
    with open(ext_path, "rb") as fh:
        raw = fh.read()
ok_elf = raw[:4] == b"\x7fELF"
ok_tag = "aarch64-linux-ohos" in base
ok_signed = b".codesign" in raw
check("ohos_signed_aarch64_elf", ok_elf and ok_tag and ok_signed,
      "file=%s elf=%s ohos_tag=%s codesign=%s"
      % (base, ok_elf, ok_tag, ok_signed))

print("SUMMARY: %d/%d checkpoints passed" % (7 - len(failures), 7))
if failures:
    print("FAILED checkpoints: %s" % ", ".join(failures))
    sys.exit(1)
