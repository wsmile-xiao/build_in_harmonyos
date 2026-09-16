#!/usr/bin/env python3
"""Conan recipe for libwapcaplet 0.4.3 (NetSurf string internment library).

libwapcaplet 是 NetSurf 浏览器组件库，上游使用 NetSurf 自有构建系统
（Makefile include $(NSSHARED)/makefiles/Makefile.tools），本平台无
netsurf-buildsystem 包。补丁 0001-Makefile.patch 将顶层 Makefile 替换为
standalone Makefile（保留原编译标志、去除 -Werror 以兼容 clang 15，
与历史适配 0.4.3.1/0.4.3.2 一致）。

构建：make && make install PREFIX=<package_folder>
测试：上游 `make check` 依赖 libcheck（test/testmain.c 直接 #include
<check.h>），本平台无 libcheck 包。build() 编译运行内嵌的等价检查程序
（覆盖与上游 test/basictests.c 同一组 lwc_string_* API，12 项断言），
解析 CHECK_PASS 行并输出 HMBS_UPSTREAM_TEST_RESULT 机器证据；
test_package 以消费者视角用 CMake 调用真实 API 验证（16 个断言）。

OHOS 陷阱（E120）：OHOS SDK 的 lld 链接 libxml2.so.16，需要把 SDK llvm 的
lib 目录注入 LD_LIBRARY_PATH，否则链接器无法启动。库本身是静态 .a，无需
ELF 签名/RPATH（R38 不适用，属库类型）。
"""
import json
import os
import re
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout

# 上游等价检查的断言项数（与 _UPSTREAM_CHECK_SRC 中的 CHECK_PASS 行一一对应）
UPSTREAM_CHECK_COUNT = 12

# 上游等价检查程序：不依赖 libcheck，直接调用 lwc_string_* 公共 API。
# 覆盖项与上游 test/basictests.c 相同（intern/data/length、指针同一性、
# isequal、caseless、hash、substring、tolower、引用计数、内嵌 NUL）。
# 每项成功打印一行 "CHECK_PASS: <name>"，任一失败打印 CHECK_FAIL 行并
# 返回该项专属的非零退出码（1-12 按项编号，setup 类失败用 20/21）。
_UPSTREAM_CHECK_SRC = r"""
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include <libwapcaplet/libwapcaplet.h>

#define CHECK(name, cond, code) do { \
    if (!(cond)) { \
        fprintf(stderr, "CHECK_FAIL: %s\n", name); \
        return code; \
    } \
    printf("CHECK_PASS: %s\n", name); \
} while (0)

int main(void)
{
    lwc_string *str1 = NULL, *str2 = NULL, *str3 = NULL, *sub = NULL;
    bool res;
    lwc_hash hash;
    lwc_error err;

    err = lwc_intern_string("hello", 5, &str1);
    CHECK("intern-string", err == lwc_error_ok && str1 != NULL, 1);
    CHECK("data-length", lwc_string_length(str1) == 5 &&
        strncmp(lwc_string_data(str1), "hello", 5) == 0, 2);

    err = lwc_intern_string("hello", 5, &str2);
    CHECK("same-pointer", err == lwc_error_ok && str1 == str2, 3);

    err = lwc_intern_string("world", 5, &str3);
    CHECK("diff-pointer", err == lwc_error_ok && str1 != str3, 4);

    err = lwc_string_isequal(str1, str2, &res);
    CHECK("isequal-true", err == lwc_error_ok && res == true, 5);
    err = lwc_string_isequal(str1, str3, &res);
    CHECK("isequal-false", err == lwc_error_ok && res == false, 6);

    {
        lwc_string *uc = NULL;
        err = lwc_intern_string("HELLO", 5, &uc);
        if (err != lwc_error_ok) {
            fprintf(stderr, "CHECK_FAIL: caseless-setup\n");
            return 20;
        }
        err = lwc_string_caseless_isequal(str1, uc, &res);
        CHECK("caseless-true", err == lwc_error_ok && res == true, 7);
        err = lwc_string_caseless_isequal(str1, str3, &res);
        CHECK("caseless-false", err == lwc_error_ok && res == false, 8);
        lwc_string_unref(uc);
    }

    hash = lwc_string_hash_value(str1);
    printf("hash(hello) = %u\n", (unsigned) hash);
    CHECK("hash-equal", hash != 0 && lwc_string_hash_value(str2) == hash, 9);

    err = lwc_intern_substring(str1, 1, 3, &sub);
    CHECK("substring", err == lwc_error_ok && lwc_string_length(sub) == 3 &&
        strncmp(lwc_string_data(sub), "ell", 3) == 0, 10);
    lwc_string_unref(sub);
    err = lwc_intern_substring(str1, 3, 10, &sub);
    CHECK("substring-range", err == lwc_error_range, 11);

    {
        lwc_string *uc = NULL, *lower = NULL;
        lwc_refcounter before;
        lwc_string *r1 = NULL, *r2 = NULL;
        err = lwc_intern_string("HeLLo", 5, &uc);
        if (err != lwc_error_ok) {
            fprintf(stderr, "CHECK_FAIL: tolower-setup\n");
            return 21;
        }
        err = lwc_string_tolower(uc, &lower);
        if (err != lwc_error_ok || lwc_string_length(lower) != 5 ||
            strncmp(lwc_string_data(lower), "hello", 5) != 0) {
            fprintf(stderr, "CHECK_FAIL: tolower-refcnt\n");
            return 12;
        }
        lwc_string_unref(lower);
        lwc_string_unref(uc);
        err = lwc_intern_string("refcount", 8, &r1);
        if (err != lwc_error_ok) {
            fprintf(stderr, "CHECK_FAIL: tolower-refcnt\n");
            return 12;
        }
        before = r1->refcnt;
        r2 = lwc_string_ref(r1);
        if (r2 != r1 || r1->refcnt != before + 1) {
            fprintf(stderr, "CHECK_FAIL: tolower-refcnt\n");
            return 12;
        }
        lwc_string_unref(r1);
        lwc_string_unref(r2);
        printf("CHECK_PASS: tolower-refcnt\n");
    }

    lwc_string_unref(str1);
    lwc_string_unref(str2);
    lwc_string_unref(str3);

    printf("UPSTREAM_EQUIV_ASSERTIONS: %d passed\n", UPSTREAM_CHECK_COUNT_PLACEHOLDER);
    return 0;
}
""".replace("UPSTREAM_CHECK_COUNT_PLACEHOLDER", str(UPSTREAM_CHECK_COUNT))


class LibwapcapletConan(ConanFile):
    name = "libwapcaplet"
    version = "0.4.3"
    description = "String internment and management tools (NetSurf project)"
    license = "MIT"
    homepage = "https://www.netsurf-browser.org/projects/libwapcaplet/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libwapcaplet 无运行时/编译依赖
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libwapcaplet is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)
        # standalone Makefile builds in-source (objects next to sources)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sdk_llvm_libdir(self):
        """E120: 定位 SDK llvm 的 lib 目录（含 libxml2.so.16）。

        优先从编译器可执行文件解析（readlink 链 → llvm/bin 的父目录/lib），
        无法解析时回退到已知 SDK 路径，最后仍不存在则跳过（编译本身不依赖）。
        """
        # R33: tools.build:compiler_executables 是 dict conf（R33），
        # 必须整体读取后取 "c" 键，不能用子键语法 :c
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        candidate = None
        try:
            p = Path(cc)
            while p.is_symlink():
                p = Path(os.path.realpath(p))
            # .../llvm/bin/clang -> .../llvm/lib
            bin_dir = p.parent if p.parent.name == "bin" else None
            if bin_dir and (bin_dir.parent / "lib").is_dir():
                candidate = str(bin_dir.parent / "lib")
        except Exception:
            candidate = None
        if candidate is None:
            candidate = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if os.path.isdir(candidate):
            return candidate
        return ""

    def _run_upstream_equiv_check(self, cc):
        """编译运行上游等价检查，输出 HMBS_UPSTREAM_TEST_RESULT 机器证据。

        上游 `make check` 依赖 libcheck（test/testmain.c 直接 #include
        <check.h>），本平台无 libcheck 包。此处运行覆盖同一组 lwc_string_*
        API 的等价检查（12 项，见 _UPSTREAM_CHECK_SRC），逐项 CHECK_PASS
        计数；退出码为 0 不等于通过，必须数够 12 行 PASS 才判 passed。
        """
        include_dir = os.path.join(self.source_folder, "include")
        lib_candidates = [
            os.path.join(self.build_folder, "libwapcaplet.a"),
            os.path.join(self.source_folder, "libwapcaplet.a"),
        ]
        static_lib = next((p for p in lib_candidates if os.path.isfile(p)), None)
        if static_lib is None:
            raise ConanException("libwapcaplet.a not built: %s" % lib_candidates)
        check_src = os.path.join(self.build_folder, "upstream_check.c")
        check_exe = os.path.join(self.build_folder, "upstream_check")
        with open(check_src, "w", encoding="utf-8", newline="\n") as f:
            f.write(_UPSTREAM_CHECK_SRC)
        cc_cmd = [cc, "-std=c99", "-I", include_dir, check_src, static_lib, "-o", check_exe]
        self.output.info("Compiling upstream-equivalent check: %s" % " ".join(cc_cmd))
        proc = subprocess.run(
            cc_cmd,
            cwd=self.build_folder,
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        self.output.info(proc.stdout or "")
        if proc.returncode != 0:
            raise ConanException("upstream-equivalent check failed to compile")
        run = subprocess.run(
            [check_exe],
            cwd=self.build_folder,
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = run.stdout or ""
        self.output.info(output)
        passed = len(re.findall(r"^CHECK_PASS: ", output, re.MULTILINE))
        failed = len(re.findall(r"^CHECK_FAIL: ", output, re.MULTILINE))
        executed = passed + failed
        if run.returncode == 0 and failed == 0 and passed == UPSTREAM_CHECK_COUNT:
            result = {
                "status": "passed",
                "framework": "custom-upstream-equiv",
                "command": " ".join(cc_cmd) + " && ./upstream_check",
                "discovered": UPSTREAM_CHECK_COUNT,
                "executed": executed,
                "passed": passed,
                "failed": 0,
                "skipped": 0,
            }
        else:
            result = {
                "status": "failed",
                "framework": "custom-upstream-equiv",
                "command": " ".join(cc_cmd) + " && ./upstream_check",
                "discovered": UPSTREAM_CHECK_COUNT,
                "executed": executed,
                "passed": passed,
                "failed": failed if failed or run.returncode != 0 else 1,
                "skipped": 0,
                "reason": "rc=%s passed=%s failed=%s, expected %s CHECK_PASS lines"
                % (run.returncode, passed, failed, UPSTREAM_CHECK_COUNT),
            }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        # 双通道输出（stdout + Conan output）：HMBS 预检抓取原始 stdout，
        # 输出缓冲下仍可稳定采集（沿用 ayatana-ido/0.10.4-v2 既定模式）。
        print(msg, flush=True)
        self.output.info(msg)
        # 持久化供 test_package 在 Conan 缓存命中（build() 被跳过）时复发证据
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8") as f:
                json.dump(result, f)
        except OSError:
            pass
        if result["status"] != "passed":
            raise ConanException("libwapcaplet upstream-equivalent check failed")

    def build(self):
        apply_conandata_patches(self)

        # E120: OHOS SDK lld 链接 libxml2.so.16，注入其 lib 目录到
        # LD_LIBRARY_PATH 使链接器可在 CI worker 上运行（SDK lib 路径
        # 不在默认 loader 搜索路径上）。
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            os.environ["LD_LIBRARY_PATH"] = sdk_lib + ":" + os.environ.get("LD_LIBRARY_PATH", "")

        # R33: 编译器/归档工具从 Conan conf 获取，禁止裸 shell 环境变量
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"
        # R9: -j1 (HMDFS 上 make -j>1 jobserver mkfifo 报 EPERM, E074)
        self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} -j1")
        # 上游官方测试（libcheck 缺失，用等价检查替代，见 MANIFEST 审计）
        self._run_upstream_equiv_check(cc)

    def package(self):
        # standalone Makefile 的 install 目标遵循 PREFIX/DESTDIR
        self.run(f"make install PREFIX={self.package_folder}")
        # test_package 复发上游证据用的持久化结果
        try:
            copy(self, "hmbs_upstream.json", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"), keep_path=False)
        except Exception:
            pass

    def package_info(self):
        # 库文件为 libwapcaplet.a，lib 名是 "wapcaplet"（pkg-config -lwapcaplet）
        self.cpp_info.libs = ["wapcaplet"]
        self.cpp_info.set_property("cmake_file_name", "LibWapcaplet")
        self.cpp_info.set_property("cmake_target_name", "LibWapcaplet::wapcaplet")
        self.cpp_info.set_property("pkg_config_name", "libwapcaplet")
