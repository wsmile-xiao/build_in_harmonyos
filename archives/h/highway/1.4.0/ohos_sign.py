"""Sign only package-owned ELF copies, preserving the executable mode."""
import os
import shutil
import subprocess
from pathlib import Path
from conan.errors import ConanException


def sign_elf(path):
    path = Path(path)
    signer = shutil.which("binary-sign-tool")
    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    if not signer or not readelf:
        raise ConanException("OHOS ELF signer and readelf are required")
    pending = path.with_name(path.name + ".libconfig-sign-input")
    signed = path.with_name(path.name + ".libconfig-signed")
    if pending.exists() or signed.exists():
        raise ConanException("stale signing sibling")
    try:
        shutil.copy2(path, pending)
        subprocess.run([signer, "sign", "-inFile", str(pending), "-outFile", str(signed), "-selfSign", "1"],
                       check=True, capture_output=True, timeout=40)
        sections = subprocess.run([readelf, "-S", str(signed)], check=True, capture_output=True, timeout=20)
        if b".codesign" not in sections.stdout:
            raise ConanException("signed ELF has no .codesign section")
        os.chmod(signed, path.stat().st_mode)
        os.replace(signed, path)
    finally:
        for p in (pending, signed):
            if p.exists(): p.unlink()
