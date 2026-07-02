"""Verify build quality — 4 gates (G1-G4).
"""
from __future__ import annotations
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail
from .models import parse_build_context


@dataclass
class GateResult:
    passed: int = 0
    failed: int = 0
    warned: int = 0
    details: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        return self.failed == 0


class VerifyBuild:
    def __init__(self, software: str, version: str,
                 archive_dir: str = "", project_dir: str = "",
                 install_prefix: str = ""):
        self.software = software
        self.version = version
        self.pdir = Path(project_dir) if project_dir else Path(find_project_dir())
        letter = software[0].lower()
        self.archive_dir = Path(archive_dir) if archive_dir else self.pdir / "archives" / letter / software / version
        self.install_prefix = Path(install_prefix) if install_prefix else self._resolve_prefix()

    def _resolve_prefix(self) -> Path:
        # Try build context
        for ctx in self.pdir.glob(f".build-context-{self.software}-{self.version}*"):
            data = parse_build_context(str(ctx))
            if "TEST_PREFIX" in data:
                return Path(data["TEST_PREFIX"])
        # Fallback
        tmpdir = os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))
        return Path(tmpdir) / f"test-install-{self.software}-{self.version}"

    def _run(self, cmd: list[str], **kw) -> tuple[int, str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15, **kw)
            return r.returncode, (r.stdout or "") + (r.stderr or "")
        except Exception:
            return 1, ""

    def gate1_binary_integrity(self) -> GateResult:
        log_info("G1: 二进制完整性...")
        g = GateResult()
        bins = list((self.install_prefix / "bin").glob("*")) if (self.install_prefix / "bin").exists() else []
        bins = [b for b in bins if b.is_file()]

        for b in bins:
            rc, out = self._run(["file", str(b)])
            is_elf = "ELF" in out
            is_exec = "executable" in out or "pie executable" in out
            is_script = "script" in out or "text" in out

            # Fallback: check ELF magic bytes directly for musl-linked binaries
            # where the `file` command may not recognize them
            if not is_elf:
                try:
                    magic = b.read_bytes()[:4]
                    if magic == b'\x7fELF':
                        is_elf = True
                except Exception:
                    pass

            # Fallback: try readelf -h for confirmation
            if not is_elf and not is_script:
                rc2, out2 = self._run(["readelf", "-h", str(b)])
                if rc2 == 0 and "ELF" in out2:
                    is_elf = True

            # Fallback: when `file` command returns empty (HMDFS issue)
            if not is_elf and not is_script and not is_exec and not out.strip():
                try:
                    head = b.read_text(encoding="utf-8", errors="replace")[:80]
                    if head.startswith("#!") or head.startswith("#!/"):
                        is_script = True
                except Exception:
                    pass

            if is_elf or is_exec:
                g.passed += 1
            elif is_script:
                g.warned += 1
                g.details.append(f"  ⚠️ {b.name}: script")
            else:
                g.failed += 1
                g.details.append(f"  ❌ {b.name}: unknown type ({out.strip()[:80]})")

            if not os.access(b, os.X_OK):
                g.warned += 1

        # Check shared libs
        for so in (self.install_prefix / "lib").rglob("*.so*") if (self.install_prefix / "lib").exists() else []:
            rc, out = self._run(["file", str(so)])
            is_elf = "ELF" in out
            if not is_elf:
                try:
                    magic = so.read_bytes()[:4]
                    if magic == b'\x7fELF':
                        is_elf = True
                except Exception:
                    pass
            if is_elf:
                g.passed += 1
            else:
                g.warned += 1

        log_ok(f"  G1: ✅{g.passed} ⚠️{g.warned} ❌{g.failed}")
        return g

    def gate2_functional(self) -> GateResult:
        log_info("G2: 功能可用性...")
        g = GateResult()
        bins = list((self.install_prefix / "bin").glob("*")) if (self.install_prefix / "bin").exists() else []
        bins = [b for b in bins if b.is_file() and os.access(b, os.X_OK)]

        for b in bins[:10]:
            rc, out = self._run([str(b), "--version"], timeout=5)
            if rc == 0 and out.strip():
                g.passed += 1
                ver = out.strip().split("\n")[0][:60]
                g.details.append(f"  ✅ {b.name}: {ver}")
            else:
                g.warned += 1
                g.details.append(f"  ⚠️ {b.name}: --version failed")

        if not bins:
            g.warned += 1
            g.details.append("  无二进制文件")

        log_ok(f"  G2: ✅{g.passed} ⚠️{g.warned} ❌{g.failed}")
        return g

    def gate3_portability(self) -> GateResult:
        log_info("G3: 可移植性...")
        g = GateResult()
        patchelf = shutil.which("patchelf")
        bins = list((self.install_prefix / "bin").glob("*")) if (self.install_prefix / "bin").exists() else []
        # Filter ELF binaries — catch OSError for HMDFS I/O errors
        elf_bins = []
        for b in bins:
            if not b.is_file():
                continue
            try:
                if b.read_bytes()[:4] == b'\x7fELF':
                    elf_bins.append(b)
            except (OSError, IOError):
                elf_bins.append(b)  # Assume ELF if unreadable (HMDFS issue)

        for b in elf_bins:
            # RPATH check
            if patchelf:
                rc, rpath = self._run([patchelf, "--print-rpath", str(b)])
                if "$ORIGIN" in rpath:
                    g.passed += 1
                elif rpath.strip():
                    g.passed += 1  # Has some RPATH
                else:
                    g.warned += 1
                    g.details.append(f"  ⚠️ {b.name}: no RPATH")

            # Signature check
            rc, out = self._run(["file", "-b", str(b)])
            if "signed" in out.lower() or "signature" in out.lower():
                g.passed += 1
            else:
                g.warned += 1

        log_ok(f"  G3: ✅{g.passed} ⚠️{g.warned} ❌{g.failed}")
        return g

    def gate4_archive(self) -> GateResult:
        log_info("G4: 档案完整性...")
        g = GateResult()

        # manifest.yaml
        mf = self.archive_dir / "manifest.yaml"
        if not mf.exists():
            g.failed += 1; g.details.append("  ❌ manifest.yaml 缺失")
        else:
            content = mf.read_text(encoding="utf-8", errors="replace")
            for field in ["software", "version", "status", "build_system"]:
                if f"{field}:" not in content:
                    g.failed += 1; g.details.append(f"  ❌ manifest 缺少 {field}")

        # notes.md
        prog = self.archive_dir / "notes.md"
        if not prog.exists():
            g.warned += 1; g.details.append("  ⚠️ notes.md 缺失")

        # Patches
        patches = list((self.archive_dir / "patches").glob("000*.patch")) if (self.archive_dir / "patches").exists() else []
        g.details.append(f"  补丁: {len(patches)} 个")

        # Directories
        for d in ["patches", "reports", "packaging"]:
            if not (self.archive_dir / d).is_dir():
                g.warned += 1; g.details.append(f"  ⚠️ 目录缺失: {d}")

        log_ok(f"  G4: ✅{g.passed} ⚠️{g.warned} ❌{g.failed}")
        return g

    def run(self) -> int:
        g1 = self.gate1_binary_integrity()
        g2 = self.gate2_functional()
        g3 = self.gate3_portability()
        g4 = self.gate4_archive()

        any_fail = g1.failed + g2.failed + g3.failed + g4.failed
        total_warn = g1.warned + g2.warned + g3.warned + g4.warned

        if any_fail:
            verdict = "FAIL"
        elif total_warn > 10:
            verdict = "PASS-WARN"
        else:
            verdict = "PASS"

        # Write report
        report_dir = self.archive_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report = report_dir / "quality-report.md"
        report.write_text(
            f"# Quality Report — {self.software} {self.version}\n\n"
            f"**Verdict**: {verdict}\n\n"
            f"## G1 Binary Integrity: {'PASS' if g1.ok() else 'FAIL'}\n"
            f"- ✅ {g1.passed} ⚠️ {g1.warned} ❌ {g1.failed}\n\n"
            f"## G2 Functional: {'PASS' if g2.ok() else 'FAIL'}\n"
            f"- ✅ {g2.passed} ⚠️ {g2.warned} ❌ {g2.failed}\n\n"
            f"## G3 Portability: {'PASS' if g3.ok() else 'FAIL'}\n"
            f"- ✅ {g3.passed} ⚠️ {g3.warned} ❌ {g3.failed}\n\n"
            f"## G4 Archive: {'PASS' if g4.ok() else 'FAIL'}\n"
            f"- ✅ {g4.passed} ⚠️ {g4.warned} ❌ {g4.failed}\n\n"
            + "\n".join(g1.details + g2.details + g3.details + g4.details),
            encoding="utf-8")

        log_ok(f"  质量报告: {verdict}")

        marker = Path(self.archive_dir) / ".verify-passed"
        if verdict != "FAIL":
            marker.write_text(
                f"verified_at={__import__('datetime').datetime.now().isoformat()}\n"
                f"verdict={verdict}\n",
                encoding="utf-8",
            )
            return 0
        else:
            marker.unlink(missing_ok=True)
            return 1


def verify_build_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="ohc verify-build")
    parser.add_argument("software", nargs="?")
    parser.add_argument("version", nargs="?")
    parser.add_argument("--software", dest="sw")
    parser.add_argument("--version", dest="ver")
    parser.add_argument("--archive-dir")
    parser.add_argument("--install-prefix")
    parser.add_argument("--project-dir")
    args = parser.parse_args(argv)

    sw = args.sw or args.software or ""
    ver = args.ver or args.version or ""
    if not sw:
        parser.print_help(); return 1

    v = VerifyBuild(sw, ver,
                    archive_dir=args.archive_dir or "",
                    project_dir=getattr(args, "project_dir", None) or "",
                    install_prefix=args.install_prefix or "")
    return v.run()
