#!/usr/bin/env python3
"""libvsgpt 0-20240504 消费者测试（Conan L1 / test_package）。

只使用已安装包（headers + 共享库 + bin/）：
- test_libvsgpt.c：通用消费者断言（版本、访问标志、codepage、签名检测正常/错误路径、
  volume 生命周期）
- test_ohos.c：鸿蒙专项（__OHOS__ 目标、TMPDIR 语义、在 TMPDIR 下合成合法 GPT 磁盘
  镜像并读回全链路），仅在 settings.os=OHOS 时编译运行
- vsgptinfo -V：安装后的 CLI 产物加载共享库并输出版本（运行/加载验证）
"""
import os

from conan import ConanFile


class LibvsgptTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _flags(self):
        cpp_info = self.dependencies["libvsgpt"].cpp_info
        include_flags = " ".join(f"-I{path}" for path in cpp_info.includedirs)
        library_flags = " ".join(f"-L{path}" for path in cpp_info.libdirs)
        link_flags = " ".join(f"-l{name}" for name in cpp_info.libs)
        return include_flags, library_flags, link_flags

    def build(self):
        include_flags, library_flags, link_flags = self._flags()
        compiler = os.environ.get("CC") or "clang"
        self.run(
            f"{compiler} test_libvsgpt.c -o test_libvsgpt "
            f"{include_flags} {library_flags} {link_flags}"
        )
        if str(self.settings.os) == "OHOS":
            self.run(
                f"{compiler} test_ohos.c -o test_ohos "
                f"{include_flags} {library_flags} {link_flags}"
            )

    def _runenv(self):
        """共享库运行期解析：包 libdir 前置到 LD_LIBRARY_PATH。"""
        cpp_info = self.dependencies["libvsgpt"].cpp_info
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
        cpp_info = self.dependencies["libvsgpt"].cpp_info
        library_dirs = self._runenv()
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH={library_dirs}:$LD_LIBRARY_PATH; "
            "./test_libvsgpt'",
            env="conanrun",
        )
        if str(self.settings.os) == "OHOS":
            self.run(
                f"{bash} -c 'export LD_LIBRARY_PATH={library_dirs}:$LD_LIBRARY_PATH; "
                f"export TMPDIR={self._tmpdir()}; ./test_ohos'",
                env="conanrun",
            )
        # 安装后的 CLI 产物必须能加载共享库并输出版本
        vsgptinfo = os.path.join(str(cpp_info.bindirs[0]), "vsgptinfo")
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH={library_dirs}:$LD_LIBRARY_PATH; "
            f'"{vsgptinfo}" -V | grep -q 20240504\'',
            env="conanrun",
        )
