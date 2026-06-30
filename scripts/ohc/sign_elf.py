"""ELF binary signing for HarmonyOS.
"""
from __future__ import annotations
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .utils import log_info, log_ok, log_warn, log_fail

HNP_BIN = "/data/service/hnp/bin"
TOOLS = {
    "llvm_objcopy": f"{HNP_BIN}/llvm-objcopy",
    "binary_sign_tool": f"{HNP_BIN}/binary-sign-tool",
    "llvm_readelf": f"{HNP_BIN}/llvm-readelf",
}


def is_elf(filepath: Path) -> bool:
    try:
        return filepath.read_bytes()[:4] == b'\x7fELF'
    except Exception:
        return False


def sign_single(elf_file: Path, rpath: str | None = None) -> int:
    """Sign a single ELF file. Returns 0=ok, 3=fail."""
    if not elf_file.exists() or not is_elf(elf_file):
        return 3

    # Step 0: Set RPATH (optional)
    if rpath:
        patchelf = shutil.which("patchelf")
        if patchelf:
            subprocess.run([patchelf, "--set-rpath", rpath, str(elf_file)],
                          capture_output=True, timeout=10)

    # Step 1: Remove old signature
    objcopy = TOOLS["llvm_objcopy"]
    if not Path(objcopy).exists():
        objcopy = shutil.which("llvm-objcopy") or objcopy
    subprocess.run([objcopy, "--remove-section", ".codesign", str(elf_file)],
                   capture_output=True, timeout=10)

    # Step 2: Sign
    sign_tool = TOOLS["binary_sign_tool"]
    if not Path(sign_tool).exists():
        log_fail(f"binary-sign-tool not found: {sign_tool}")
        return 3

    tmp = elf_file.with_suffix(elf_file.suffix + ".signed.tmp")
    for attempt in range(3):
        r = subprocess.run(
            [sign_tool, "sign", "-inFile", str(elf_file),
             "-outFile", str(tmp), "-selfSign", "1"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0 and tmp.exists():
            shutil.move(str(tmp), str(elf_file))
            break
        if attempt < 2:
            import time; time.sleep(1)
    else:
        tmp.unlink(missing_ok=True)
        log_warn(f"  签名失败: {elf_file.name}")
        return 3

    # Step 3: Fix permissions
    os.chmod(elf_file, 0o755)
    return 0


def batch_sign(directory: Path, max_workers: int | None = None) -> int:
    """Batch sign all ELF files in directory."""
    elfs = [f for f in directory.rglob("*") if f.is_file() and is_elf(f)]
    if not elfs:
        log_info("  无 ELF 文件需要签名")
        return 0

    if not max_workers:
        cpu = os.cpu_count() or 1
        max_workers = min(cpu, len(elfs), 8)

    log_info(f"  批量签名: {len(elfs)} 个 ELF (workers={max_workers})")
    success = failed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(sign_single, f): f for f in elfs}
        for fut in as_completed(futures):
            if fut.result() == 0:
                success += 1
            else:
                failed += 1

    log_ok(f"  签名完成: {success} 成功, {failed} 失败")
    return 3 if failed > 0 else 0


def sign_elf_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="ohc sign-elf")
    parser.add_argument("elf_file", nargs="?")
    parser.add_argument("rpath", nargs="?")
    parser.add_argument("--batch", type=Path)
    args = parser.parse_args(argv)

    if args.batch:
        return batch_sign(args.batch)
    elif args.elf_file:
        return sign_single(Path(args.elf_file), args.rpath)
    else:
        parser.print_help()
        return 1
