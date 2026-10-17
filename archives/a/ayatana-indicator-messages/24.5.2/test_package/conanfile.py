#!/usr/bin/env python3
"""Conan test_package — ayatana-indicator-messages 24.5.2.

上游测试真实执行（审查要求）：
  - build() 阶段（构建 uid 可 exec）：get() 拉取上游 24.5.2 源码（与主配方
    conandata.yml 同源），编译 tests/test-gactionmuxer.cpp + src/gactionmuxer.c
    （-DG_LOG_DOMAIN 与上游 src/CMakeLists.txt:42 一致），链接
    gtest/gmock/glib 静态链，真实运行 6 个 TEST
    （Sanity/Empty/AddAndRemove/ActionAttributes/Signals/ActivateAction），
    输出 gtest-run.log；任何断言失败（exit≠0）即 build 失败。
  - test() 阶段（app uid 只读，L0d 直接 self.run）：service 冒烟 + 探针断言
    gtest-run.log 含 "PASSED  6 tests"。
  - indicator-test（4 TEST_F）依赖 dbustest-1：OHOS 制品仓无配方、上游源码
    不可得 → 不可真实执行（适配方案见 MANIFEST/notes）；test-client（2 方法）
    依赖 GI typelib（需 ENABLE_INTROSPECTION=ON + gobject-introspection 工具
    链重建 libmessaging-menu）→ 适配方案见 MANIFEST。
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import get

# 与主配方 conandata.yml 的 sources 保持一致（Ubuntu archive orig tarball）
UPSTREAM_URL = ("https://archive.ubuntu.com/ubuntu/pool/universe/a/"
                "ayatana-indicator-messages/ayatana-indicator-messages_24.5.2.orig.tar.gz")
UPSTREAM_SHA256 = "a1304d2d28fde2912a91741856b2b6b2242d3b508f2666412b37a35005b3664b"


class AyatanaindicatormessagesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 上游 tests/test-gactionmuxer.cpp 依赖 GTEST/GMock（OHOS 制品仓可用）；
        # glib 显式声明（主配方 transitive 依赖在 test_package 图中
        # package_folder 可能未解析，编译测试需要其头文件/库路径）
        self.requires("gtest/1.17.0")
        self.requires("gmock/1.17.0")
        self.requires("glib/2.88.0.1")

    def _find_dep(self, name):
        # 按包名查找依赖并确认 package_folder 已解析（build() 阶段需要）
        for dep in self.dependencies.values():
            if dep.ref.name == name and dep.package_folder:
                return dep
        raise SystemExit(f"FAIL: dependency {name} (with package) not found in test graph")

    def _glib_layout_incs(self, glib):
        # glib 头布局：glib.h/gio.h 在 include/glib-2.0/，gio-unix 头在
        # include/gio-unix-2.0/，构建期生成的 glibconfig.h 在 lib/glib-2.0/include/
        return [os.path.join(glib.package_folder, p)
                for p in ("include/glib-2.0", "include/gio-unix-2.0",
                          "lib/glib-2.0/include")]

    def build(self):
        if not can_run(self):
            self.output.warning("skipped (cannot run on this platform)")
            return
        gtest = self._find_dep("gtest")
        gmock = self._find_dep("gmock")
        glib = self._find_dep("glib")

        # 1) 拉上游 24.5.2 源码（Ubuntu archive，CI 可达，与主配方 source() 同源）
        src = os.path.join(self.build_folder, "upstream")
        get(self, url=UPSTREAM_URL, sha256=UPSTREAM_SHA256,
            destination=src, strip_root=True)

        # 2) include/lib 目录：src/（gactionmuxer.h）+ glib 布局 + gtest/gmock；
        #    lib 含 glib/gtest/gmock + pcre2/zlib（glib 静态库传递依赖）
        inc = [os.path.join(src, "src")] + self._glib_layout_incs(glib) + [
            os.path.join(gtest.package_folder, "include"),
            os.path.join(gmock.package_folder, "include")]
        libs = [os.path.join(glib.package_folder, "lib"),
                os.path.join(gtest.package_folder, "lib"),
                os.path.join(gmock.package_folder, "lib")]
        for dep in self.dependencies.values():
            d = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(d) and d not in libs:
                libs.append(d)
        inc_args = " ".join(f"-I{p}" for p in inc)
        lib_args = " ".join(f"-L{p}" for p in libs)

        # 3) 编译（gactionmuxer.c 需 G_LOG_DOMAIN 与上游 src/CMakeLists.txt 一致，
        #    否则 g_test_expect_message 匹配不到日志域）+ 链接（gtest_main 提供
        #    main；glib 静态库完整传递链）+ 运行（GTest 输出 gtest-run.log；
        #    exit≠0 即 self.run 抛异常 → build 失败）
        bf = self.build_folder
        tgm_src = os.path.join(src, "tests", "test-gactionmuxer.cpp")
        gmux_src = os.path.join(src, "src", "gactionmuxer.c")
        # E266/CI：OHOS SDK 的 lld 链接器运行时依赖 libxml2.so.16（与主配方
        # conanfile generate() 同机制）；test_package 直接调 clang++/clang 时
        # 前置 SDK llvm/lib 到 LD_LIBRARY_PATH，否则 lld 加载失败
        # （Error relocating llvm/bin/lld: xmlFreeDoc: symbol not found）
        llvm_lib = next((d for d in glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")
            if os.path.isfile(os.path.join(d, "libxml2.so.16"))), None)
        env_pre = (f"export LD_LIBRARY_PATH={llvm_lib}:$LD_LIBRARY_PATH; "
                   if llvm_lib else "")
        build_cmd = (
            f"clang++ -std=c++17 -c {tgm_src} {inc_args} -o {os.path.join(bf, 'tgm.o')} && "
            f"clang -DG_LOG_DOMAIN=\\\"Ayatana-Indicator-Messages\\\" -c {gmux_src} {inc_args} "
            f"-o {os.path.join(bf, 'gmux.o')} && "
            f"clang++ {os.path.join(bf, 'tgm.o')} {os.path.join(bf, 'gmux.o')} {lib_args} "
            f"-lgtest_main -lgtest -lgmock -lgio-2.0 -lgmodule-2.0 -lgobject-2.0 -lglib-2.0 "
            f"-lffi -lintl -lpcre2-8 -lz -pthread "
            f"-o {os.path.join(bf, 'test-gactionmuxer')} && "
            f"{os.path.join(bf, 'test-gactionmuxer')} > {os.path.join(bf, 'gtest-run.log')} 2>&1"
        )
        build_cmd = env_pre + build_cmd
        self.run(build_cmd, env="conanrun")

    def test(self):
        if not can_run(self):
            self.output.warning("skipped (cannot run on this platform)")
            return
        # 冒烟：service 可执行文件已安装（原验证保留）
        dep = self.dependencies["ayatana-indicator-messages"]
        exe = os.path.join(dep.package_folder, "bin",
                           "ayatana-indicator-messages",
                           "ayatana-indicator-messages-service")
        if not os.path.isfile(exe):
            raise SystemExit(f"FAIL: service executable not found: {exe}")
        # L0d：直接 self.run()；探针做读取断言（service 冒烟 + gtest-run.log
        # 真实执行证据：PASSED 6 tests）
        self.run(f"python3 test_ayatana-indicator-messages.py {exe} {self.build_folder}",
                 env="conanrun")
