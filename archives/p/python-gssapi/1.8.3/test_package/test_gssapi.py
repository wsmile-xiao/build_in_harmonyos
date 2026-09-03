import os
import sys

pkg_dir = os.environ.get("GSSAPI_PKG_DIR", "")
if not pkg_dir or not os.path.isdir(pkg_dir):
    print("FAIL: GSSAPI_PKG_DIR not set or not a directory")
    sys.exit(1)

gssapi_dir = os.path.join(pkg_dir, "gssapi")
if not os.path.isdir(gssapi_dir):
    print("FAIL: gssapi package directory not found")
    sys.exit(1)

so_files = []
py_files = []
for root, dirs, files in os.walk(gssapi_dir):
    for f in files:
        full = os.path.join(root, f)
        if f.endswith(".so"):
            so_files.append(f)
        elif f.endswith(".py"):
            py_files.append(f)

if not so_files:
    print("FAIL: No compiled .so extension modules found")
    sys.exit(1)

if not py_files:
    print("FAIL: No Python source files found")
    sys.exit(1)

print(f"PASS: Found {len(so_files)} compiled extension modules and {len(py_files)} Python files")
for f in so_files[:5]:
    print(f"  {f}")
if len(so_files) > 5:
    print(f"  ... and {len(so_files) - 5} more")
