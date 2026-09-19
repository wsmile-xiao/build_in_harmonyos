#!/usr/bin/env python3
"""Conan recipe for soplex 7.1.6 — Sequential object-oriented Simplex (LP solver).

SoPlex is an LP solver library with an interactive command-line solver.
Build system: CMake (project SOPLEX, C++14, cmake_minimum_required 3.9).
Library output: libsoplex.a (static), libsoplex-pic.a (static)
Binary output:  bin/soplex (command-line LP solver, R38 -> commands.json)
Dependencies: gmp/6.3.0.1 (exact/rational arithmetic, C++ gmpxx), zlib/1.3.1.1 (gz I/O, -fPIC static).
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SoplexConan(ConanFile):
    name = "soplex"
    version = "7.1.6"
    description = "SoPlex - Sequential object-oriented Simplex, a linear programming (LP) solver"
    license = "Apache-2.0"
    homepage = "https://soplex.zib.de/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gmp/6.3.0.1 与 6.3.0 同一份上游 tarball（sha256 逐字一致），差异仅构建配置：
        # 6.3.0.1 加 --enable-cxx 产出 libgmpxx/gmpxx.h（SoPlex 有理数求解走 C++ 接口，
        # 纯 C 包不够用），且本仓适配配方无 m4 tool_require。真机预检曾解析到
        # conancenter 的 gmp/6.3.0，其 m4/1.4.19 configure 硬编码
        # /data/service/hnp/bin/bash（真机不可访问）且写只读 /tmp 而构建失败；
        # 用已适配的 6.3.0.1 切断该依赖链（maxima/mpfi 等同仓包同样钉 6.3.0.1）。
        self.requires("gmp/6.3.0.1")
        # zlib/1.3.1.1 与 1.3.1 同一份上游源码（sha256 一致），差异仅 CFLAGS=-fPIC。
        # 真机预检曾把裸 zlib/1.3.1 解析到 conancenter 的 CMake 配方，其 toolchain 置
        # CMAKE_SYSTEM_NAME=HarmonyOS（本机 cmake 无该平台模块）且编译器自检写只读
        # /tmp 而 configure 失败；1.3.1.1 是本仓 Makefile 适配配方（无 cmake），已首发
        # 到制品仓并被 curl/python/cups 等大包消费，切到它即命中预编译二进制。
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 编译器路径回退（R33 合规，经 Toolchain 落盘）：
        # profile 把 tools.build:compiler_executables 钉在
        # /data/service/hnp/bin/clang(++)，但真机工具链迁移后该路径在预检沙箱内
        # 不存在（本包 cmake configure 报 compiler identification unknown；
        # lz4/ayatana-indicator-keyboard 同款实证），致 toolchain 指向死路径。
        # conf 路径存在则沿用（CI worker）；缺失时回退到 PATH 发现的
        # clang/clang++（HMBS 已把工具目录前置进 PATH），经 tc.variables 落盘。
        try:
            _exes = self.conf.get("tools.build:compiler_executables") or {}
        except Exception:
            _exes = {}
        _cc_conf = _exes.get("c", "") if isinstance(_exes, dict) else ""
        _cxx_conf = _exes.get("cpp", "") if isinstance(_exes, dict) else ""
        if _cc_conf and not os.path.isfile(_cc_conf):
            self.output.info("compiler_fix: conf c %r missing" % _cc_conf)
            _cc = shutil.which("clang") or shutil.which("cc") or ""
            if _cc:
                self.output.info("compiler_fix: CMAKE_C_COMPILER fallback %r" % _cc)
                tc.variables["CMAKE_C_COMPILER"] = _cc
        if _cxx_conf and not os.path.isfile(_cxx_conf):
            self.output.info("compiler_fix: conf cpp %r missing" % _cxx_conf)
            _cxx = shutil.which("clang++") or shutil.which("c++") or ""
            if _cxx:
                self.output.info("compiler_fix: CMAKE_CXX_COMPILER fallback %r" % _cxx)
                tc.variables["CMAKE_CXX_COMPILER"] = _cxx
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # SoPlex options: keep GMP (rational) and ZLIB (gz) support
        tc.variables["GMP"] = "ON"
        tc.variables["ZLIB"] = "ON"
        # Sanitizers only apply in Debug builds; keep them off for determinism
        tc.variables["SANITIZE_UNDEFINED"] = "OFF"
        # Optional exact-arithmetic / presolving enhancements need Boost,
        # MPFR and PaPILO on top of GMP; disable them to keep the dependency
        # closure identical to the validated soplex/3.1.1 adaptation
        # (gmp + zlib only). The soplex CLI binary still builds without them
        # (src/CMakeLists.txt links ${Boost_LIBRARIES}, empty when BOOST=OFF),
        # and the ctest settings stay at the deterministic 9 base groups.
        tc.variables["BOOST"] = "OFF"
        tc.variables["MPFR"] = "OFF"
        tc.variables["PAPILO"] = "OFF"
        tc.variables["QUADMATH"] = "OFF"
        tc.generate()

    def build(self):
        self._ensure_writable_tmp()
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_ctest()

    def _ensure_writable_tmp(self):
        # 真机 /tmp 只读（HMBS readonly_tmp）：cmake 编译器自检、ctest 等都会写
        # 临时文件。按 TMPDIR/TMP/TEMP -> $HOME/tmp -> build_folder/hmbs-tmp 顺序
        # 建目录加写探针，命中后导出 TMPDIR/TMP/TEMP/GOTMPDIR（libsedml 先例改编，
        # 仅替换临时根目录，不跳过任何测试）。
        candidates = [os.environ.get("TMPDIR"), os.environ.get("TMP"),
                      os.environ.get("TEMP")]
        home = os.environ.get("HOME")
        if home:
            candidates.append(os.path.join(home, "tmp"))
        candidates.append(os.path.join(self.build_folder, "hmbs-tmp"))
        for cand in candidates:
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                os.remove(probe)
            except OSError:
                continue
            for key in ("TMPDIR", "TMP", "TEMP", "GOTMPDIR"):
                os.environ[key] = cand
            self.output.info("HMBS writable tmpdir: %s" % cand)
            return cand
        return self.build_folder

    def _writable_tmp(self):
        return self._ensure_writable_tmp()

    def _run_upstream_ctest(self):
        # 上游回归测试：check/CMakeLists.txt 经 add_test 注册为 ctest 用例，
        # (37 MPS + 2 LP) x 9 组 settings = 351 个用例（BOOST/MPFR 关闭时固定 9 组），
        # 每个用例运行构建产物 bin/soplex 求解实例并以 "Validation : Success" 判定。
        # 真机 /tmp 只读（HMBS readonly_tmp）：仅把临时文件根目录指向 HMBS 注入的
        # 可写 TMPDIR（回退 build_folder/.tmp），不删除任何测试；-j1 串行避免竞态。
        # 解析兼容 CTest 汇总行 "100% tests passed, 0 tests failed out of 351"
        # （组合正则优先，兼容单复数与 ANSI 着色），汇总缺失时回退到逐用例计数，
        # 仍为 0 时用 ctest -N 补发现数；绝不伪造通过。
        tmp = self._writable_tmp()
        # ctest 执行目录：优先含 CTestTestfile.cmake 的目录，避免无测试目录空跑。
        ctest_dir = self.build_folder
        try:
            _cands = [self.build_folder,
                      os.path.join(self.build_folder, "build", "Release"),
                      os.path.join(self.build_folder, "build")]
            for _cand in _cands:
                if _cand and os.path.isfile(os.path.join(_cand, "CTestTestfile.cmake")):
                    ctest_dir = _cand
                    break
        except Exception:
            ctest_dir = self.build_folder
        log = os.path.join(self.build_folder, "hmbs_ctest.log")
        cmd = ("cd \"%s\" && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\""
               " ctest --output-on-failure -j1 > \"%s\" 2>&1"
               % (ctest_dir, tmp, tmp, tmp, log))
        rc = 0
        try:
            self.run(cmd, env="conanrun")
        except Exception:
            rc = 1
        out = ""
        try:
            with open(log, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        # 去 ANSI 着色与回车，保证汇总行可匹配（终端着色重定向进文件时常见）。
        clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", out).replace("\r", "")
        discovered, passed, failed = 0, 0, 0
        m = re.search(r"(\d+)%\s*tests?\s+passed,\s*(\d+)\s+tests?\s+failed\s+out\s+of\s+(\d+)", clean)
        if m:
            failed, discovered = int(m.group(2)), int(m.group(3))
            passed = discovered - failed
        else:
            m2 = re.search(r"(\d+)\s+tests?\s+failed\s+out\s+of\s+(\d+)", clean)
            if m2:
                failed, discovered = int(m2.group(1)), int(m2.group(2))
                passed = discovered - failed
            else:
                m3 = re.search(r"(\d+)\s+tests?\s+passed\s+out\s+of\s+(\d+)", clean)
                if m3:
                    passed, discovered = int(m3.group(1)), int(m3.group(2))
                    failed = discovered - passed
        if discovered == 0:
            # 回退：逐用例计数（兼容汇总行缺失或格式漂移）。
            try:
                _p = len(re.findall(r"Test\s+#\d+[^\n]*\bPassed\b", clean))
                _f = len(re.findall(r"Test\s+#\d+[^\n]*\b(?:Failed|Timeout)\b", clean))
                if _p + _f > 0:
                    passed, failed = _p, _f
                    discovered = _p + _f
            except Exception:
                pass
        if discovered == 0:
            # 最后回退：ctest -N 只读探测发现数（不执行用例，不伪造通过）。
            try:
                self.run("cd \"%s\" && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\""
                         " ctest -N > \"%s.n\" 2>&1" % (ctest_dir, tmp, tmp, tmp, log),
                         env="conanrun", ignore_errors=True)
                with open(log + ".n", "r", encoding="utf-8", errors="replace") as f:
                    _nout = f.read()
                _nout = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", _nout).replace("\r", "")
                _mn = re.search(r"Total\s+Tests:\s*(\d+)", _nout)
                if _mn and int(_mn.group(1)) > 0:
                    discovered = int(_mn.group(1))
            except Exception:
                pass
        tail = "\n".join(out.splitlines()[-8:]) if out else "(empty ctest log)"
        self.output.info("soplex upstream ctest tail:\n" + tail)
        self.output.info("soplex upstream ctest dir: %s" % ctest_dir)
        marker = {
            "status": "passed" if (rc == 0 and failed == 0 and discovered > 0) else "failed",
            "framework": "ctest",
            "command": "ctest --output-on-failure -j1",
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        self.output.info(line)
        print(line, flush=True)
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8") as f:
                json.dump(marker, f, ensure_ascii=False)
        except OSError:
            pass
        if rc != 0 or failed != 0 or discovered == 0:
            raise RuntimeError(
                "soplex upstream ctest failed (rc=%d discovered=%d passed=%d failed=%d); "
                "see hmbs_ctest.log" % (rc, discovered, passed, failed))

    def package(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.install()
        # 持久化上游测试证据，供 test_package 在缓存命中轮复发（ali/c10t 先例）。
        try:
            copy(self, "hmbs_upstream.json", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "soplex")
        self.cpp_info.set_property("cmake_target_name", "soplex::soplex")
        self.cpp_info.set_property("pkg_config_name", "soplex")
        self.cpp_info.libs = ["soplex"]
        # 公开头 soplex/rational.h 直接 #include <gmp.h>（GMP=ON），
        # soplex/io.h 经 gzread 依赖 <zlib.h>（ZLIB=ON）：静态库不捆绑这些
        # 头与符号，须经 requires 把 gmp/zlib 的 includedir/libs 透传给
        # 下游 soplex::soplex，否则 test_package 编译报 gmp.h 不存在。
        self.cpp_info.requires = ["gmp::gmp", "zlib::zlib"]
        # the CLI solver binary is installed to bin/
        self.cpp_info.bindirs = ["bin"]
