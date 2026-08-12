#!/usr/bin/env python3
"""Conan recipe for imgp — Python CLI image resizer/rotator.

imgp is a pure Python CLI tool that uses Pillow for image processing.
It is installed via pip from the PyPI source tarball.
System Python (pre-installed via cmd-pkgs) is used at build and run time.
"""
import os, sys

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class ImgpConan(ConanFile):
    name = "imgp"
    version = "2.9"
    description = "High-performance CLI batch image resizer & rotator"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/jarun/imgp"
    url = "https://github.com/jarun/imgp"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Use system Python (pre-installed via cmd-pkgs)
        python = "python3"

        # Change to the source directory since pip needs to find setup.py
        src_dir = self.source_folder

        # Install pillow (pre-built wheel for OHOS) separately.
        # Use --prefix to install to $HOME/usr/local instead of the
        # default user site-packages (~/.local/). The OHOS filesystem
        # at ~/.local/ is mounted with noexec, preventing .so loading.
        # $HOME/usr/local/ is on an executable filesystem.
        # Use --force-reinstall because pip may skip if pillow is
        # already cached in the noexec user site-packages.
        prefix = os.path.expanduser("~/usr/local")
        self.run(f"{python} -m pip install --force-reinstall --prefix='{prefix}' pillow", env="conanrun")
        # HMDFS 上 pip 安装的 `.so` 文件缺少执行位(660 → 755)，
        # 导致运行时 dlopen 报 Permission denied。显式修复执行权限。
        # 动态检测 Python 版本号，与 package() 方法保持一致。
        # 注意：HMDFS 上 chmod 755 对部分 .so（如 PIL/_imaging.cpython-*.so）会被拒
        # (xattr 限制),改用 install -m 755 强制重写文件赋权,幂等且绕过 chmod 限制。
        # CI 的 find -exec 对双 {} 占位符支持不稳(报 install: bad '{}'),
        # 改用 Python os.walk 逐文件赋权,CI 兼容且行为一致。
        # 注意: GNU install 拒绝 src==dst 同文件(报 '...' is '...'),
        # 且匹配需精确到 .so 后缀(排除 .pyc/.cpython-*.pyc)。
        # 方案: 先 copy2 到临时文件,再 install -m 755 从临时文件写回原路径。
        import shutil
        _py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        _so_dir = os.path.join(prefix, "lib", _py_ver, "site-packages")
        _so_count = 0
        for _root, _dirs, _files in os.walk(_so_dir):
            for _fn in _files:
                if _fn.endswith(".so"):  # PIL: _imaging.cpython-312-aarch64-linux-ohos.so
                    _fpath = os.path.join(_root, _fn)
                    _tmp = _fpath + ".permfix"
                    shutil.copy2(_fpath, _tmp)
                    self.run(f"install -m 755 {_tmp} {_fpath}", env="conanrun")
                    os.remove(_tmp)
                    _so_count += 1
        self.output.info(f"  [ok] install -m 755 applied to {_so_count} .so files")

        # Install setuptools from the community pip index (pypi.cnb.cool).
        # The CI's internal pip index HAS setuptools (verified: pip download
        # succeeds, wheel py3-none-any). Previously this recipe hand-downloaded
        # the setuptools tarball from files.pythonhosted.org via urllib, which
        # timed out on the CI network (TimeoutError at ~9%). pip from the
        # community index is reachable (pillow installs fine), so use pip.
        self.run(f"{python} -m pip install setuptools==75.8.0", env="conanrun")

        # Install imgp from source directory using --no-build-isolation
        # (setuptools is now available in the system Python).
        # Use --no-deps to prevent pip from re-installing pillow to the
        # noexec user site-packages (~/.local/). Pillow is already
        # installed to $HOME/usr/local/ via --prefix --force-reinstall.
        # Copy imgp → imgp.py first so setup.py can find it in the
        # temporary build sandbox created by pip.
        self.run(f"{python} -c \"import shutil; shutil.copy('{src_dir}/imgp', '{src_dir}/imgp.py')\"", env="conanrun")
        self.run(f"{python} -m pip install \"{src_dir}\" --no-build-isolation --no-deps", env="conanrun")

    def package(self):
        # Find the installed files from the system Python
        python = "python3"
        python_bin = os.path.join(os.sep, "usr", "local", "bin")

        # Try to find the Python bin directory
        import subprocess
        try:
            result = subprocess.run([python, "-c", "import sys; print(sys.executable)"],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                python_bin = os.path.dirname(result.stdout.strip())
        except Exception:
            pass

        # Copy imgp executable.
        # 注意: pip 把 imgp 可执行脚本装到 *user* bin (~/.local/bin, 因为系统
        # site-packages 不可写, CI 日志 "The script imgp is installed in
        # '.../.local/bin'"), 而 sys.executable 目录 (CI 沙箱 /data/app/bin)
        # 并没有 imgp —— 只从 python_bin 复制会得到空的 bin/, 导致静态验证
        # 断言 bin/imgp 失败。遍历所有候选 bin 目录, 取第一个有 imgp 的。
        _bin_candidates = [
            python_bin,
            os.path.expanduser("~/.local/bin"),
            os.path.expanduser("~/usr/local/bin"),
            "/usr/local/bin",
        ]
        _dest_bin = os.path.join(self.package_folder, "bin")
        _imgp_copied = False
        for _bdir in _bin_candidates:
            if not _bdir or not os.path.isdir(_bdir):
                continue
            if not os.path.isfile(os.path.join(_bdir, "imgp")):
                continue
            copy(self, "imgp*", _bdir, _dest_bin)
            _imgp_copied = True
            self.output.info(f"  [ok] imgp executable copied from {_bdir} to bin/")
            break
        if not _imgp_copied:
            self.output.warning("  [warn] imgp executable not found in any bin dir!")
        # 确保 bin/imgp 可执行(HMDFS/沙箱下 copy 可能丢执行位, 与 .so 同因)
        _bin_imgp = os.path.join(_dest_bin, "imgp")
        if os.path.isfile(_bin_imgp):
            try:
                os.chmod(_bin_imgp, 0o755)
            except OSError:
                pass

        # Dynamically detect Python version for site-packages paths
        import subprocess
        try:
            result = subprocess.run([python, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                                    capture_output=True, text=True, timeout=10)
            py_ver = f"python{result.stdout.strip()}" if result.returncode == 0 and result.stdout.strip() else "python3.12"
        except Exception:
            py_ver = "python3.12"
            self.output.warning(f"Failed to detect Python version, falling back to {py_ver}")
        for site_dir in [
            f"/usr/local/lib/{py_ver}/site-packages",
            f"/usr/lib/{py_ver}/site-packages",
            os.path.expanduser(f"~/.local/lib/{py_ver}/site-packages"),
            os.path.expanduser(f"~/usr/local/lib/{py_ver}/site-packages"),
        ]:
            if os.path.isdir(site_dir):
                dest = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
                # Copy imgp module
                copy(self, "imgp.py*", site_dir, dest)
                copy(self, "imgp-*.egg-info*", site_dir, dest)
                # Copy PIL (pillow) - runtime dependency
                pil_dir = os.path.join(site_dir, "PIL")
                if os.path.isdir(pil_dir):
                    copy(self, "*", pil_dir, os.path.join(dest, "PIL"))
                # Copy PIL dist-info
                for f in os.listdir(site_dir):
                    if f.startswith("PIL") and f.endswith("dist-info"):
                        copy(self, f, site_dir, dest)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []