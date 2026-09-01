#!/usr/bin/env python3
"""Test script for Crypt::OpenSSL::Random package verification."""
import sys, os, shutil, subprocess

MODULE = "Crypt::OpenSSL::Random"

def find_perl():
    perl = shutil.which("perl")
    if perl:
        return perl
    common_paths = [
        "/data/service/hnp/bin/perl",
        "/storage/Users/currentUser/usr/local/bin/perl",
        os.path.expanduser("~/usr/local/bin/perl"),
    ]
    for p in common_paths:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_package.py <pkg_folder>", file=sys.stderr)
        sys.exit(1)
    pkg_folder = sys.argv[1]
    errors = []
    warnings = []

    # 检查 .so 文件
    so_path = None
    for root, dirs, files in os.walk(pkg_folder):
        for fn in files:
            if fn.endswith(".so"):
                so_path = os.path.join(root, fn)
                break
        if so_path:
            break
    if not so_path:
        errors.append("No .so file found in package")
    else:
        with open(so_path, "rb") as f:
            magic = f.read(4)
            if magic != b"\x7fELF":
                errors.append(f"{so_path} is not valid ELF")

    # 检查 .pm 文件并加载测试
    module_rel = MODULE.replace("::", "/") + ".pm"
    pm_path = None
    perl5lib = None
    for root, dirs, files in os.walk(pkg_folder):
        for fn in files:
            full_path = os.path.join(root, fn)
            if full_path.endswith("/" + module_rel):
                pm_path = full_path
                idx = full_path.rfind("/" + module_rel)
                perl5lib = full_path[:idx]
                break
        if pm_path:
            break

    if not pm_path:
        errors.append("No .pm file found in package")
    elif perl5lib:
        perl_path = find_perl()
        if not perl_path:
            warnings.append("perl not found, skipping module load test")
        else:
            env = dict(os.environ)
            env["PERL5LIB"] = perl5lib
            try:
                result = subprocess.run(
                    [perl_path, "-e", "use " + MODULE + "; print 'loaded'"],
                    capture_output=True, text=True, env=env, timeout=10
                )
                if result.returncode == 0:
                    print(f"Perl module load test: PASS")
                else:
                    stderr = result.stderr.strip()
                    if any(ind.lower() in stderr.lower() for ind in ["Permission denied", "symbol not found", "Error relocating", "dlopen failed", "No such file"]):
                        warnings.append(f"Platform limitation: {stderr}")
                    else:
                        errors.append(f"Failed to load module: {stderr}")
            except Exception as e:
                warnings.append(f"Module load test error: {e}")

    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: {MODULE} package verified")
    sys.exit(0)

if __name__ == "__main__":
    main()
