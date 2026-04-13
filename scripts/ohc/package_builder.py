"""Package builder — 10-step packaging pipeline.
"""
from __future__ import annotations
import os
import re
import shutil
import subprocess
from pathlib import Path

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail
from .sign_elf import sign_single, is_elf


class PackageBuilder:
    def __init__(self, software: str, version: str,
                 static: bool = False, debug: bool = True,
                 prefix: str = "", pdir: str | None = None):
        self.software = software
        self.version = version
        self.static = static
        self.debug = debug
        self.pdir = Path(pdir) if pdir else Path(find_project_dir())
        letter = software[0].lower()
        self.archive_dir = self.pdir / "archives" / letter / software / version
        self.packaging_dir = self.archive_dir / "packaging"
        self.pkgdir = self.packaging_dir / f"pkg-{software}-{version}"
        self.debug_dir = self.packaging_dir / "debug-symbols"
        self.src_prefix = Path(prefix) if prefix else self._resolve_prefix()

    def _resolve_prefix(self) -> Path:
        tmpdir = os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))
        p = Path(tmpdir) / f"test-install-{self.software}-{self.version}"
        if p.exists():
            return p
        return Path(os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local")))

    def _run(self, cmd: list[str] | str, **kw) -> tuple[int, str]:
        if isinstance(cmd, str):
            cmd = ["zsh", "-c", cmd]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kw)
            return r.returncode, (r.stdout or "") + (r.stderr or "")
        except Exception as e:
            return 1, str(e)

    def step1_create_pkgdir(self):
        log_info("Step 1/10: 创建打包目录...")
        if self.pkgdir.exists():
            shutil.rmtree(self.pkgdir)
        for d in ["bin", "lib", "lib/external", "include", "share", "doc"]:
            (self.pkgdir / d).mkdir(parents=True, exist_ok=True)

    def step2_copy(self):
        log_info("Step 2/10: 复制文件...")
        for subdir in ["bin", "lib", "include", "share"]:
            src = self.src_prefix / subdir
            dst = self.pkgdir / subdir
            if src.exists():
                for item in src.iterdir():
                    if item.is_dir():
                        shutil.copytree(str(item), str(dst / item.name), dirs_exist_ok=True)
                    else:
                        shutil.copy2(str(item), str(dst / item.name))

        # Apply exclude list
        for excl_file in [self.archive_dir / "EXCLUDE_LIST",
                          self.archive_dir.parent / "EXCLUDE_LIST"]:
            if excl_file.exists():
                for line in excl_file.read_text(encoding="utf-8", errors="replace").split("\n"):
                    name = line.strip()
                    if not name or name.startswith("#"):
                        continue
                    for d in ["bin", "lib"]:
                        target = self.pkgdir / d / name
                        if target.exists():
                            target.unlink()

    def step3_symlinks(self):
        log_info("Step 3/10: 替换符号链接...")
        replaced = 0
        for item in list(self.pkgdir.rglob("*")):
            if item.is_symlink():
                target = item.resolve()
                item.unlink()
                if item.parent.name == "bin" and target.exists():
                    # Create wrapper script
                    wrapper = f"#!/bin/sh\nSELF_DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"\nexec \"$SELF_DIR/{target.name}\" \"$@\"\n"
                    item.write_text(wrapper, encoding="utf-8")
                    os.chmod(item, 0o755)
                else:
                    try:
                        shutil.copy2(str(target), str(item))
                    except Exception:
                        pass
                replaced += 1
        log_ok(f"  替换 {replaced} 个符号链接")

    def step4_collect_deps(self):
        log_info("Step 4/10: 收集外部依赖...")
        skip_libs = {"libc.so", "libm.so", "libdl.so", "libpthread.so",
                     "librt.so", "libutil.so", "ld-musl", "ld-linux"}
        search_paths = [
            self.src_prefix / "lib",
            Path(os.path.expanduser("~/usr/local/lib")),
            Path("/data/service/hnp/lib"),
            Path("/usr/lib"), Path("/usr/lib64"),
        ]
        ext_dir = self.pkgdir / "lib" / "external"
        collected = set()

        def collect(elf_file: Path, depth: int = 0):
            if depth > 2:
                return
            rc, out = self._run(["llvm-readelf", "-d", str(elf_file)])
            if rc != 0:
                rc, out = self._run(["/data/service/hnp/bin/llvm-readelf", "-d", str(elf_file)])
            for m in re.finditer(r'\(NEEDED\)\s+Shared library:\s+\[(.+?)\]', out):
                lib = m.group(1)
                if any(s in lib for s in skip_libs):
                    continue
                if lib in collected:
                    continue
                if (self.pkgdir / "lib" / lib).exists():
                    continue
                # Find in search paths
                for sp in search_paths:
                    candidate = sp / lib
                    if candidate.exists() and is_elf(candidate):
                        shutil.copy2(str(candidate), str(ext_dir / lib))
                        collected.add(lib)
                        collect(ext_dir / lib, depth + 1)
                        break

        for f in self.pkgdir.rglob("*"):
            if f.is_file() and is_elf(f):
                collect(f)

        log_ok(f"  收集 {len(collected)} 个外部依赖")

    def step5_rpath(self):
        log_info("Step 5/10: 设置 RPATH...")
        patchelf = shutil.which("patchelf") or shutil.which("chrpath")
        if not patchelf:
            log_warn("  patchelf/chrpath 不可用，跳过"); return

        for f in self.pkgdir.rglob("*"):
            if not f.is_file() or not is_elf(f):
                continue
            rel = f.relative_to(self.pkgdir)
            if rel.parts[0] == "bin":
                rpath = "$ORIGIN/../lib:$ORIGIN/../lib/external"
            elif rel.parts[0] == "lib" and "external" in rel.parts:
                rpath = "$ORIGIN"
            elif rel.parts[0] == "lib":
                rpath = "$ORIGIN:$ORIGIN/external"
            else:
                continue
            subprocess.run([patchelf, "--set-rpath", rpath, str(f)],
                          capture_output=True, timeout=5)

    def step6_strip(self):
        log_info("Step 6/10: Strip 调试符号...")
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        for f in self.pkgdir.rglob("*"):
            if not f.is_file() or not is_elf(f) or f.suffix == ".a":
                continue
            if self.debug:
                self.debug_dir.mkdir(parents=True, exist_ok=True)
                debug_file = self.debug_dir / (f.name + ".debug")
                subprocess.run([objcopy, "--only-keep-debug", str(f), str(debug_file)],
                              capture_output=True, timeout=10)
                tmp = f.with_suffix(f.suffix + ".tmp")
                subprocess.run([objcopy, "--strip-debug", str(f), str(tmp)],
                              capture_output=True, timeout=10)
                if tmp.exists():
                    shutil.move(str(tmp), str(f))
                subprocess.run([objcopy, f"--add-gnu-debuglink={debug_file}", str(f)],
                              capture_output=True, timeout=10)
            else:
                tmp = f.with_suffix(f.suffix + ".tmp")
                subprocess.run([objcopy, "--strip-debug", str(f), str(tmp)],
                              capture_output=True, timeout=10)
                if tmp.exists():
                    shutil.move(str(tmp), str(f))

    def step7_sign(self):
        log_info("Step 7/10: ELF 签名...")
        for f in self.pkgdir.rglob("*"):
            if f.is_file() and is_elf(f):
                rc = sign_single(f)
                if rc != 0:
                    f.with_suffix(f.suffix + ".unsigned").touch()

    def step8_permissions(self):
        log_info("Step 8/10: 修复执行权限...")
        fixed = 0
        for f in self.pkgdir.rglob("*"):
            if f.is_file() and (is_elf(f) or (f.parent.name == "bin" and not os.access(f, os.X_OK))):
                os.chmod(f, 0o755)
                fixed += 1
        log_ok(f"  修复 {fixed} 个文件权限")

    def step9_install_sh(self):
        log_info("Step 9/10: 生成 install.sh...")
        install_sh = self.packaging_dir / f"install-{self.software}-{self.version}.sh"
        install_sh.write_text(
            f"#!/bin/sh\n"
            f"# Install script for {self.software} {self.version}\n"
            f"set -e\n"
            f"PREFIX=${{1:-$HOME/usr/local}}\n"
            f"SCRIPT_DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"\n"
            f"cd \"$SCRIPT_DIR\"\n"
            f"for d in bin lib include share; do\n"
            f"  [ -d \"$d\" ] && cp -a \"$d/\" \"$PREFIX/$d/\"\n"
            f"done\n"
            f"chmod +x \"$PREFIX/bin/\"* 2>/dev/null || true\n"
            f"echo '{self.software} {self.version} installed to $PREFIX'\n",
            encoding="utf-8")
        os.chmod(install_sh, 0o755)

    def step10_tarball(self):
        log_info("Step 10/10: 打包 tar.gz...")
        tar_name = f"{self.software}-{self.version}-ohos-aarch64"

        # Main tarball
        tar_gz = self.packaging_dir / f"{tar_name}.tar.gz"
        subprocess.run(
            ["tar", "czf", str(tar_gz), "bin", "lib", "include", "share", "doc"],
            cwd=str(self.pkgdir), capture_output=True,
        )
        if tar_gz.exists():
            size = tar_gz.stat().st_size
            log_ok(f"  {tar_gz.name}: {size // 1024}KB")
        else:
            # Fallback: fewer dirs
            subprocess.run(
                ["tar", "czf", str(tar_gz), "bin", "lib", "share"],
                cwd=str(self.pkgdir), capture_output=True,
            )

        # Debug tarball
        if self.debug and self.debug_dir.exists() and any(self.debug_dir.iterdir()):
            debug_tar = self.packaging_dir / f"{tar_name}-debug.tar.gz"
            subprocess.run(
                ["tar", "czf", str(debug_tar), "."],
                cwd=str(self.debug_dir), capture_output=True,
            )

    def run(self) -> int:
        if not self.archive_dir.exists():
            log_fail(f"归档目录不存在: {self.archive_dir}")
            return 1
        self.step1_create_pkgdir()
        self.step2_copy()
        self.step3_symlinks()
        self.step4_collect_deps()
        self.step5_rpath()
        self.step6_strip()
        self.step7_sign()
        self.step8_permissions()
        self.step9_install_sh()
        self.step10_tarball()
        # Write completion marker (finish.py uses this to verify)
        marker = self.packaging_dir / ".packaged"
        marker.write_text(
            f"software={self.software}\nversion={self.version}\n"
            f"timestamp={__import__('datetime').datetime.now().isoformat()}\n",
            encoding="utf-8",
        )
        log_ok(f"✅ 打包完成: {self.software} {self.version}")
        return 0


def package_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="ohc package")
    parser.add_argument("software")
    parser.add_argument("version")
    parser.add_argument("--static", action="store_true")
    parser.add_argument("--debug", action="store_true", default=True)
    parser.add_argument("--prefix")
    parser.add_argument("--project-dir")
    args = parser.parse_args(argv)
    builder = PackageBuilder(
        args.software, args.version,
        static=args.static, debug=args.debug,
        prefix=args.prefix or "",
        pdir=getattr(args, "project_dir", None),
    )
    return builder.run()
