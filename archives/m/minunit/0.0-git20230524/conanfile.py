#!/usr/bin/env python3
"""Conan recipe — minunit 0.0-git20230524 (single-header C unit test framework).

minunit 是 siu（David Siñuela Pastor）维护的极简单元测试框架：整个库只有
一个头文件 minunit.h（MU_TEST/MU_TEST_SUITE 定义测试，MU_RUN_TEST/
MU_RUN_SUITE 驱动执行，mu_check / mu_assert / mu_assert_int_eq /
mu_assert_double_eq / mu_assert_string_eq 五个断言宏 + mu_fail，MU_REPORT
输出统计与 real/proc 计时，MU_EXIT_CODE 返回失败计数）。

版本号依据：上游 master 线无 tag / 无 release（master-only 库），按仓库
规则取 0.0-gitYYYYMMDD —— master HEAD
  a0586569bd8abfb7a37390d670484c201e9173bf（2023-05-24 提交）
→ 0.0-git20230524（conandata.yml 官方 master tarball URL + 实测 sha256）。

形态选型（参照 kernel-headers 6.12.77 / daw-utf-range 2.2.6 header-only 先例）：
- package_type = "header-library"，package() 仅拷贝 minunit.h → include/
  （+ MIT-LICENSE.txt → licenses/），无任何编译产物入库；
- 上游无构建系统（根目录无 CMakeLists/Makefile；ci/Makefile 仅供官方 CI
  编译 example），build() 直接以 profile 注入的 OHOS clang（R33：从
  tools.build:compiler_executables 取，不裸用 ${CC}）编译上游官方测试
  minunit_example.c 并按官方契约运行：ci/check_example.sh 断言
  exit code == 6 → PASS（11 个 MU_TEST 中 6 个为框架故意演示失败用例，
  MU_EXIT_CODE = minunit_fail = 6，exit 6 即套件按设计行为完整运行）；
- W0 实测零依赖：minunit.h 仅用 C99 标准库 + POSIX 计时器
  （unistd/time/sys/time/sys/resource/sys/times），无第三方依赖。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class MinunitConan(ConanFile):
    name = "minunit"
    version = "0.0-git20230524"
    description = "Minimal unit testing framework for C (single header minunit.h)"
    license = "MIT"
    homepage = "https://github.com/siu/minunit"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("unit-test", "testing-framework", "header-only", "c", "embedded")

    package_type = "header-library"
    implements = ["auto_header_only_mode"]
    # header-only：settings 声明但 binary 由 header-only 模式归一
    settings = "os", "compiler", "build_type", "arch"

    # 源码只读（build 阶段产物全部落在 build 目录）
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        # 纯头文件包：任何配置产出同一组头文件
        self.info.clear()

    def source(self):
        # R39：官方单 URL（GitHub master tarball；master HEAD 即
        # a0586569bd8abfb7a37390d670484c201e9173bf = 2023-05-24）。
        # CI 自动为 GitHub URL 追加镜像 fallback，勿手写镜像。
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # ── 上游官方测试（进统计表，真编译真运行）────────────────────
        # 上游官方 CI 入口（.travis.yml / appveyor.yml 的 script）：
        #   (cd ci && make && ./check_example.sh)
        #   ci/Makefile:      $(CC) -Wall -Wextra -I../ minunit_example.c
        #                     $(LIBS) -o minunit_example   （LIBS = -lm，
        #                     仅 UNAME_S == Linux 时追加 -lrt）
        #   ci/check_example.sh: ./minunit_example 后断言 exit code == 6
        # R33：编译器从 conf 注入（profile tools.build:compiler_executables），
        # 禁止裸用 ${CC}/${CFLAGS} shell 变量。
        compilers = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        cc = compilers.get("c", "clang")

        example_src = os.path.join(self.source_folder, "minunit_example.c")
        example_bin = os.path.join(self.build_folder, "minunit_example")

        # 构建宿主 uname 为 HarmonyOS → 按上游 Makefile 自身分支逻辑不链
        # -lrt（OHOS musl 的 timer 函数全在 libc，librt 为 stub），仅 -lm。
        self.run(
            "{cc} -std=c99 -Wall -Wextra -I{inc} {src} -lm -o {bin}".format(
                cc=cc, inc=self.source_folder, src=example_src, bin=example_bin
            )
        )

        if can_run(self):
            # 官方契约：exit code == 6 → 套件 PASS（6 个故意失败用例是
            # 框架特性：演示/验证断言捕获能力，MU_EXIT_CODE = 失败计数）。
            retcode = self.run("./minunit_example", cwd=self.build_folder, ignore_errors=True)
            if retcode != 6:
                raise ConanException(
                    "minunit upstream official test FAILED: ci/check_example.sh "
                    "contract expects exit code 6, got %d" % retcode
                )
            self.output.info(
                "minunit upstream official test PASS "
                "(exit code 6 as per ci/check_example.sh: 11 tests / 11 assertions, "
                "6 designed-to-fail demo cases behaved as expected)"
            )
        else:
            self.output.warning(
                "cross-building: upstream example compiled but runtime check skipped"
            )

    def package(self):
        # 许可证
        copy(self, "MIT-LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 唯一头文件 → include/ 根（消费者 #include <minunit.h>）
        copy(self, "minunit.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "minunit")
        self.cpp_info.set_property("cmake_target_name", "minunit::minunit")
        self.cpp_info.set_property("pkg_config_name", "minunit")
        # minunit.h 使用 fabs/log10（math.h）→ 消费者链接 libm（musl 中
        # libm 已并入 libc，-lm 为无害空操作；glibc 侧为真实依赖）
        self.cpp_info.system_libs = ["m"]
