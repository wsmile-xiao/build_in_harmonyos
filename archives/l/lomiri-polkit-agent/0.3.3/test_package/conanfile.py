#!/usr/bin/env python3
"""Conan test_package for lomiri-polkit-agent 0.3.3 — R34 substantive consumer test.

被测包是 D-Bus 会话认证代理（application 类型，产物为
bin/lomiri-polkit-agent/policykit-agent + systemd user unit）。

L1 验证分两层（均实质依赖被测包产物）：
  1. 结构层（与主机架构无关，任何环境都执行）：
     * 包内服务可执行文件存在且为 aarch64 ELF（校验 e_ident/e_machine）；
     * systemd user unit 已安装且非空。
     该层保证 L1e 破坏性反向验证（移走包内产物）必然失败。
  2. 运行层（can_run 为真时执行）：通过 test.sh 实跑
     `policykit-agent --version` / `--help`，断言版本号 0.3.3。
     agent 本身由 D-Bus 激活、需要 session bus + polkitd，测试环境不具备，
     故 --version/--help 由 patches/0002 提供的 CLI 分支承担（同族 D-Bus
     服务配方同口径）。

运行库路径：VirtualRunEnv 的 conanrun 只聚合声明了 run env 的依赖，
generate() 显式遍历整张依赖图收集 lib 目录写入 conanrun_test 脚本，
供 self.run(env="conanrun_test") 使用。

E489 运行期重签名：OHOS 动态链接器拒绝加载 .codesign 失效/缺失的 ELF 共享库，
报 `Error loading shared library libnotify.so.4`（随后是该库缺席引起的
`notify_* symbol not found` 重定位错误）。制品仓 libnotify/0.8.3
（recipe rev 3d16c3c8）的 libnotify.so.4.0.0 即属此列，故 generate() 在测试前
把依赖图共享库复制到私有目录并统一 selfSign 重签，签名目录置于
LD_LIBRARY_PATH 首位（实现与证据见 _sign_dependency_closure）。
"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    _BINARY_NAME = "policykit-agent"
    _ELF_MACHINE_AARCH64 = 0xB7
    _ELF_MACHINE_X86_64 = 0x3E
    _SIGN_ALG = "SHA256withECDSA"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        """构造 conanrun_test 环境：签名目录 + 全部依赖 lib 目录 -> LD_LIBRARY_PATH。"""
        lib_dirs = self._collect_lib_dirs()
        signed_dir = self._sign_dependency_closure()
        # define_path 只接受字符串：列表必须先按 os.pathsep 拼接，否则写入脚本的
        # 是一段 Python 列表字面量，运行期 libnotify.so.4 等依赖库全部找不到。
        # 重签名副本所在目录放最前，同名库优先命中可加载版本。
        ld_dirs = ([signed_dir] if signed_dir else []) + lib_dirs
        env = Environment()
        env.define_path("LD_LIBRARY_PATH", os.pathsep.join(ld_dirs))
        env.vars(self).save_script("conanrun_test")

    def test(self):
        pkg = self.dependencies["lomiri-polkit-agent"].package_folder

        binary = self._find_binary(pkg)
        if not binary:
            self.output.error(f"未找到服务可执行文件 policykit-agent (pkg={pkg})")
            sys.exit(1)
        self.output.info(f"被测二进制: {binary}")

        self._assert_elf(binary)
        self._assert_service_unit(pkg)

        if not can_run(self):
            self.output.warning(
                "被测产物为 aarch64-linux-ohos，当前主机不可执行："
                "运行期冒烟跳过（ELF / systemd unit 结构校验已通过）")
            return

        # 真实执行被测包产物（R34/L0d）：test.sh 负责 --version/--help 与版本断言。
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.sh")
        rc = self.run(f'sh "{script}" "{binary}"', env="conanrun_test", ignore_errors=True)
        if rc != 0:
            self.output.error(f"smoke test 失败 (self.run 退出码 {rc})")
            sys.exit(1)

        self.output.info("smoke test 通过：policykit-agent 可执行且 --version 输出正确")

    # ── assertions ───────────────────────────────────────────

    def _assert_elf(self, binary):
        """断言产物是目标架构的 ELF 可执行文件（不依赖主机架构）。"""
        with open(binary, "rb") as handle:
            header = handle.read(20)
        if len(header) < 20 or header[:4] != b"\x7fELF":
            self.output.error(f"产物不是 ELF 文件: {binary}")
            sys.exit(1)
        if header[4] != 2:                     # EI_CLASS: 2 = 64-bit
            self.output.error("产物不是 64 位 ELF")
            sys.exit(1)
        machine = struct.unpack("<H", header[18:20])[0]
        if machine not in (self._ELF_MACHINE_AARCH64, self._ELF_MACHINE_X86_64):
            self.output.error(f"产物 ELF e_machine={machine:#x} 既非 aarch64 也非 x86_64")
            sys.exit(1)
        self.output.info(f"✅ ELF 校验通过 (e_machine={machine:#x})")

    def _assert_service_unit(self, pkg):
        """断言 D-Bus/systemd user unit 已随包安装且非空。"""
        candidates = [
            os.path.join(pkg, "lib", "systemd", "user", "lomiri-polkit-agent.service"),
            os.path.join(pkg, "share", "dbus-1", "services", "lomiri-polkit-agent.service"),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate) and os.path.getsize(candidate) > 0:
                self.output.info(f"✅ 服务单元已安装: {candidate}")
                return
        self.output.error(f"未找到非空的服务单元文件，已尝试: {candidates}")
        sys.exit(1)

    # ── E489：运行期 ELF 加载闭包重签名 ────────────────────────

    def _sign_dependency_closure(self):
        """把依赖图的共享库复制到私有目录并逐个重签名，返回该目录（失败返回 None）。

        OHOS 动态链接器要求共享库带可校验的 .codesign：制品仓 libnotify/0.8.3
        （recipe rev 3d16c3c8，2026-08-18 发布）的 libnotify.so.4.0.0 带有一段
        无法通过校验的签名，`dlopen` 直接报 Permission denied，测试运行期表现为
        `Error loading shared library libnotify.so.4` + `notify_* symbol not found`
        （证据与三态对照实验见 notes.md）。该缺陷属依赖包本身（其配方需修复后
        重新发布），但运行期加载闭包必须在执行测试前可加载 —— 故按 E489
        「sign-build-tree-runtime-closure」在测试前统一重签名。

        只写私有副本，绝不改动 conan 缓存（与 R49 的私有 prefix 口径一致）；
        依赖包自身的加载不依赖本包 cache 的改动。
        先例：archives/a/awf-gtk/4.2.0/conanfile.py（把 conan 依赖的 libnotify
        复制到 external 目录后签名）、archives/a/abbtr/1.0.4/conanfile.py
        （llvm-objcopy --remove-section .codesign + binary-sign-tool 写法）。
        """
        objcopy, signer = self._sign_tools()
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            self.output.warning(
                "llvm-objcopy / binary-sign-tool 不可用，跳过依赖库重签名"
                "（依赖库保持原样，加载失败时由测试如实报告）")
            return None

        target_dir = self._signed_libs_root()
        if not target_dir:
            return None

        libraries = self._iter_shared_libs()
        if not libraries:
            self.output.warning("依赖图中未发现 ELF 共享库，跳过重签名")
            return None

        signed, reused, failed = 0, 0, 0
        for src, aliases in sorted(libraries.items()):
            name = os.path.basename(src)
            dst = os.path.join(target_dir, name)
            # 重签名不改文件大小，故已存在同尺寸产物即可复用（幂等，重复运行零开销）
            if os.path.isfile(dst) and os.path.getsize(dst) >= os.path.getsize(src):
                reused += 1
            elif self._resign(src, dst, objcopy, signer):
                signed += 1
            else:
                failed += 1
                continue
            for alias in sorted(aliases):
                self._ensure_link(alias, name, target_dir)

        self.output.info(
            f"E489 运行期闭包重签名: 新签 {signed} / 复用 {reused} / 失败 {failed}"
            f" -> {target_dir}")
        return target_dir

    def _resign(self, src, dst, objcopy, signer):
        """复制 src 到 dst：先移除已有 .codesign 段，再 selfSign 重新签名。"""
        tmp = dst + ".signing"
        try:
            shutil.copy2(src, tmp)
            subprocess.run([objcopy, "--remove-section", ".codesign", tmp],
                           capture_output=True, timeout=60, check=False)
            result = subprocess.run(
                [signer, "sign", "-selfSign", "1", "-inFile", tmp,
                 "-outFile", tmp + ".signed", "-signAlg", self._SIGN_ALG],
                capture_output=True, timeout=180, check=False)
            if result.returncode != 0 or not os.path.isfile(tmp + ".signed"):
                raise RuntimeError(f"binary-sign-tool 退出码 {result.returncode}")
            os.replace(tmp + ".signed", dst)      # 原子替换，避免半写文件留在 LD 路径里
            os.chmod(dst, 0o755)
            return True
        except Exception as exc:                  # 单个库失败不阻断：同名库回退到依赖包原件
            self.output.warning(f"重签名失败 {os.path.basename(src)}: {exc}")
            return False
        finally:
            for stale in (tmp, tmp + ".signed"):
                if os.path.isfile(stale):
                    try:
                        os.unlink(stale)
                    except OSError:
                        pass

    @staticmethod
    def _signed_libs_root():
        """可写的签名目录（E002：本机 /tmp 只读，故按 TMPDIR → ~/tmp → gettempdir 探测）。"""
        for root in (os.environ.get("TMPDIR"), os.path.expanduser("~/tmp"),
                     tempfile.gettempdir()):
            if not root:
                continue
            target = os.path.join(root, "lomiri-polkit-agent-signed-libs")
            try:
                os.makedirs(target, exist_ok=True)
                probe = os.path.join(target, ".write-test")
                with open(probe, "w") as handle:
                    handle.write("ok")
                os.unlink(probe)
                return target
            except OSError:
                continue
        return None

    @staticmethod
    def _ensure_link(alias, target, target_dir):
        """在签名目录里补建同名软链（如 libnotify.so.4 -> libnotify.so.4.0.0）。"""
        link = os.path.join(target_dir, alias)
        if os.path.islink(link) or os.path.exists(link):
            return
        try:
            os.symlink(target, link)
        except OSError:
            pass

    @staticmethod
    def _sign_tools():
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        return objcopy, signer

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _iter_shared_libs(self):
        """依赖图 lib 目录下的 ELF 共享库 -> {真实文件: {别名...}}（别名含软链名）。"""
        libraries = {}
        for dependency in self.dependencies.values():
            folder = getattr(dependency, "package_folder", None)
            if not folder:
                continue
            for libdir in getattr(dependency.cpp_info, "libdirs", None) or ["lib"]:
                full = libdir if os.path.isabs(libdir) else os.path.join(folder, libdir)
                if not os.path.isdir(full):
                    continue
                for entry in sorted(os.listdir(full)):
                    path = os.path.join(full, entry)
                    if os.path.islink(path):
                        real = os.path.realpath(path)
                        if os.path.isfile(real) and self._is_elf(real):
                            libraries.setdefault(real, set()).add(entry)
                        continue
                    if os.path.isfile(path) and self._is_elf(path):
                        libraries.setdefault(os.path.realpath(path), set())
        return libraries

    # ── helpers ──────────────────────────────────────────────

    def _collect_lib_dirs(self):
        lib_dirs = []
        for dep in self.dependencies.values():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            for libdir in getattr(dep.cpp_info, "libdirs", None) or ["lib"]:
                path = os.path.join(folder, libdir)
                if os.path.isdir(path) and path not in lib_dirs:
                    lib_dirs.append(path)
        return lib_dirs

    def _find_binary(self, pkg):
        candidates = [
            # 实测安装位置：bin/lomiri-polkit-agent/（CMAKE_INSTALL_FULL_PKGLIBEXECDIR
            # 在本构建的 Conan 工具链下解析到包内 bin/）；其余项为兼容兜底
            os.path.join(pkg, "bin", "lomiri-polkit-agent", self._BINARY_NAME),
            os.path.join(pkg, "bin", self._BINARY_NAME),
            os.path.join(pkg, "libexec", "lomiri-polkit-agent", self._BINARY_NAME),
            os.path.join(pkg, "libexec", self._BINARY_NAME),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        for root, _dirs, files in os.walk(pkg):     # 递归兜底
            if self._BINARY_NAME in files:
                return os.path.join(root, self._BINARY_NAME)
        return None
