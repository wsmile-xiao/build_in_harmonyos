#!/usr/bin/env python3
"""Conan recipe for libpktriggercord — OHOS (HarmonyOS PC) aarch64 adaptation.

Upstream: https://github.com/asalamon74/pktriggercord (LGPL-3.0-or-later) —
Pentax DSLR remote control (tethering) library `pslr` + CLI.
Snapshot: commit c1177a48, Makefile `VERSION=0.85.01` == 目标版本 0.85.1。
上游没有 0.85.1 release 产物（`pktriggercord.spec:25` 的 Source URL 实测 404），
因此使用官方 commit-pinned GitHub archive URL。

构建路线（上游是裸 Makefile，没有任何"库"产物目标，配方自建）：
 1. `make cli` 编译 pslr* 目标文件（上游规则自带 -fPIC）并链接 pktriggercord-cli；
    这组目标文件就是库本体，CLI 是上游唯一的功能冒烟入口
    （`.travis.yml` script: `./pktriggercord-cli --version`），故在 build() 中真实
    执行作为上游测试，但不随包发布（包范围=库）。
 2. 同一组目标文件链接为 libpktriggercord.so（shared）或归档为 libpktriggercord.a。

OHOS 适配要点：
 - CFLAGS 陷阱（本次首个真实错误）：`Makefile:5` 为 `CFLAGS ?= -O3 -g -Wall -I$(JSONDIR)`。
   环境中任何 CFLAGS 都会整条顶掉默认值并丢掉内嵌 js0n 的 include 目录，真实报错：
   `pslr_model.c:45:10: fatal error: 'js0n.h' file not found`。
   对策：始终以 make 命令行变量（优先级高于环境）传入保留 `-Isrc/external/js0n` 的
   CFLAGS；编译器取自 Conan conf，绝不裸用 shell 的 ${CC}（R33）。
 - 排除 GUI 目标：`pktriggercord.c` 需要 GTK+ 2（`Makefile:18,20` pkg-config
   `gtk+-2.0 gmodule-2.0`；spec `BuildRequires: gtk2-devel`；Changelog
   "Requires at least gtk+ 2.18"）。GTK2 已 EOL 且不在 ohpcd 制品仓（仅
   gtk/3.24.x，其 pkg_config_name=gtk+-3.0）。实测失败证据：
   `make gui` -> `fatal error: 'gtk/gtk.h' file not found`。
 - 无 configure/CMake 步骤 -> 不需要 E007 config.guess/sub 补丁。
 - 依赖闭包为空：产物 `llvm-readelf -d` 实测 NEEDED 仅 `libc.so`；源码只用
   libc + libm（`Makefile:7 LDFLAGS ?= -lm`）与树内 vendored js0n（`Makefile:1`）。
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

# 上游 Makefile:80 SRCOBJNAMES —— 库对象全集（不含 GUI 的 pktriggercord.c）
LIB_OBJECTS = [
    "pslr.o", "pslr_enum.o", "pslr_scsi.o", "pslr_log.o", "pslr_lens.o",
    "pslr_model.o", "pktriggercord-servermode.o", "pslr_utils.o",
    "src/external/js0n/js0n.o",
]

# 上游 Makefile:22 VERSION（目标版本 0.85.1 的上游写法）
UPSTREAM_VERSION = "0.85.01"


class LibpktriggercordConan(ConanFile):
    name = "libpktriggercord"
    version = "0.85.1-20221221181244"
    description = ("Pentax DSLR remote-control (tethering) library pslr with "
                   "SCSI-generic transport, pkTriggerCord snapshot 0.85.01")
    license = "LGPL-3.0-or-later"
    homepage = "https://pktriggercord.melda.info"
    url = "https://github.com/asalamon74/pktriggercord"
    topics = ("pentax", "dslr", "tethering", "camera", "scsi")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # ─────────────────────────── 私有辅助（工具/命令）───────────────────────────
    def _tool(self, key, *fallbacks):
        """R33: 编译器一律取自 Conan conf；conf 不可执行时才回退 PATH。"""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cand = (compilers.get(key) or "").strip()
        if cand:
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
            self.output.warning("conf %s='%s' 不可执行，回退 PATH" % (key, cand))
        for name in fallbacks:
            found = shutil.which(name)
            if found:
                return found
        raise ConanException("找不到可用的 %s 编译器（conf 与 PATH 均无）" % key)

    def _run(self, cmd, cwd):
        self.output.info("+ %s" % cmd)
        proc = subprocess.run(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=1200,
                              env=os.environ.copy())
        out = proc.stdout or ""
        if proc.returncode != 0:
            self.output.info(out[-8000:])
            raise ConanException("command failed (rc=%s): %s\n%s"
                                 % (proc.returncode, cmd, out[-4000:]))
        return out

    def _smoke_cc(self, cc):
        """最小编译（+可执行时再运行），让工具链问题在这里暴露而非埋在 make 错误里。"""
        work = os.path.join(self.build_folder, "cc-smoke")
        os.makedirs(work, exist_ok=True)
        src = os.path.join(work, "smoke.c")
        with open(src, "w", encoding="utf-8") as f:
            f.write("int main(void){return 0;}\n")
        self._run('"%s" "%s" -o "%s"' % (cc, src, os.path.join(work, "smoke")),
                  cwd=work)
        if can_run(self):
            # 交叉构建（host != build）时只验证"能编译"，不执行 host 二进制
            self._run('"%s"' % os.path.join(work, "smoke"), cwd=work)
        self.output.info("C compiler smoke test passed: %s" % cc)

    def _make_vars(self):
        prefix = self.package_folder.replace("\\", "/")
        # 上游用 `CFLAGS ?=`，环境顶掉默认值就会丢 -I$(JSONDIR)：此处用命令行变量固定
        cflags = "%s -g -Wall -fPIC -Isrc/external/js0n" % (
            "-O3" if str(self.settings.build_type) == "Release" else "-O0")
        return 'CC="%s" AR="%s" CFLAGS="%s" LDFLAGS="-lm" PREFIX="%s"' % (
            self._tool("c", "clang", "cc"), self._tool("ar", "llvm-ar", "ar"),
            cflags, prefix)

    # ─────────────────────────── conan 生命周期 ───────────────────────────
    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ─────────────────────────────── build ───────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        out = self.build_folder
        os.makedirs(out, exist_ok=True)
        cc = self._tool("c", "clang", "cc")
        ar = self._tool("ar", "llvm-ar", "ar")
        self._smoke_cc(cc)

        # 上游对象集 + CLI（CLI 承载上游唯一功能测试入口）
        self._run("make cli %s -j1" % self._make_vars(), cwd=src)

        self._run_upstream_tests(src)

        # 库产物：上游 Makefile 无此目标，用同一组 -fPIC 对象自建（R1 参数最少化）。
        # DT_SONAME 显式给出（CI L5a 门禁要求）；不建 .so.0 版本链——HMDFS 上符号链接
        # 覆盖语义不可靠（§7/R5），下游统一经 conan 的 -L<libdir> -lpktriggercord 解析。
        objs = " ".join('"%s"' % os.path.join(src, o) for o in LIB_OBJECTS)
        if self.options.shared:
            self._run('"%s" -shared -Wl,-soname,libpktriggercord.so -o "%s" %s -lm'
                      % (cc, os.path.join(out, "libpktriggercord.so"), objs), cwd=out)
        else:
            self._run('"%s" rcs "%s" %s'
                      % (ar, os.path.join(out, "libpktriggercord.a"), objs), cwd=out)

    def _run_upstream_tests(self, src):
        """上游无测试框架（无 tests/ 目录、无 test|check 目标、无 ctest 注册）。

        唯一功能测试入口取自 .travis.yml script: `./pktriggercord-cli --version`；
        另补 1 项 `--help` 冒烟。`--status` 等其余命令需要真实相机，且默认
        `--timeout=0`（永久阻塞，本地实测挂起 350s 后需 kill），不作为测试入口。
        结果从真实运行解析，不硬编码。
        """
        cases = [
            ("version", ["./pktriggercord-cli", "--version"],
             lambda rc, o: rc == 0 and UPSTREAM_VERSION in o),
            ("help-usage", ["./pktriggercord-cli", "--help"],
             lambda rc, o: "Usage:" in o),
        ]
        if not can_run(self):
            # code-style §19: 统一走 self.output，不用 print()
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
                "status": "skipped", "framework": "upstream-cli-smoke",
                "command": "./pktriggercord-cli --version ; --help",
                "discovered": len(cases), "executed": 0, "passed": 0,
                "failed": 0, "skipped": len(cases),
                "reason": "交叉构建，host 二进制不可执行"}))
            return
        executed = passed = 0
        details = []
        for name, argv, ok in cases:
            cmd = " ".join('"%s"' % a for a in argv)
            proc = subprocess.run(cmd + " 2>&1", shell=True, cwd=src,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=120, env=os.environ.copy())
            out = proc.stdout or ""
            good = ok(proc.returncode, out)
            executed += 1
            passed += 1 if good else 0
            self.output.info("--- upstream case %s (rc=%s, %s) ---\n%s"
                             % (name, proc.returncode, "PASS" if good else "FAIL",
                                out[:1200]))
            details.append("%s:%s" % (name, "pass" if good else "fail"))
        failed = executed - passed
        status = "passed" if failed == 0 and executed == len(cases) else "failed"
        result = {
            "status": status, "framework": "upstream-cli-smoke",
            "command": "./pktriggercord-cli --version; ./pktriggercord-cli --help",
            "discovered": len(cases), "executed": executed, "passed": passed,
            "failed": failed, "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result,
                                                                ensure_ascii=False))
        if status != "passed":
            raise ConanException("libpktriggercord upstream tests failed: %s (%s)"
                                 % (result, ";".join(details)))

    # ────────────────────────────── package ──────────────────────────────
    def package(self):
        pkg = self.package_folder
        # 上游 Makefile:83 打包的根目录公共头（vendored js0n.h、Android 专用
        # android_scsi_sg.h 与 rad10/ 头文件均不导出）。conan 2 的 copy() 无
        # root 参数，故逐个显式复制（无 ** 的模式只匹配 src 顶层文件）。
        public_headers = [
            "pslr.h", "pslr_enum.h", "pslr_lens.h", "pslr_log.h", "pslr_model.h",
            "pslr_scsi.h", "pslr_utils.h", "pktriggercord-servermode.h",
        ]
        for h in public_headers:
            if not os.path.isfile(os.path.join(self.source_folder, h)):
                raise ConanException("公共头缺失: %s" % h)
            copy(self, h, src=self.source_folder, dst=os.path.join(pkg, "include"))
        copy(self, "pentax_settings.json", src=self.source_folder,
             dst=os.path.join(pkg, "share", "pktriggercord"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(pkg, "licenses"))
        if self.options.shared:
            copy(self, "libpktriggercord.so", src=self.build_folder,
                 dst=os.path.join(pkg, "lib"))
        else:
            copy(self, "libpktriggercord.a", src=self.build_folder,
                 dst=os.path.join(pkg, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["pktriggercord"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["share"]
        # CLI 只在 build() 中承载上游测试，不进入交付产物
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("pkg_config_name", "libpktriggercord")
        if self.settings.os in ("Linux", "OHOS"):  # R32
            self.cpp_info.system_libs = ["m"]
