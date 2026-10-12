#!/usr/bin/env python3
"""Conan test_package — qlog 0.51.1（consumer-side smoke validation）。

R34：实际执行打包出的应用。QLog 上游自带 19 个 QTest 套件（tests/，
见 notes.md 上游测试申报），但均为交叉编译 aarch64 产物，需在设备端
执行；consumer 侧的可自动化验证为启动冒烟：

  * `qlog --version` — QApplication 构造（加载 offscreen QPA 插件，
    验证整个 Qt6 运行链接闭包），QCommandLineParser 打印版本后退出 0；
  * `qlog --help`   — 同样的启动路径，并校验上游命令行选项齐全；
  * 可执行文件内嵌版本字符串 0.51.1（QLog.pro VERSION → DEFINES）；
  * .codesign 段存在（OHOS 加载器要求）。

运行期环境（E537 家族先例：isoimagewriter/alligator）：运行环境显式
重建，不依赖继承的 conanrun LD_LIBRARY_PATH（其中含 OHOS 加载器无法
解析的空白路径项）。
"""
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.env import Environment


class QlogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ── helpers ──────────────────────────────────────────────────────────

    def _lib_dirs(self):
        lib_dirs = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                for layout_dir in ("lib", "bin"):
                    lib_dir = os.path.join(dep.package_folder, layout_dir)
                    if os.path.isdir(lib_dir):
                        lib_dirs.append(lib_dir)
        return lib_dirs

    def _find_readelf(self):
        for cand in ("readelf", "/data/service/hnp/bin/readelf",
                     "/usr/bin/readelf", "/bin/readelf"):
            try:
                found = shutil.which(cand)
                if found and subprocess.run(
                    [found, "--version"], capture_output=True, timeout=20
                ).returncode == 0:
                    return found
            except (OSError, subprocess.SubprocessError):
                continue
        return None

    def _needed_entries(self, readelf, path):
        try:
            out = subprocess.run([readelf, "-d", path], capture_output=True,
                                 text=True, timeout=60).stdout
        except (OSError, subprocess.SubprocessError):
            return []
        return re.findall(r"Shared library: \[([^\]]+)\]", out)

    def _find_lib(self, basename, lib_dirs):
        for lib_dir in lib_dirs:
            cand = os.path.join(lib_dir, basename)
            if os.path.exists(cand):
                return cand
        return None

    def _link_or_copy(self, src, dst):
        """OHOS 沙箱 uid 映射导致 symlink 创建可能 EACCES → 回退复制。"""
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.lexists(dst):
            return
        try:
            os.symlink(src, dst)
        except OSError:
            shutil.copy2(src, dst)

    def _repair_dt_needed(self, readelf, lib_dirs, run_cwd):
        repaired = []
        for lib_dir in lib_dirs:
            for name in sorted(os.listdir(lib_dir)):
                if not name.endswith(".so"):
                    continue
                for entry in self._needed_entries(readelf, os.path.join(lib_dir, name)):
                    if entry.startswith("/"):
                        dest = entry
                    elif "/" in entry:
                        dest = os.path.normpath(os.path.join(run_cwd, entry))
                    else:
                        continue
                    if os.path.exists(dest):
                        continue
                    src = self._find_lib(os.path.basename(entry), lib_dirs)
                    if not src:
                        continue
                    try:
                        self._link_or_copy(src, dest)
                        repaired.append(f"{os.path.basename(entry)} -> {dest}")
                    except OSError as exc:
                        self.output.warning(f"cannot materialize {dest}: {exc}")
        return repaired

    # ── test ─────────────────────────────────────────────────────────────

    def test(self):
        dep = self.dependencies.get("qlog")
        if dep is None or not dep.package_folder:
            raise AssertionError("qlog not found in the dependency graph")
        app_bin = os.path.join(dep.package_folder, "bin", "qlog")
        if not os.path.exists(app_bin):
            raise AssertionError(f"missing packaged application: {app_bin}")

        # OHOS ELF 必须带 .codesign 段（不签名的 ELF 加载器拒载）
        if str(self.settings.os) == "OHOS":
            readelf = self._find_readelf()
            if readelf:
                sections = subprocess.run(
                    [readelf, "-S", app_bin], capture_output=True, text=True,
                    timeout=60).stdout
                if ".codesign" not in sections:
                    raise AssertionError(
                        "packaged qlog ELF has no .codesign section"
                    )

        with open(app_bin, "rb") as handle:
            binary = handle.read()
        pkg_version = str(dep.ref.version)
        if pkg_version.encode() not in binary:
            raise AssertionError(
                f"packaged binary does not embed the version string {pkg_version}"
            )

        scratch = tempfile.mkdtemp(prefix="qlog-test-")
        run_cwd = os.path.join(scratch, "a", "b")
        os.makedirs(run_cwd, exist_ok=True)

        lib_dirs = self._lib_dirs()
        readelf = self._find_readelf()
        if readelf:
            repaired = self._repair_dt_needed(readelf, lib_dirs, run_cwd)
            self.output.info(f"DT_NEEDED entries materialized: {len(repaired)}")
            for item in repaired:
                self.output.info(f"  {item}")
        else:
            self.output.warning("readelf not found; DT_NEEDED repair skipped")

        ld_paths = list(lib_dirs)
        ld_paths.extend(["/system/lib64", "/system/lib64/platformsdk",
                         "/system/lib64/ndk"])
        plugin_paths = []
        for dep_it in self.dependencies.values():
            if dep_it and dep_it.package_folder:
                for plugins_dir in ("plugins", os.path.join("lib", "plugins")):
                    plugins_path = os.path.join(dep_it.package_folder, plugins_dir)
                    if os.path.isdir(plugins_path):
                        plugin_paths.append(plugins_path)

        env = Environment()
        env.define("LD_LIBRARY_PATH", ":".join(ld_paths))
        env.define("QT_PLUGIN_PATH", ":".join(plugin_paths))
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("TZ", "Asia/Shanghai")
        home = os.path.join(run_cwd, "test-home")
        xdg_runtime = os.path.join(run_cwd, "xdg-runtime")
        os.makedirs(home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(home, ".local", "share"))

        # 冒烟断言抽离到 test_qlog.py（L0c 测试源），由本 test() 实际执行
        # （R34）：脚本内以子进程方式运行 bin/qlog --version / --help，
        # 校验版本号与上游命令行选项；运行环境在 self.run 外层应用。
        test_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "test_qlog.py"
        )
        if not os.path.isfile(test_script):
            raise AssertionError(f"missing test source: {test_script}")
        with env.vars(self).apply():
            self.run(
                f'python3 "{test_script}" "{app_bin}" "{pkg_version}"',
                cwd=run_cwd,
            )
