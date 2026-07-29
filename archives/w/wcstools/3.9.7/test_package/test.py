#!/usr/bin/env python3
"""Conan test_package smoke test — wcstools 3.9.7."""
import os, sys, subprocess, glob

def run_binary(bindir, name):
    path = os.path.join(bindir, name)
    if not os.path.isfile(path):
        return (None, None)
    try:
        r = subprocess.run([path], capture_output=True, text=True, timeout=30)
        return (r.returncode, r.stdout + r.stderr)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        print(f"[ERROR] run_binary({name}): {e}", file=sys.stderr)
        return (None, None)

def main():
    # Accept bindir from argv[1] (passed by test_package/conanfile.py)
    bindir = sys.argv[1] if len(sys.argv) > 1 else ""
    if not bindir or not os.path.isdir(bindir):
        bins = sorted(glob.glob("/storage/Users/currentUser/.conan2/p/b/wcsto*/p/bin"))
        if bins: bindir = bins[-1]
    if not bindir or not os.path.isdir(bindir):
        print("[FAIL] No binary dir"); sys.exit(1)

    smoke_ok = 0
    for name, expect in [("imhead","IMHEAD"),("gethead","GETHEAD")]:
        rc, out = run_binary(bindir, name)
        if rc is not None and expect in (out or "").upper():
            print(f"[RUNTIME PASS] {name}: exit_code={rc}"); smoke_ok += 1
        else:
            print(f"[RUNTIME FAIL] {name}: rc={rc}")
    print(f"Runtime smoke: {smoke_ok}/2")

    target51 = sorted(["addpix","bincat","char2sp","conpix","cphead","crlf","delhead","delwcs","edhead","filename","fileroot","filext","fixpix","getcol","getdate","getfits","gethead","getpix","gettab","htmlsp","i2f","imcat","imextract","imfill","imhead","immatch","imresize","imrot","imsize","imsmooth","imstack","imstar","imwcs","isfile","isfits","isnum","isrange","keyhead","newfits","remap","scat","sethead","setpix","simpos","sky2xy","skycoor","sp2char","subpix","sumpix","wcshead","xy2sky"])
    art_ok = sum(1 for n in target51 if os.path.isfile(os.path.join(bindir,n)) and os.access(os.path.join(bindir,n),os.X_OK) and os.path.getsize(os.path.join(bindir,n))>100)
    if os.path.isfile(os.path.join(bindir,"wcstools")): art_ok += 1
    print(f"Artifact check: {art_ok}/52")
    print(f"=== SUMMARY: Runtime {smoke_ok}/2, Artifact {art_ok}/52 ===")
    sys.exit(0 if smoke_ok == 2 and art_ok == 52 else 1)

if __name__ == "__main__": main()
