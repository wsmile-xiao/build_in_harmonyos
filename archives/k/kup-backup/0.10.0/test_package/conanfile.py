#!/usr/bin/env python3
"""Conan test_package for kup-backup 0.10.0 (application package).

上游 kup 0.10.0 无任何测试用例（无 tests/ 目录、CMakeLists 无 test 目标，
MANIFEST 如实申报 0）。本 test_package 为消费者视角运行时冒烟（kfourinline/
ksystemlog 26.04.0 模式）：

  1. 三个二进制存在于包 bin/（kup-daemon / kup-filedigger / kup-purger）
  2. kup-filedigger --version / kup-purger --version 打印 0.10.0 退出 0
  3. kup-daemon 无 kuprc 时走 "not enabled" 早退路径退出 0

运行时环境（ksystemlog 26.04.0 先例，KF6 6.14 发布包兼容层）：
  - 相对 DT_NEEDED（"../../bin/libKF6*.so"）：兼容软链农场（<build>/bin 与
    <build>/../../bin，musl loader 按 cwd 解析路径式 NEEDED）
  - 绝对 DT_NEEDED（发布机 $HOME/.cache/conan2/... 烤死路径）：缺失路径
    以符号链接补到依赖包真实库（musl loader 按 literal 解析）
  - /system/lib64 兼容 libc++_shared.so；qtbase 包内 offscreen 平台插件
  - OHOS 签名刷新（llvm-objcopy 去 .codesign + binary-sign-tool 重签）

断言主体在 test_kup.py（L0c 测试源文件，subprocess timeout=60 兜底）。
"""
import os
import shlex
import shutil
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment


class KupBackupTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # KF6 6.14 传递闭包显式声明（发布包配方不向消费图传播 runenv，
        # lib 目录收集需要 —— kfourinline/ksystemlog test_package 先例）。
        self.requires("qtbase/6.11.1")
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("kconfig/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("knotifications/6.14.0")
        self.requires("solid/6.14.0")
        self.requires("kidletime/6.14.0")
        self.requires("kjobwidgets/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")
        self.requires("kxmlgui/6.14.0")
        self.requires("kio/6.14.0")
        self.requires("kdbusaddons/6.14.0")
        self.requires("libgit2/1.9.0")
        self.requires("openssl/3.5.6", override=True)
        self.requires("zlib/1.3.1.1.1", override=True)
        self.requires("libxml2/2.15.3")

    def _libdirs(self):
        dirs = []
        seen = set()
        for dep in self.dependencies.values():
            if not (dep and dep.package_folder):
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if libdir not in seen and os.path.isdir(libdir):
                seen.add(libdir)
                dirs.append(libdir)
        return dirs

    def _prepare_runtime_links(self):
        """相对 DT_NEEDED 兼容软链农场（kfourinline/kgoldrunner 先例）。"""
        compat_libs = {}
        for libdir in self._libdirs():
            for name in os.listdir(libdir):
                if name.startswith("lib") and (
                    name.endswith(".so") or ".so." in name
                ):
                    full = os.path.join(libdir, name)
                    real = (
                        os.path.realpath(full)
                        if os.path.islink(full)
                        else full
                    )
                    compat_libs.setdefault(name, real)
        for base in (
            os.path.normpath(
                os.path.join(self.build_folder, os.pardir, os.pardir, "bin")
            ),
            os.path.join(self.build_folder, "bin"),
        ):
            os.makedirs(base, exist_ok=True)
            for name, src in compat_libs.items():
                dst = os.path.join(base, name)
                if not os.path.lexists(dst):
                    try:
                        os.symlink(src, dst)
                    except OSError:
                        shutil.copy2(src, dst)

    @staticmethod
    def _elf_needed(path):
        """极简 ELF64 小端 DT_NEEDED 提取（纯 python，无 readelf 依赖；
        .dynstr 经 SHT_DYNAMIC 的 sh_link 定位 —— ksystemlog 先例）。"""
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            return []
        if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
            return []

        def sh_field(idx, fmt, off):
            o = e_shoff + idx * e_shentsize + off
            return struct.unpack_from("<" + fmt, data, o)[0]

        e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
        e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
        e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
        dyn_off = dyn_size = dynstr = None
        for i in range(e_shnum):
            if sh_field(i, "H", 4) == 6:  # SHT_DYNAMIC
                dyn_off = sh_field(i, "Q", 0x18)
                dyn_size = sh_field(i, "Q", 0x20)
                dynstr = sh_field(sh_field(i, "I", 0x28), "Q", 0x18)
                break
        if dyn_off is None or dynstr is None:
            return []
        needed = []
        p, end = dyn_off, dyn_off + dyn_size
        while p + 16 <= end and p + 16 <= len(data):
            tag, val = struct.unpack_from("<QQ", data, p)
            if tag == 0:
                break
            if tag == 1:
                s = dynstr + val
                e = data.find(b"\x00", s)
                if e == -1:
                    break
                needed.append(data[s:e].decode("utf-8", "replace"))
            p += 16
        return needed

    def _fix_absolute_needed(self):
        """绝对 DT_NEEDED 兜底：KF6 发布包烤死的发布机绝对路径在当前
        worker 不存在 → 用指向依赖包真实库的符号链接补齐（musl loader
        按 literal 解析路径式 NEEDED，无 LD_LIBRARY_PATH 回退）。"""
        index = {}
        for libdir in self._libdirs():
            for name in os.listdir(libdir):
                full = os.path.join(libdir, name)
                if os.path.isfile(full) and (
                    name.endswith(".so") or ".so." in name
                ):
                    index.setdefault(name, full)
        pkg = self.dependencies.get("kup-backup")
        scan_roots = list(self._libdirs())
        if pkg and pkg.package_folder:
            pkg_bin = os.path.join(pkg.package_folder, "bin")
            if os.path.isdir(pkg_bin):
                scan_roots.append(pkg_bin)
        fixes = 0
        for root in scan_roots:
            for name in os.listdir(root):
                full = os.path.join(root, name)
                if not os.path.isfile(full):
                    continue
                if root.endswith("/bin") and not name.startswith("kup-"):
                    continue
                if root != scan_roots and not (
                    name.endswith(".so") or ".so." in name
                ):
                    continue
                for entry in self._elf_needed(full):
                    if not entry.startswith("/"):
                        continue
                    if os.path.exists(entry):
                        continue
                    source = index.get(os.path.basename(entry))
                    if not source:
                        continue
                    try:
                        os.makedirs(os.path.dirname(entry), exist_ok=True)
                        if not os.path.lexists(entry):
                            os.symlink(source, entry)
                            fixes += 1
                    except OSError as exc:
                        self.output.warning(
                            "cannot create NEEDED fallback %s: %s"
                            % (entry, exc))
        if fixes:
            self.output.info(
                "created %d absolute-NEEDED compatibility symlinks" % fixes)

    def _sign(self, path):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       check=True)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                        "-selfSign", "1"], check=True)

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        if self.settings.os not in ("Linux", "OHOS"):
            return
        pkg = self.dependencies["kup-backup"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        for name in ("kup-daemon", "kup-filedigger", "kup-purger"):
            if not os.path.isfile(os.path.join(bin_dir, name)):
                raise ConanException(
                    "kup-backup binary not found: %s" % name)

        if str(self.settings.os) == "OHOS":
            for name in ("kup-daemon", "kup-filedigger", "kup-purger"):
                self._sign(os.path.join(bin_dir, name))
            self._prepare_runtime_links()
            self._fix_absolute_needed()

        lib_dirs = self._libdirs()
        farm_dir = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, os.pardir, "bin"))
        ld_path = os.pathsep.join(["/system/lib64", farm_dir] + lib_dirs)

        plugin_dirs = []
        platforms = []
        for p in self.dependencies.values():
            if p.package_folder:
                for rel in ("plugins", os.path.join("lib", "plugins")):
                    d = os.path.join(p.package_folder, rel)
                    if os.path.isdir(d):
                        plugin_dirs.append(d)
                    pd = os.path.join(d, "platforms")
                    if os.path.isdir(pd):
                        platforms.append(pd)

        env = Environment()
        env.append("LD_LIBRARY_PATH", ld_path)
        env.define("QT_QPA_PLATFORM", "offscreen")
        for d in plugin_dirs:
            env.append("QT_PLUGIN_PATH", d)
        for d in platforms:
            env.append("QT_QPA_PLATFORM_PLUGIN_PATH", d)
        env.define("XDG_RUNTIME_DIR", self.build_folder)
        env.define("HOME", self.build_folder)

        # 持久化到 os.environ（self.run 可能 spawn 干净 shell，
        # khealthcertificate 先例，与 env.vars 双保险）。
        os.environ["LD_LIBRARY_PATH"] = (
            ld_path + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        ).rstrip(os.pathsep)
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        if platforms:
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.pathsep.join(
                platforms)
            os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(plugin_dirs)

        # 显式二进制路径经环境变量传入（self.run 签名无 env_vars 参数；
        # os.environ 持久化 + env.vars 双保险，khealthcertificate 先例）。
        os.environ["KUP_BIN_DIR"] = bin_dir
        script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "test_kup.py")
        with env.vars(self).apply():
            self.run(
                "python3 %s" % shlex.quote(script),
                env="conanrun",
                cwd=self.build_folder,
            )
        self.output.info("kup-backup runtime smoke passed")
