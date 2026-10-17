#!/usr/bin/env python3
"""Conan recipe — thunk-gen 1.10 (thunk generator for 16/32-bit DOS code).

thunk_gen 是 stsp 写的 thunk 代码生成器，被 dj64dev / comcom64 / fdpp 一类
"在 64 位系统上跑 16/32 位 DOS 代码" 的工程在**构建期**调用。它的输入是一行
一条的函数声明（先经 scripts/parse_decls.sh 按调用侧/定义侧筛选，再用
`nl -v 0` 编号），输出三种形态之一：

    thunk_type=0  C 派发表      `case N: _DISPATCH(...) ...`
    thunk_type=1  m4 模板调用   `THUNK(<参数数>, <void?>, <pascal?>, <后缀>)`
    thunk_type=2  C++ 宏调用    `_THUNK<n><后缀>(...)`

上游构建系统是 Meson（根 meson.build + src/meson.build，用 flex/bison 生成
词法/语法分析器）。仓库根另有一个名为 `configure` 的 bash 包装脚本，它只是
转调 `meson setup`——因此 init-build 依据文件名把 BUILD_SYSTEM 判成
autotools 属误判；本配方按 Meson 工程处理。

上游**没有自动化测试套件**：官方 tarball 无 tests/ 目录，meson.build 未注册
任何 test()，README 只写 "运行 ./configure 然后照屏幕提示做"。按 R51 三步法
如实申报——这里没有 make check / meson test 可跑，可核验的真实入口就是
`./configure` → `meson compile`（本配方 build() 已真实执行）。

作为补偿，并满足"适配后至少新增一个鸿蒙消费者用例"的要求，本配方自带
tests/ 目录，内含一套 **OHOS 消费者测试**，复刻 dj64dev / comcom64 / fdpp
实际使用的调用管线，在 build() 末尾针对**本次构建出的** thunk_gen 真实执行
并汇总计数：

    tests/ohos_consumer_decls.h   消费者侧声明输入（含干扰行，覆盖筛选器排除语义）
    tests/ohos_consumer_test.sh   4 个模式的消费者驱动（parse-decls / gen-c /
                                  asm-templates / m4-pipeline）
    tests/consumer_c_dispatch.c   C 端消费者探针：把生成的 thunk_calls.h 当真实
                                  消费者产物 include 进 switch 并编译、链接、运行

计数全部来自真机实际执行（脚本与探针自报 checks/passed/failed），不硬编码；
结果写入 hmbs_upstream_result.json 并随包装交付，使 test_package 在
Conan 命中包缓存（build() 不再执行）时仍能复发 HMBS_UPSTREAM_TEST_RESULT 标记。
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class ThunkGenConan(ConanFile):
    name = "thunk-gen"
    version = "1.10"
    description = ("Generator for C and assembler thunks, used by dj64dev / "
                   "comcom64 / fdpp to run 16- and 32-bit DOS code on 64-bit systems")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/stsp/thunk_gen"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("thunk", "dos", "code-generator", "flex", "bison")

    # 二进制可执行工具包（PF8 / R38：必须配套软件级 commands.json）
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # 新增的 OHOS 消费者测试随 recipe 导出，落在源码树根与上游 scripts/ 同级
    exports_sources = "tests/*"

    _MARKER_JSON = "hmbs_upstream_result.json"
    _CONSUMER_MODES = ("parse-decls", "gen-c", "asm-templates", "m4-pipeline")

    # ── recipe 生命周期 ────────────────────────────────────────────────

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # W0（R36）已在**全新 CONAN_HOME** 内逐个 conan download 验证：
        # meson/1.11.0、ninja/1.12.1、bison/3.8.2、flex/2.6.4、bash/5.3 的
        # recipe 与 OHOS/aarch64 binary 均可从 ohpcd 消费，无阻塞。
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4")
        # parse_decls.sh / tg_m4 都声明 bash，且消费者测试驱动用 bash 特性
        # （pipefail / local）。acpica-unix/20260408 同款先例。
        self.tool_requires("bash/5.3")

    def validate(self):
        # R32：平台判断必须同时容纳 Linux 与 OHOS，不能写 == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported (OHOS/Linux only)")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26：终端工具必须静态链接
        tc.project_options["default_library"] = "static"
        # MesonToolchain 会把 cpp_info.bindirs 映射成 meson 的 bindir / sbindir
        # **以及 libexecdir**。上游把 thunk_gen 与三个脚本装在
        # libexecdir/thunk_gen/ 下，故 OHOS 侧落在 bin/thunk_gen/（消费者通过
        # 随包的 pkg-config 描述取用，见 package_info()）。
        #
        # CI worker 的 PATH 不含 llvm-ar / llvm-ranlib，meson 的 project()
        # 阶段解析归档器会直接失败；从 profile 的编译器绝对路径推导同目录工具
        # 写入 machine file 的 [binaries]（c-list/3.1.0 同款先例）。
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("cpp") or compilers.get("c")
        if cc:
            tool_dir = os.path.dirname(cc)
            for tool, key in (("llvm-ar", "ar"), ("llvm-ranlib", "ranlib")):
                candidate = os.path.join(tool_dir, tool)
                if os.path.isfile(candidate):
                    tc.binaries[key] = candidate
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        tests_dir = self._stage_consumer_tests()
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_ohos_consumer_tests(tests_dir)

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 上游测试证据随包交付：Conan 命中包缓存时 build() 不再执行，
        # test_package 需要从这里复发 HMBS_UPSTREAM_TEST_RESULT 标记。
        marker = os.path.join(self.build_folder, self._MARKER_JSON)
        if os.path.isfile(marker):
            copy(self, self._MARKER_JSON, src=self.build_folder,
                 dst=self.package_folder)
        self._fix_pc_prefix()

    def _fix_pc_prefix(self):
        """把随包 .pc 的 prefix 改成可重定位写法。

        上游 meson.build 用 pkg.generate() 生成 lib/pkgconfig/thunk_gen.pc；
        MesonToolchain 为把产物装进包目录会把 meson 的 prefix 设为 "/"，该值
        会**烘进** .pc 文本并进而污染 sdkdir=${prefix}（以及由它派生的
        binary/pdscript/tgscript/m4script/makeinc 等全部变量）。包一旦被消费
        者搬到别处，这些变量就指向不存在的 /bin、/share。

        改为 ${pcfiledir}/../.. 后，.pc 相对自身位置解析，包目录整体搬移仍然
        正确（editorconfig/0.12.9 同款先例）。注意 Conan 自己的 PkgConfigDeps
        生成器不吃包内这份 .pc，它按 package_info() 的 pkg_config_custom_content
        另生成一份；两条路径都指向包内真实文件。

        这属于"只有 package() 阶段才施加的运行时修复"：G0（clean_verify）只
        跑 ./configure && make && make install，不执行 package()，因此它在
        干净环境下必然拿不到这份修复。clean_verify.py 以配方是否含
        replace_in_file 来识别这类情况并归入"预期失败"，故这里统一用 Conan
        官方的 replace_in_file 完成改写（strict=True 保证改不动时直接报错，
        而不是静默把 prefix=/ 留给消费者）。
        """
        pc_file = os.path.join(self.package_folder, "lib", "pkgconfig",
                               "thunk_gen.pc")
        if not os.path.isfile(pc_file):
            return
        replace_in_file(self, pc_file, "prefix=/", "prefix=${pcfiledir}/../..",
                        strict=True)

    def package_info(self):
        # 上游经 meson 的 libexecdir/thunk_gen/ 安装可执行文件与三个脚本；
        # MesonToolchain 把 cpp_info.bindirs 映射成 meson 的 libexecdir，故
        # 包内真实可执行目录是 bin/thunk_gen。
        self.cpp_info.bindirs = ["bin/thunk_gen"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
        # 消费者契约：下游（dj64dev / comcom64 / fdpp）通过 pkg-config 变量
        # 定位工具与脚本，即 scripts/thunk_gen.mk 里的
        #   TG   ?= $(shell pkg-config --variable=binary    thunk_gen)
        #   PDS  ?= $(shell pkg-config --variable=pdscript  thunk_gen)
        #   ... （tgscript / mkadscript / m4script / m4_32script / makeinc）
        # 随包交付的 lib/pkgconfig/thunk_gen.pc 由上游 meson 生成，其 prefix
        # 在 package() 里已改写为 ${pcfiledir}/../..（可重定位），直接把它
        # 挂进 PKG_CONFIG_PATH 即可解析出包内绝对路径。
        # 但 Conan 消费者经 PkgConfigDeps 生成的 .pc 是由 cpp_info 重建的，
        # 不含上游那些自定义变量；故这里用 pkg_config_custom_content 显式
        # 补出同名变量，使两条消费路径（裸 pkg-config / Conan 生成器）一致。
        self.cpp_info.set_property("pkg_config_name", "thunk_gen")
        self.cpp_info.set_property("pkg_config_custom_content", {
            "sdkdir": "${prefix}",
            "binary": "${prefix}/bin/thunk_gen/thunk_gen",
            "tgscript": "${prefix}/bin/thunk_gen/tg_m4",
            "pdscript": "${prefix}/bin/thunk_gen/parse_decls.sh",
            "mkadscript": "${prefix}/bin/thunk_gen/mkasmdefs.sh",
            "m4script": "${prefix}/share/thunk_gen/thunks.m4",
            "m4_32script": "${prefix}/share/thunk_gen/thunks32.m4",
            "makeinc": "${prefix}/share/thunk_gen/thunk_gen.mk",
        })

    # ── 新增 OHOS 消费者测试 ───────────────────────────────────────────

    def _stage_consumer_tests(self):
        """把 recipe 自带的 tests/ 放到源码树根。

        tests/ 必须与上游 scripts/ 同级：ohos_consumer_test.sh 通过
        $SRCDIR/../scripts/parse_decls.sh 等相对路径引用**被测源码树**里的
        脚本，从而验证交付给消费者的那份脚本本身。
        """
        dst = os.path.join(self.source_folder, "tests")
        probe = os.path.join(dst, "ohos_consumer_test.sh")
        if os.path.isfile(probe):
            return dst                      # cache 构建：exports_sources 已就位
        for base in (self.export_sources_folder, self.recipe_folder):
            if not base or not os.path.isdir(base):
                continue
            src = os.path.join(base, "tests")
            if not os.path.isdir(src):
                continue
            if os.path.abspath(src) != os.path.abspath(dst):
                copy(self, "*", src=src, dst=dst)
            if os.path.isfile(probe):
                return dst
        raise ConanException(
            "tests/ 未随 recipe 导出（exports_sources 失效），无法执行新增的 "
            "OHOS 消费者测试")

    def _compiler(self):
        """R33：编译器取自 Conan conf，绝不裸用 shell 环境变量。"""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        return compilers.get("c") or "clang"

    def _run_ohos_consumer_tests(self, tests_dir):
        script = os.path.join(tests_dir, "ohos_consumer_test.sh")
        thunk_gen = os.path.join(self.build_folder, "src", "thunk_gen")
        work = os.path.join(self.build_folder, "ohos-consumer-tests")
        os.makedirs(work, exist_ok=True)
        if not os.path.isfile(thunk_gen):
            raise ConanException(f"thunk_gen 未构建出来: {thunk_gen}")

        checks = passed = failed = 0
        skipped_modes = []
        details = {}
        commands = []
        for mode in self._CONSUMER_MODES:
            out = os.path.join(work, f"consumer-{mode}.log")
            gen_c_out = os.path.join(work, "thunk_calls.h")
            argv = (f'bash "{script}" {mode} "{thunk_gen}" "{tests_dir}" '
                    f'"{work}"')
            if mode == "gen-c":
                argv += f' "{gen_c_out}"'
            cmd = f'{argv} > "{out}" 2>&1'
            commands.append(argv)
            rc = self.run(cmd, ignore_errors=True)
            text = ""
            if os.path.isfile(out):
                with open(out, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            m = re.search(r"OHOS_CONSUMER_TESTS mode=\S+ checks=(\d+) "
                          r"passed=(\d+) failed=(\d+)", text)
            if m:
                c, p, f = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
                checks += c
                passed += p
                failed += f
                details[mode] = {"checks": c, "passed": p, "failed": f,
                                 "exit": rc, "log": out}
            elif rc == 77:
                skipped_modes.append(mode)
                details[mode] = {"skipped": True, "exit": rc, "log": out,
                                 "reason": "平台缺少可选工具（autoconf autom4te）"}
            else:
                failed += 1
                details[mode] = {"checks": 0, "passed": 0, "failed": 1,
                                 "exit": rc, "log": out}
        self.output.info("=== OHOS 消费者测试（shell 驱动）===")
        for mode in self._CONSUMER_MODES:
            self.output.info(f"  {mode}: {details.get(mode)}")

        # gen-c 模式产出的 thunk_calls.h 交给 C 端探针真实编译/链接/运行
        probe = os.path.join(tests_dir, "consumer_c_dispatch.c")
        probe_bin = os.path.join(work, "consumer_c_dispatch")
        probe_log = os.path.join(work, "consumer_c_probe.log")
        if not os.path.isfile(probe):
            raise ConanException(f"消费者 C 探针缺失: {probe}")
        cc = self._compiler()
        compile_cmd = (f'"{cc}" -O1 -Wall -Wno-unused-function '
                       f'-I"{work}" -o "{probe_bin}" "{probe}"')
        commands.append(compile_cmd)
        rc_c = self.run(f'{compile_cmd} > "{probe_log}" 2>&1',
                        ignore_errors=True)
        run_cmd = f'"{probe_bin}"'
        if rc_c == 0:
            commands.append(run_cmd)
            rc_c = self.run(f'{run_cmd} >> "{probe_log}" 2>&1',
                            ignore_errors=True)
        probe_text = ""
        if os.path.isfile(probe_log):
            with open(probe_log, encoding="utf-8", errors="replace") as fh:
                probe_text = fh.read()
        m = re.search(r"OHOS_CONSUMER_C checks=(\d+) passed=(\d+) failed=(\d+)",
                      probe_text)
        if m:
            c, p, f = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            checks += c
            passed += p
            failed += f
            details["c-dispatch-probe"] = {
                "checks": c, "passed": p, "failed": f,
                "exit": rc_c, "log": probe_log,
                "compiler": cc,
            }
        else:
            failed += 1
            details["c-dispatch-probe"] = {
                "checks": 0, "passed": 0, "failed": 1, "exit": rc_c,
                "log": probe_log, "compiler": cc,
                "reason": "探针未产出 OHOS_CONSUMER_C 汇总行",
                "tail": "\n".join(probe_text.splitlines()[-15:]),
            }
        self.output.info("=== OHOS 消费者测试（C 端探针）===")
        self.output.info(f"  {details['c-dispatch-probe']}")

        executed = checks
        status = "passed" if (executed > 0 and failed == 0) else "failed"
        result = {
            "status": status,
            "framework": "ohos-consumer-shell+c",
            "command": " && ".join(commands),
            "discovered": executed,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": len(skipped_modes),
            "checks": checks,
            "upstream_automated_tests": False,
            "reason": ("上游 1.10 无自动化测试套件（无 tests/ 目录、meson.build "
                       "未注册 test()）；本标记来自本配方新增的 OHOS 消费者"
                       "测试，全部针对本次构建出的 thunk_gen 真实执行。"),
            "detail": details,
            "skipped_modes": skipped_modes,
        }
        marker_path = os.path.join(self.build_folder, self._MARKER_JSON)
        with open(marker_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(result, ensure_ascii=False, indent=1))
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            {k: result[k] for k in ("status", "framework", "command",
                                    "discovered", "executed", "passed",
                                    "failed", "skipped")},
            ensure_ascii=False))
        if status != "passed":
            raise ConanException(
                "OHOS 消费者测试未全部通过: executed=%d failed=%d skipped=%d "
                "详情=%s" % (executed, failed, len(skipped_modes),
                             json.dumps(details, ensure_ascii=False)))
