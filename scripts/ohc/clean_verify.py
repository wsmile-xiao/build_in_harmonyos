"""G0: Clean build verification — verify patches are self-contained."""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail

def clean_verify(software: str, version: str, pdir: str | None = None) -> int:
    """
    G0 clean build verification.
    
    Steps:
    1. Locate original tarball, patches, manifest
    2. Extract tarball to temp dir
    3. Apply patches
    4. Run configure (using manifest configure_options)
    5. Run make
    6. Run make install DESTDIR=...
    7. Check product integrity
    8. Cleanup
    
    Returns: 0=PASS, 1=FAIL
    """
    project = Path(pdir) if pdir else Path(find_project_dir())
    letter = software[0].lower()
    ver_dir = project / "archives" / letter / software / version
    
    # Locate resources
    patch_dir = ver_dir / "patches"
    manifest = ver_dir / "manifest.yaml"
    
    # Find original tarball — check .build-context for BUILD_SRC_ORIG_DIR and tarball path
    tarball = None
    ctx_files = list(project.glob(f".build-context-{software}-{version}*"))
    ctx_vars = {}
    if ctx_files:
        for line in ctx_files[0].read_text(encoding="utf-8", errors="replace").split("\n"):
            m = re.match(r'^(?:export\s+)?(\w+)=(.*)', line.strip())
            if m:
                val = m.group(2).strip().strip('"').strip("'")
                if val:
                    ctx_vars[m.group(1)] = val
    
    # Find tarball from BUILD_TARBALL or search common locations
    if "BUILD_TARBALL" in ctx_vars:
        p = Path(ctx_vars["BUILD_TARBALL"])
        if p.exists():
            tarball = p
    
    if not tarball:
        # Search for tarball
        for pattern in [f"{software}-{version}.tar.*", f"{software}*{version}*.tar.*"]:
            matches = list(Path(ctx_vars.get("BUILD_SRC_DIR", "")).parent.glob(pattern))
            if matches:
                tarball = matches[0]
                break
    
    if not tarball or not tarball.exists():
        log_fail(f"G0: 找不到原始 tarball")
        return 1
    
    # Read configure_options from manifest
    configure_cmd = "/bin/sh ./configure"
    configure_options = ""
    if manifest.exists():
        content = manifest.read_text(encoding="utf-8")
        m = re.search(r'configure_options:\s*["\']?(.*?)["\']?\n', content)
        if m:
            configure_options = m.group(1).strip()
    
    # Get DEFAULT_PREFIX from context
    default_prefix = ctx_vars.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local"))
    
    # Step 1: Extract tarball to temp dir
    tmpdir = Path(tempfile.mkdtemp(prefix=f"ohc-verify-{software}-"))
    log_info(f"G0: 解压 {tarball.name} 到 {tmpdir}")
    
    try:
        r = subprocess.run(
            ["tar", "xf", str(tarball)],
            cwd=str(tmpdir), capture_output=True, timeout=120
        )
        if r.returncode != 0:
            log_fail(f"G0: tar xf 失败: {r.stderr.decode()[:200]}")
            shutil.rmtree(tmpdir, ignore_errors=True)
            return 1
        
        # Find extracted directory (usually tarball-name without extension)
        extracted = list(tmpdir.iterdir())
        if len(extracted) == 1 and extracted[0].is_dir():
            src_dir = extracted[0]
        else:
            # Try common naming
            src_dir = None
            for candidate in [f"{software}-{version}", f"{software.lower()}-{version}"]:
                if (tmpdir / candidate).is_dir():
                    src_dir = tmpdir / candidate
                    break
            if not src_dir:
                log_fail(f"G0: 无法确定解压目录")
                shutil.rmtree(tmpdir, ignore_errors=True)
                return 1
        
        # Step 2: Apply patches
        patches = sorted(patch_dir.glob("*.patch"))
        if patches:
            log_info(f"G0: 应用 {len(patches)} 个补丁...")
            for pf in patches:
                r = subprocess.run(
                    ["patch", "-p1", "-i", str(pf)],
                    cwd=str(src_dir), capture_output=True, timeout=30
                )
                if r.returncode != 0:
                    log_fail(f"G0: 补丁 {pf.name} 应用失败")
                    log_fail(f"    {r.stderr.decode()[:200]}")
                    _emit_handoff("patch", pf.name, src_dir, tmpdir)
                    return 1
            log_ok(f"G0: {len(patches)} 个补丁全部应用成功")
        else:
            log_info("G0: 无补丁")
        
        # Ensure configure script is executable (patch doesn't preserve mode)
        configure_script = src_dir / "configure"
        if configure_script.exists():
            configure_script.chmod(0o755)
            log_info("G0: 设置 configure 可执行权限")
        
        # Step 3: Configure
        log_info("G0: 运行 configure...")
        full_cmd = f"{configure_cmd} --prefix={default_prefix} {configure_options}"
        log_file = tmpdir / "g0-configure.log"
        g0_env = os.environ.copy()
        g0_env["TMPDIR"] = str(tmpdir)
        default_prefix = ctx_vars.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local"))
        g0_env["PKG_CONFIG_PATH"] = f"{default_prefix}/lib/pkgconfig:{default_prefix}/share/pkgconfig:{g0_env.get('PKG_CONFIG_PATH', '')}"
        g0_env["LD_LIBRARY_PATH"] = f"{default_prefix}/lib:{g0_env.get('LD_LIBRARY_PATH', '')}"
        g0_env["PCRE2_CFLAGS"] = f"-I{default_prefix}/include"
        g0_env["PCRE2_LIBS"] = f"-L{default_prefix}/lib -lpcre2-8"
        # Ensure CC/CXX are set for Makefile projects
        if "CC" not in g0_env:
            g0_env["CC"] = "clang"
        if "CXX" not in g0_env:
            g0_env["CXX"] = "clang++"
        with open(log_file, "w") as lf:
            r = subprocess.run(
                full_cmd, shell=True,
                cwd=str(src_dir), stdout=lf, stderr=subprocess.STDOUT,
                env=g0_env,
                timeout=600  # 10 minutes for configure
            )
        if r.returncode != 0:
            log_fail(f"G0: configure 失败 (exit {r.returncode})")
            _emit_handoff("configure", str(log_file), src_dir, tmpdir)
            
            return 1
        log_ok("G0: configure 成功")
        
        # Step 4: Make
        log_info("G0: 运行 make...")
        log_file = tmpdir / "g0-make.log"
        # Run make with proper output capture
        r = subprocess.run(
            ["make", "-j1"],
            cwd=str(src_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=g0_env,
            timeout=1800,  # 30 minutes for make
            check=False
        )
        # Write output to log file
        with open(log_file, "w") as lf:
            lf.write(r.stdout.decode("utf-8", errors="replace"))
        # Print to console for debugging
        if r.stdout:
            print(r.stdout.decode("utf-8", errors="replace"), flush=True)
        if r.returncode != 0:
            log_fail(f"G0: make 失败 (exit {r.returncode})")
            _emit_handoff("make", str(log_file), src_dir, tmpdir)
            return 1
        log_ok("G0: make 成功")
        
        # Step 5: Make install
        log_info("G0: 运行 make install...")
        destdir = tmpdir / "g0-install"
        destdir.mkdir()
        log_file = tmpdir / "g0-install.log"
        with open(log_file, "w") as lf:
            r = subprocess.run(
                ["make", "install", f"DESTDIR={destdir}"],
                cwd=str(src_dir), stdout=lf, stderr=subprocess.STDOUT,
                env=g0_env,
                timeout=300
            )
        if r.returncode != 0:
            log_fail(f"G0: make install 失败 (exit {r.returncode})")
            _emit_handoff("make_install", str(log_file), src_dir, tmpdir)
            return 1
        
        # Step 6: Check product integrity
        bins = list(destdir.rglob("bin/*"))
        libs = list(destdir.rglob("lib/*"))
        if not bins and not libs:
            log_fail("G0: 安装产物为空！")
            _emit_handoff("make_install", "empty staging", src_dir, tmpdir)
            return 1
        
        log_ok(f"G0: 安装产物正常 ({len(bins)} bin, {len(libs)} lib)")
        
        # PASS
        # Create G0 marker
        (ver_dir / ".g0-verified").write_text(
            f"verified_at: {__import__('datetime').datetime.now().isoformat()}\n"
            f"tarball: {tarball}\n"
            f"patches: {len(patches)}\n",
            encoding="utf-8"
        )
        log_ok("✅ G0 干净构建验证通过")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return 0
        
    except Exception as e:
        log_fail(f"G0: 异常: {e}")
        print(f"[DEBUG] 保留临时目录: {tmpdir}")
        import traceback
        traceback.print_exc()
        return 1


def _emit_handoff(failed_step: str, error_ref: str, src_dir: Path, tmpdir: Path):
    """Emit G0 HANDOFF block for AI."""
    print(f"""
╔═══ G0 HANDOFF ══════════════════════════════════╗
║ G0_CHECK: clean-build-verify                    ║
║ RESULT: FAIL                                     ║
║ FAILED_STEP: {failed_step:<37}║
║ ERROR_REF: {error_ref:<37}║
║ SRC_DIR: {str(src_dir):<37}║
║ TMPDIR: {str(tmpdir):<37} (保留用于调试)          ║
║ AI NEXT ACTIONS:                                 ║
║   1. 读取错误日志，诊断根因                        ║
║   2. 修复补丁或 hints                            ║
║   3. 重新运行 ohc-run.py clean-verify            ║
╚══════════════════════════════════════════════════╝
""", flush=True)


def clean_verify_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="ohc clean-verify")
    parser.add_argument("software")
    parser.add_argument("version")
    parser.add_argument("--project-dir")
    args = parser.parse_args(argv)
    return clean_verify(args.software, args.version, getattr(args, "project_dir", None))
