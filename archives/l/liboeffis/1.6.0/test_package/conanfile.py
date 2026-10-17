#!/usr/bin/env python3
"""Conan test_package — liboeffis 1.6.0 消费者测试（L1 official test）。

CI 在 conan create 时自动执行。C 消费者程序真实链接 liboeffis.so 并调用
公共 API：上下文生命周期、ref/unref、fd 语义、失败连接错误路径，返回值与
errno 决定断言；断言失败 ⇒ 非零退出 ⇒ conan create 失败（真实门禁）。

OHOS 运行时注意：
- musl 解析 DT_NEEDED 时不跟随符号链接，因此把 liboeffis.so.1 与
  libsystemd.so.0 以「实体文件」形式摊平到运行时目录；
- 该目录通过 LD_LIBRARY_PATH 注入，与 conanrun 环境叠加生效。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


def _flatten(src, dst_dir, name):
    """把 src（可能是符号链接）以实体文件形式放到 dst_dir/name。"""
    real = os.path.realpath(src)
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, name)
    if os.path.lexists(dst):
        os.remove(dst)
    shutil.copy2(real, dst)
    os.chmod(dst, 0o755)
    return dst


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS 上 /tmp 只读（E002）：给消费者测试指定可写短路径目录
        tmpdir = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp"
        )
        os.makedirs(tmpdir, exist_ok=True)

        # 运行时库目录：摊平符号链接，供 musl 解析 DT_NEEDED
        rt_dir = os.path.join(tmpdir, "liboeffis-runtime-lib")
        if os.path.isdir(rt_dir):
            shutil.rmtree(rt_dir, ignore_errors=True)
        os.makedirs(rt_dir, exist_ok=True)

        seen = set()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs or []:
                if not libdir or libdir in seen or not os.path.isdir(libdir):
                    continue
                seen.add(libdir)
                for entry in sorted(os.listdir(libdir)):
                    path = os.path.join(libdir, entry)
                    if not os.path.isfile(path):
                        continue
                    if entry.startswith("liboeffis.so") or entry.startswith(
                        "libsystemd.so"
                    ):
                        _flatten(path, rt_dir, entry)

        # musl 按 SONAME 查找，补齐 liboeffis.so.1 / libsystemd.so.0
        for src_name, soname in (
            ("liboeffis.so.1.6.0", "liboeffis.so.1"),
            ("libsystemd.so.0.44.0", "libsystemd.so.0"),
        ):
            src = os.path.join(rt_dir, src_name)
            if os.path.isfile(src) and not os.path.lexists(
                os.path.join(rt_dir, soname)
            ):
                _flatten(src, rt_dir, soname)
        # 兜底：任何 libsystemd.so.0.* 实体文件都摊平成 libsystemd.so.0
        if not os.path.lexists(os.path.join(rt_dir, "libsystemd.so.0")):
            for entry in sorted(os.listdir(rt_dir)):
                if entry.startswith("libsystemd.so.0."):
                    _flatten(os.path.join(rt_dir, entry), rt_dir, "libsystemd.so.0")
                    break

        exe = os.path.join(self.cpp.build.bindirs[0], "test_liboeffis")
        env = Environment()
        env.define("LIBOEFFIS_TEST_DIR", tmpdir)
        env.define("TMPDIR", tmpdir)
        env.define_path("LD_LIBRARY_PATH", rt_dir)
        with env.vars(self, scope="run").apply():
            self.run(f'"{exe}"', env="conanrun")
