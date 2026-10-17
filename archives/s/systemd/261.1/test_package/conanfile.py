#!/usr/bin/env python3
"""Conan test_package for systemd — R34 consumer checks.

L1 official test: verifies the packaged libsystemd client library exists under
<pkg>/lib/, is a valid aarch64 ELF shared object, and the public header
sd-bus.h is present under <pkg>/include/. R34 real artifact verification.

消费者硬门禁（至少 1 个真实消费者用例）：编译并运行 test_consumer.c——
仅通过公开头文件 <systemd/sd-event.h> 与公开 API（sd_event_new/
sd_event_add_time/sd_event_run/sd_event_unref）使用打包产物，实际运行
验证 timer 回调触发（可观察结果），确认第三方使用者可编译、链接、调用、
运行。
"""
import os
import subprocess
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resolve_cc(self):
        """解析 C 编译器（可移植，不再硬编码裸 clang）。

        优先级：
        1) Conan conf 注入的工具链 —— ci/conan/profiles/ohos-aarch64 的
           tools.build:compiler_executables={"c": "/data/service/hnp/bin/clang"}，
           CI/本地均从 profile 获得绝对路径，不依赖 shell PATH；
        2) 环境变量 CC（conanbuild.sh / env_info 注入或 CI 显式设置）；
        3) 兜底 PATH 中的 clang（仅本地开发环境，含 hnp 工具链 PATH 时可用）。
        """
        ce = {}
        try:
            ce = self.conf.get("tools.build:compiler_executables",
                               default={}, check_type=dict) or {}
        except Exception:
            ce = {}
        if ce.get("c"):
            return ce["c"]
        cc = os.environ.get("CC")
        if cc:
            return cc
        return "clang"

    def _sdk_llvm_lib_dir(self):
        """定位 OHOS SDK LLVM lib 目录（lld 动态依赖 libxml2.so.16 所在路径）。

        OHOS SDK 的 lld 链接器 NEEDED libxml2.so.16，若 subprocess 的
        LD_LIBRARY_PATH 不含 SDK `ohos/native/llvm/lib`，加载到缺 xml 符号的
        libxml2 即报 "Error relocating lld: xmlFreeDoc: symbol not found"
        （CI/本地环境差异）。本方法探测候选并验证 libxml2.so* 存在：
        1) 从 _resolve_cc() 编译器绝对路径相对推导（realpath 解析符号链接后
           <cc_dir>/../lib、<cc_dir>/../llvm/lib）；
        2) glob 探测 /data/service/hnp/ohos-sdk.org/ohos-sdk_*/.../llvm/lib 取最新；
        不硬编码 SDK 小版本目录名；找不到时返回 None（调用方给 warning 沿用现状）。
        """
        import glob as _glob
        cands = []
        cc = self._resolve_cc()
        if cc and os.path.isabs(cc):
            cc_real = os.path.realpath(cc)
            cc_dir = os.path.dirname(cc_real)
            for d in (os.path.join(cc_dir, "..", "lib"),
                      os.path.join(cc_dir, "..", "llvm", "lib"),
                      os.path.join(cc_dir, "..", "..", "native", "llvm", "lib")):
                cands.append(os.path.normpath(d))
        try:
            cands += sorted(
                _glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/"
                           "ohos/native/llvm/lib"),
                key=lambda p: os.path.basename(p), reverse=True)
        except Exception:
            pass
        seen = set()
        for d in cands:
            if d in seen:
                continue
            seen.add(d)
            if os.path.isdir(d) and _glob.glob(os.path.join(d, "libxml2.so*")):
                return d
        return None

    def _compile_and_run_consumer(self, pkg):
        """编译并运行真实消费者（公开 API，不包含库私有头/内部符号）。"""
        here = os.path.dirname(__file__)
        src = os.path.join(here, "test_consumer.c")
        exe = os.path.join(self.build_folder, "test_consumer")
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib")
        # OHOS clang 工具链（优先 Conan conf 注入，其次环境 CC，最后 PATH）
        cc = self._resolve_cc()
        cmd = [cc, "-I" + inc, "-o", exe, src, "-L" + lib, "-lsystemd",
               "-Wl,-rpath," + lib]
        self.output.info("consumer compile: %s" % " ".join(cmd))
        env = os.environ.copy()
        # E002 平台陷阱：OHOS /tmp 只读，clang 需可写临时目录（写入告警并以
        # worktree 内目录兜底，保证 CI/受限环境可移植）。
        if not env.get("TMPDIR"):
            tmpdir = os.path.join(self.build_folder, ".consumer-tmp")
            os.makedirs(tmpdir, exist_ok=True)
            env["TMPDIR"] = env["TMP"] = env["TEMP"] = tmpdir
            self.output.warning(
                "consumer compile: TMPDIR 未设置，使用 %s（OHOS /tmp 只读）"
                % tmpdir)
        # OHOS SDK lld 动态依赖 libxml2.so.16：LD_LIBRARY_PATH 前置 SDK LLVM lib
        # （E120/E132 场景；不覆盖现有，找不到候选时 warning 沿用现状，不伪造）。
        sdk_llvm_lib = self._sdk_llvm_lib_dir()
        if sdk_llvm_lib:
            env["LD_LIBRARY_PATH"] = sdk_llvm_lib + os.pathsep + \
                env.get("LD_LIBRARY_PATH", "")
            self.output.info("consumer compile: LD_LIBRARY_PATH 前置 SDK LLVM lib: %s"
                             % sdk_llvm_lib)
        else:
            self.output.warning(
                "consumer compile: 未找到含 libxml2.so* 的 SDK LLVM lib 目录，"
                "沿用现有 LD_LIBRARY_PATH（CI 若失败将报 lld xml* symbol not found）")
        subprocess.check_call(cmd, env=env)
        env2 = os.environ.copy()
        env2["LD_LIBRARY_PATH"] = lib + os.pathsep + env2.get("LD_LIBRARY_PATH", "")
        r = subprocess.run([exe], env=env2, capture_output=True, text=True)
        sys.stdout.write(r.stdout)
        if r.stderr:
            sys.stderr.write(r.stderr)
        if r.returncode != 0:
            raise SystemExit("CONSUMER FAILED (exit=%d)" % r.returncode)
        self.output.info("CONSUMER PASSED (public API sd_event_* runtime verified)")

    def test(self):
        if can_run(self):
            pkg = self.dependencies["systemd"].package_folder
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_systemd.py")
            self.run(f'{sys.executable} "{test_script}" "{pkg}"',
                     env="conanrun")
            self._compile_and_run_consumer(pkg)
