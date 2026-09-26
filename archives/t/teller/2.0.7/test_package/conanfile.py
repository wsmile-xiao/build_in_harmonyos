#!/usr/bin/env python3
"""Conan consumer test for teller 2.0.7 (Rust binary package).

三层验证：
  1. 包完整性 —— 打包的 `teller` 可执行文件存在且可执行；
  2. 消费者冒烟 + 鸿蒙特有断言 —— test_teller.py 运行真实二进制
     （AArch64 / OHOS musl loader / code signature / --version /
     export json / scan 端到端），断言产物在本平台可用所必需的特性；
  3. 依赖功能测试 —— test_deps.c 以消费者身份用 OHOS clang 编译并链接
     openssl/3.5.8.1（teller 经 rustify→native-tls→openssl-sys 使用），
     在设备上实际执行 OpenSSL 代码路径（SHA256/EVP/RAND/BN/AES 往返）。
"""

import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TellerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_teller.py", "test_deps.c"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明，使消费者侧能解析其 package_folder：teller 静态链接 OpenSSL
        # （产物 DT_NEEDED 仅 libc.so），仅运行 teller 无法证明该依赖真实可用。
        self.requires("openssl/3.5.8.1")

    def layout(self):
        basic_layout(self)

    def _ohos_cc(self):
        candidates = []
        try:
            conf = self.conf.get("tools.build:compiler_executables")
            if isinstance(conf, dict):
                candidates.append(conf.get("c"))
        except Exception:  # noqa: BLE001 - conf may be absent on some runners
            pass
        candidates += [
            os.environ.get("CC"),
            shutil.which("aarch64-unknown-linux-ohos-clang"),
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/"
            "llvm/bin/aarch64-unknown-linux-ohos-clang",
            shutil.which("clang"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _compile_dependency_test(self):
        cc = self._ohos_cc()
        dep = None
        try:
            dep = self.dependencies["openssl"]
        except Exception:  # noqa: BLE001 - dependency missing from graph
            dep = None
        if cc is None or dep is None:
            self.output.warning("dependency test skipped: cc=%s openssl=%s"
                                % (cc, bool(dep)))
            return None
        source = os.path.join(self.source_folder, "test_deps.c")
        binary = os.path.join(self.build_folder, "test_deps")
        include = os.path.join(dep.package_folder, "include")
        libdir = os.path.join(dep.package_folder, "lib")
        cmd = " ".join(['"%s"' % cc, '"%s"' % source, "-o", '"%s"' % binary,
                        '-I"%s"' % include, '-L"%s"' % libdir,
                        "-lssl", "-lcrypto"])
        self.output.info(f"compiling dependency test: {cmd}")
        if self.run(cmd, env="conanbuild", ignore_errors=True) != 0:
            raise AssertionError("dependency test failed to compile")
        if not os.path.isfile(binary):
            raise AssertionError(f"dependency test binary missing: {binary}")
        os.chmod(binary, 0o755)
        return binary

    def test(self):
        package_folder = self.dependencies["teller"].package_folder
        exe = os.path.join(package_folder, "bin", "teller")
        if not os.path.isfile(exe):
            raise AssertionError(f"Missing teller executable: {exe}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_teller.py")
        result = self.run(
            f'PACKAGE_FOLDER="{package_folder}" "{sys.executable}" "{script}"',
            env="conanrun",
            ignore_errors=True,
        )
        if result != 0:
            raise AssertionError(
                f"teller test_package failed with exit code {result}")

        dep_test = self._compile_dependency_test()
        if dep_test is None:
            self.output.warning("SKIP: dependency functional test not executed")
            return
        result = self.run(f'"{dep_test}"', env="conanrun", ignore_errors=True)
        if result != 0:
            raise AssertionError(
                f"dependency functional test failed with exit code {result}")
