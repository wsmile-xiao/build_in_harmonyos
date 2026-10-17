# conan-test-package — liboil 0.3.17 (HarmonyOS PC / AArch64)
#
# 真实链接安装后的 liboil，调用真实 API 做确定性计算并核对结果；
# 另含 HarmonyOS 专项 ELF 检查。无 stub、无 skip、无超时代替执行。
# （test_package 清单见同目录 MANIFEST.yml）
#
# 注意: 本机为 aarch64 HarmonyOS PC，产物为原生可执行（build 机器即
# 目标机器）；不使用 can_run()——它在 build profile(x86_64 default) 与
# host profile(OHOS armv8) 组合下恒为 False，会静默跳过全部测试。

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LiboilTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    # conan create 运行 test_package 时注入（显式 test_type 下由
    # 命令行语义提供）；直接 conan build 时用默认引用名。
    def requirements(self):
        ref = getattr(self, "tested_reference", None) or "liboil/0.3.17"
        self.requires(ref)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _liboil_libdir(self):
        for pkg, dep in self.dependencies.items():
            if pkg.ref.name == "liboil":
                return dep.cpp_info.libdirs[0]
        raise AssertionError("liboil dependency libdir not found")

    def test(self):
        exe = os.path.join(self.build_folder, "oil_consumer")
        libdir = self._liboil_libdir()
        shared = os.path.exists(os.path.join(libdir, "liboil-0.3.so.0"))

        # --- 1) 真实 API 确定性计算（consumer 内 6 项断言，任何一项
        #     失败 oil_consumer 返回非 0，self.run 即抛错）---
        # env="conanrun" 加载 VirtualRunEnv 生成的运行环境
        # （LD_LIBRARY_PATH 指向包内 lib，真实动态加载 liboil-0.3.so.0）。
        self.run('"%s"' % exe, env="conanrun")

        # --- 2) HarmonyOS 专项 ELF 检查（每条均为真实 readelf/ar 管道，
        #     grep 断言失败 → 非零退出 → self.run 抛错）---
        if shared:
            so = os.path.join(libdir, "liboil-0.3.so.0.0.0")
            if not os.path.exists(so):
                so = os.path.join(libdir, "liboil-0.3.so.0")
            # ELF64
            self.run('readelf -h "%s" | grep -q "Class:.*ELF64"' % so,
                     env="conanrun")
            self.output.info("OHOS check: shared object is ELF64")
            # AArch64
            self.run('readelf -h "%s" | grep -q "Machine:.*AArch64"' % so,
                     env="conanrun")
            self.output.info("OHOS check: shared object targets AArch64")
            # consumer 真实动态依赖 liboil SONAME
            self.run('readelf -d "%s" | grep -q "NEEDED.*liboil-0.3.so.0"'
                     % exe, env="conanrun")
            self.output.info("OHOS check: consumer NEEDED contains "
                             "liboil-0.3.so.0 (real dynamic linkage)")
            # NEEDED 全量打印（人工核查无 x86-only 依赖）
            self.run('readelf -d "%s" | grep NEEDED' % exe, env="conanrun")
            # 无宿主路径 RPATH/RUNPATH（grep 找到即失败）
            self.run('if readelf -d "%s" | grep -qE "RPATH|RUNPATH"; '
                     'then readelf -d "%s" | grep -E "RPATH|RUNPATH"; '
                     'exit 1; fi' % (exe, exe), env="conanrun")
            self.output.info("OHOS check: no RPATH/RUNPATH in consumer")
            # SONAME 打印（上游 liboil-0.3.so.0）
            self.run('readelf -d "%s" | grep SONAME' % so, env="conanrun")
        else:
            # 上游静态库名带版本后缀: liboil-0.3.a
            archive = os.path.join(libdir, "liboil-0.3.a")
            if not os.path.exists(archive):
                raise AssertionError("static liboil-0.3.a not found in %s"
                                     % libdir)
            # 静态库成员为 AArch64 ELF64（ar t 列成员——上游归档成员
            # 可能带子目录路径，ar x 解包到临时目录后真实 readelf）
            import tempfile
            with tempfile.TemporaryDirectory(dir=self.build_folder) as td:
                self.run('cd "%s" && ar x "%s"' % (td, archive), env="conanrun")
                self.run('find "%s" -name "*.o" | head -1 | '
                         'xargs readelf -h | grep -q "Class:.*ELF64" && '
                         'find "%s" -name "*.o" | head -1 | '
                         'xargs readelf -h | grep -q "Machine:.*AArch64"'
                         % (td, td), env="conanrun")
            self.output.info("OHOS check: liboil-0.3.a members are "
                             "ELF64 AArch64 objects")
            # consumer 静态链入: NEEDED 不得出现 liboil
            self.run('if readelf -d "%s" | grep -q "NEEDED.*liboil"; '
                     'then exit 1; fi' % exe, env="conanrun")
            self.output.info("OHOS check: consumer statically linked "
                             "(no liboil NEEDED)")
            # consumer 仍为 ELF64 AArch64 可执行
            self.run('readelf -h "%s" | grep -q "Class:.*ELF64" && '
                     'readelf -h "%s" | grep -q "Machine:.*AArch64"'
                     % (exe, exe), env="conanrun")

        self.output.info("HarmonyOS ELF checks: PASSED")
