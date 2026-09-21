#!/usr/bin/env python3
"""libsmraw 20240506 消费者测试（Conan L1 / test_package）。

只使用已安装包（headers + 共享库 + bin/）：
- test_libsmraw.c：通用消费者断言（版本串、codepage 正常/错误路径、单文件 RAW
  打开/读回、seek 后扇区读、offset 推进、handle 生命周期）
- test_ohos.c：鸿蒙专项（__OHOS__ 目标、TMPDIR 语义、在 TMPDIR 下合成 8 KiB
  RAW 镜像并读回全链路），仅在 settings.os=OHOS 时编译运行
- smrawverify -V：安装后的 CLI 产物加载共享库并输出版本（运行/加载验证）
"""
import os

from conan import ConanFile


class LibsmrawTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _flags(self):
        cpp_info = self.dependencies["libsmraw"].cpp_info
        include_flags = " ".join(f"-I{path}" for path in cpp_info.includedirs)
        library_flags = " ".join(f"-L{path}" for path in cpp_info.libdirs)
        link_flags = " ".join(f"-l{name}" for name in cpp_info.libs)
        return include_flags, library_flags, link_flags

    def build(self):
        include_flags, library_flags, link_flags = self._flags()
        compiler = os.environ.get("CC") or "clang"
        self.run(
            f"{compiler} test_libsmraw.c -o test_libsmraw "
            f"{include_flags} {library_flags} {link_flags}"
        )
        if str(self.settings.os) == "OHOS":
            self.run(
                f"{compiler} test_ohos.c -o test_ohos "
                f"{include_flags} {library_flags} {link_flags}"
            )

    def _runenv(self):
        """共享库运行期解析：包 libdir 前置到 LD_LIBRARY_PATH。"""
        cpp_info = self.dependencies["libsmraw"].cpp_info
        return ":".join(str(path) for path in cpp_info.libdirs)

    def _tmpdir(self):
        """OHOS：TMPDIR 必须存在且不是只读的 /tmp；缺省时用包内可写目录兜底。"""
        tmpdir = os.environ.get("TMPDIR") or ""
        if not tmpdir or tmpdir == "/tmp":
            tmpdir = os.path.join(self.build_folder, "ohos-tmp")
            os.makedirs(tmpdir, exist_ok=True)
        return tmpdir

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cpp_info = self.dependencies["libsmraw"].cpp_info
        library_dirs = self._runenv()
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH={library_dirs}:$LD_LIBRARY_PATH; "
            "./test_libsmraw'",
            env="conanrun",
        )
        if str(self.settings.os) == "OHOS":
            self.run(
                f"{bash} -c 'export LD_LIBRARY_PATH={library_dirs}:$LD_LIBRARY_PATH; "
                f"export TMPDIR={self._tmpdir()}; ./test_ohos'",
                env="conanrun",
            )
        # 安装后的 CLI 产物必须能加载共享库并输出版本
        smrawverify = os.path.join(str(cpp_info.bindirs[0]), "smrawverify")
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH={library_dirs}:$LD_LIBRARY_PATH; "
            f'"{smrawverify}" -V | grep -q 20240506\'',
            env="conanrun",
        )
