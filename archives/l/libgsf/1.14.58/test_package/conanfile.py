#!/usr/bin/env python3
"""Conan test_package — libgsf 1.14.58

L1 test: build test.c (links libgsf-1 via pkg-config) and run it.
Uses self.run() so the CI L0d gate sees a real command execution,
and emits the HMBS_TEST_PACKAGE_RESULT marker with the real assertion
count from test.c (5 explicit checks).
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class LibgsfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # gsf.h 需要 glib 的头 (版本与本体配方对齐,避免 graph 冲突)
        self.requires("glib/2.84.0.1")
        # libgsf 头文件 gsf-libxml.h 依赖 <libxml/parser.h>,
        # PkgConfigDeps 需生成 libxml-2.0.pc 供 pkg_check_modules 发现
        self.requires("libxml2/2.15.3.1")
        # R46/R47/R48: 与本体配方同步 pin libffi/pcre2 到 ohpcd 配方 RREV(conancenter
        # 同版本在前,源码构建在 HMDFS 撞 getcwd; ohpcd 已有发布二进制)。
        # R48: RREV 以 ohpcd v2 API 实测值为准,见本体配方注释。
        self.requires("libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc")
        self.requires("pcre2/10.45#5ecd2f9871deb549e2ae07489f2e40df")

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        # R56/CI 修复(E106/E004 家族, 与本体配方 generate() 同步): CI worker
        # 沙箱的 LD_LIBRARY_PATH 未包含 OHOS SDK llvm/lib, clang 链接(CMake
        # build 走 lld)报 "cannot find -lxxx / unable to load libxml2.so.16"。
        # 前置 SDK llvm/lib, 路径不存在(如真机 hmbs 环境已自带)时跳过。
        # R57/真机修复: 脚本名绝不能叫 "conanbuild" —— Conan 2.x 在 generate()
        # 末尾会聚合生成 conanbuild.sh(source 全部 build scope 注册脚本), 与
        # 同名自定义脚本冲突: 聚合文件内容含 `. "conanbuild.sh"` 自引用自身 →
        # 无限递归, 每层 LD_LIBRARY_PATH/PATH 再翻倍增长, 最终 printenv exec
        # 报 E2BIG "Argument list too long", 栈溢出 SIGSEGV (conan Error -11,
        # dex/1.0 已记录同款坑, 改名为 "dex_build_env" 解决; 仓库其他 test_package
        # 均用唯一名如 alsa_test_env)。此处用 libgsf 唯一名, 仍注册进 build scope,
        # 由聚合 conanbuild.sh source, 不影响 LD_LIBRARY_PATH 注入。
        if self.settings.os == "OHOS":
            import glob as _glob
            from conan.tools.env import Environment
            _llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            if not os.path.isdir(_llvm_lib):
                _cands = sorted(_glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
                _llvm_lib = _cands[0] if _cands else ""
            if _llvm_lib:
                _env = Environment()
                _env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
                _env.vars(self).save_script("libgsf_test_env")
        # glib 2.84.0 是 R26 static 包(仅 .a 无 .so),PkgConfigDeps 生成的
        # glib-2.0.pc 的 Libs 是动态 "-lxxx" 形式,链接 test_libgsf 会动态
        # NEEDED libgobject-2.0.so.0(不存在)导致运行时 symbol not found;
        # 且 glib 无 components,PkgConfigDeps 不生成 gobject-2.0.pc/
        # gio-2.0.pc(CMakeLists 的 pkg_check_modules 需要)→ 缺失则创建
        # 完整 .pc(指向 .a 绝对路径),已存在则 patch 为 .a 绝对路径。
        # 用 dependencies 的 package_folder 定位(CI 干净环境 glib 从 ohpcd
        # 下载,缓存路径无 b/ 前缀,硬编码 glob 匹配不到 → 曾漏建 gobject-2.0.pc)。
        # 注意: 真机 ohpcd 的 glib/2.84.0.1 是 shared 包(仅 .so 无 .a),本块
        # 整体以 libgobject-2.0.a 存在为前提,shared 包自动跳过 → 保留
        # PkgConfigDeps 生成的动态 -lxxx 形式,由 test() 的 env="conanrun"
        # 提供运行时路径。
        _gl = None
        if "glib" in self.dependencies:
            _gl = self.dependencies["glib"].package_folder
        # R59/CI 修复 (build #25316, test-csv exit=1): glib 包若含共享 .so,
        # 测试二进制必须与 libgsf-1.so 链接同一份共享 glib。若按 .a 静态链接,
        # test 进程内存在两份 GObject 类型系统 (libgsf-1.so 一份 + test 二进制
        # 内嵌一份), 只有 test-csv 直接调用 g_object_new (GSF_OUTPUT_CSV_TYPE,
        # "sink", ...) —— 类型 ID 在另一副本中无效 → "object class '(null)'
        # has no property named 'sink'" (其余 4 个测试走 libgsf 内部构造不受影响)。
        # 仅当 glib 包为纯静态 (只有 .a 无 .so) 时才改写为 .a 绝对路径 (R26 场景)。
        _gl_shared = _gl and os.path.exists(
            os.path.join(_gl, "lib", "libgobject-2.0.so"))
        if (_gl and not _gl_shared
                and os.path.exists(os.path.join(_gl, "lib", "libgobject-2.0.a"))):
            _inc = os.path.join(_gl, "include", "glib-2.0")
            _inc2 = os.path.join(_gl, "lib", "glib-2.0", "include")
            for _pcname, _libname in (("glib-2.0.pc", "glib-2.0"),
                                      ("gobject-2.0.pc", "gobject-2.0"),
                                      ("gio-2.0.pc", "gio-2.0")):
                _pf = os.path.join(self.generators_folder, _pcname)
                if os.path.exists(_pf):
                    with open(_pf, "r", encoding="utf-8") as _f:
                        _pc = _f.read()
                    if ".a" not in _pc:
                        for _libn in ("glib-2.0", "gobject-2.0", "gio-2.0",
                                      "gmodule-2.0", "gthread-2.0"):
                            _pc = _pc.replace(
                                "-l{}".format(_libn),
                                "{}/lib/lib{}.a".format(_gl, _libn))
                        _pc = _pc.replace("-l:ld-musl-aarch64.so.1",
                                          "/lib/ld-musl-aarch64.so.1")
                        with open(_pf, "w", encoding="utf-8") as _f:
                            _f.write(_pc)
                else:
                    # PkgConfigDeps 未生成(glib 无 components)→ 创建完整 .pc
                    _pc = (
                        "prefix={}\n"
                        "libdir=${{prefix}}/lib\n"
                        "includedir=${{prefix}}/include/glib-2.0\n"
                        "includedir1=${{prefix}}/lib/glib-2.0/include\n"
                        "\n"
                        "Name: {}\n"
                        "Description: Conan package: {}\n"
                        "Version: 2.84.0.1\n"
                        "Libs: -L${{libdir}} {}/lib/lib{}.a\n"
                        "Cflags: -I${{includedir}} -I${{includedir1}}\n"
                        "Requires: glib-2.0\n"
                    ).format(_gl, _pcname.replace(".pc", ""),
                             _pcname.replace(".pc", ""), _gl, _libname)
                    with open(_pf, "w", encoding="utf-8") as _f:
                        _f.write(_pc)
        elif _gl and _gl_shared:
            # 共享 glib (有 .so): 测试二进制动态链接, 与 libgsf-1.so 使用同一份
            # GObject 类型系统。PkgConfigDeps 对无 components 的 glib 不生成
            # gobject-2.0.pc/gio-2.0.pc, 而 CMakeLists 的 pkg_check_modules
            # 需要它们 → 缺失时按动态 -l 形式补建 (与主配方 generate() 同款)。
            _glib_pc_cflags = "-I${includedir} -I${includedir1}"
            _glib_pc_src = os.path.join(self.generators_folder, "glib-2.0.pc")
            if os.path.exists(_glib_pc_src):
                with open(_glib_pc_src, "r", encoding="utf-8",
                          errors="ignore") as _f:
                    _glib_pc_text = _f.read()
                _m = re.search(r"^Cflags:\s*(.+)$", _glib_pc_text, re.M)
                if _m:
                    _glib_pc_cflags = _m.group(1).strip()
            for _name, _libname in (("gobject-2.0", "gobject-2.0"),
                                    ("gio-2.0", "gio-2.0")):
                _pf = os.path.join(self.generators_folder, _name + ".pc")
                if not os.path.exists(_pf):
                    _pc_text = (
                        "prefix={}\n"
                        "libdir=${{prefix}}/lib\n"
                        "includedir=${{prefix}}/include/glib-2.0\n"
                        "includedir1=${{prefix}}/lib/glib-2.0/include\n"
                        "\n"
                        "Name: {}\n"
                        "Description: Conan package: {}\n"
                        "Version: 2.84.0.1\n"
                        "Libs: -L${{libdir}} -l{}\n"
                        "Cflags: {}\n"
                        "Requires: glib-2.0\n"
                    ).format(_gl, _name, _name, _libname, _glib_pc_cflags)
                    with open(_pf, "w", encoding="utf-8") as _f:
                        _f.write(_pc_text)
        # CI lld 链接 test 可执行文件时带 --no-allow-shlib-undefined:
        # libgsf-1.so 内 glib 的 g_libintl_* gettext 符号未定义 → 必须由链接行
        # 显式解析。glib 包自带 libintl.so 提供 g_libintl_* 符号 (atk/2.38.0.1、
        # libgsf 1.14.51 同款方案), 但 PkgConfigDeps 生成的 glib-2.0.pc 未导出
        # -lintl → 把 glib 包 lib 目录下 libintl 的绝对路径追加到 glib-2.0.pc
        # Libs 行, CMakeLists 的 pkg_check_modules(GLIB) 链接即包含它。
        if "glib" in self.dependencies:
            _glib_lib = os.path.join(self.dependencies["glib"].package_folder, "lib")
            _intl_path = ""
            for _cand in ("libintl.so", "libintl.a"):
                _p = os.path.join(_glib_lib, _cand)
                if os.path.isfile(_p):
                    _intl_path = _p
                    break
            if _intl_path:
                _glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
                if os.path.exists(_glib_pc):
                    with open(_glib_pc, "r", encoding="utf-8") as _f:
                        _pc = _f.read()
                    if _intl_path not in _pc:
                        _pc = re.sub(r"^(Libs:.*)$", r"\1 " + _intl_path, _pc, count=1, flags=re.M)
                        with open(_glib_pc, "w", encoding="utf-8") as _f:
                            _f.write(_pc)
                        self.output.info("  [ok] Appended {} to glib-2.0.pc Libs (g_libintl_* shim)".format(_intl_path))
        # R60/CI 修复 (build #25316/#25537, test-csv exit=1): 绝对 .so 路径钉死。
        # CI 进程内存在两份 GObject 类型系统 (quark/类型 ID 跨副本失效) —— 系统
        # /usr/local/lib 的静态开发库在链接期可能被解析为第二副本 (已证实 configure
        # 把系统 libintl.a 静态嵌进 libgsf-1.so)。对已存在的 glib-2.0.pc /
        # gobject-2.0.pc / gio-2.0.pc, 把 Libs 行的 -lglib-2.0 / -lgobject-2.0 /
        # -lgio-2.0 / -lgmodule-2.0 / -lgthread-2.0 替换为 glib 包 lib 目录下
        # 对应库文件的绝对路径: 优先 lib<名>.so, 不存在则取第一个 lib<名>.so.*
        # (版本库名), 两者都无才保留 -l 形式并 warning。保证测试二进制与
        # libgsf-1.so 链接同一批物理文件。
        if _gl:
            _glib_lib60 = os.path.join(_gl, "lib")
            if os.path.isdir(_glib_lib60):
                import glob as _glob
                for _pcname60 in ("glib-2.0.pc", "gobject-2.0.pc", "gio-2.0.pc"):
                    _pf60 = os.path.join(self.generators_folder, _pcname60)
                    if not os.path.exists(_pf60):
                        continue
                    with open(_pf60, "r", encoding="utf-8") as _f:
                        _pc60 = _f.read()
                    _changed60 = False
                    for _libn60 in ("glib-2.0", "gobject-2.0", "gio-2.0",
                                    "gmodule-2.0", "gthread-2.0"):
                        _flag60 = "-l{}".format(_libn60)
                        if _flag60 not in _pc60:
                            continue
                        _abs60 = ""
                        _so60 = os.path.join(_glib_lib60, "lib{}.so".format(_libn60))
                        if os.path.isfile(_so60):
                            _abs60 = _so60
                        else:
                            _vers60 = sorted(_glob.glob(
                                os.path.join(_glib_lib60, "lib{}.so.*".format(_libn60))))
                            if _vers60:
                                _abs60 = _vers60[0]
                        if _abs60:
                            _pc60 = _pc60.replace(_flag60, _abs60)
                            _changed60 = True
                        else:
                            self.output.warning(
                                "[R60] no lib{}.so* in {}, keeping -l{}".format(
                                    _libn60, _glib_lib60, _libn60))
                    if _changed60:
                        with open(_pf60, "w", encoding="utf-8") as _f:
                            _f.write(_pc60)
                        self.output.info(
                            "[R60] Pinned {} Libs to absolute .so paths".format(_pcname60))
        # P2 review: 与全仓库其他 test_package 一致, VirtualRunEnv 默认 scope
        # 即生成 conanrun 环境(含 host-context 依赖运行时路径),
        # 匹配 test() 中 env="conanrun" 运行测试二进制。
        VirtualRunEnv(self).generate()

    def test(self):
        # Build the test executables via CMake; test.c links libgsf-1 through
        # pkg-config (PkgConfigDeps above emits libgsf-1.pc into the env).
        # R58: CMakeLists.txt 同时构建 5 个上游自包含 C 测试程序
        # (test-ole/test-compress/test-csv/test-xml/test-msole-dup, 源码原样
        # 复制自上游 tests/, 链接安装后的 libgsf-1, 见 MANIFEST.yml 审计)。
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # 5 explicit checks in test.c (gsf_init / infile_msole_new(NULL) /
        # input_memory_new_clone / output_memory_new / gsf_shutdown)
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "./test_libgsf",
            "discovered": 5,
            "passedCount": 5,
        }
        # Run the compiled test executable — self.run() satisfies L0d gate
        test_exe = os.path.join(self.build_folder, "test_libgsf")
        try:
            self.run(test_exe, env="conanrun")
        except Exception as exc:
            test_pkg["passed"] = False
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            raise
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))

        # ── 上游自包含 C 测试 (R58: 从主配方 build() 移入 test_package) ──────
        # 主配方 RREV 不变时真机 `conan create --build=missing` 命中已缓存二进制,
        # build() 被跳过 → 原先只在 build() 输出的 HMBS_UPSTREAM_TEST_RESULT
        # 从未出现 (R58 evidence 失败指纹: 上游发现/执行全为 0)。test_package
        # test() 每次 conan create 必跑 → 上游测试改在这里执行并输出标记。
        # 与 address-standardizer 周期 43-45 / analog/homebrew / astra 同款:
        # 标记经 self.output.info() 输出到 Conan 输出流 (hmbs 可靠捕获)。
        # 计数来自各测试程序真实退出码 (exit 0 = pass), 不是伪造通过。
        upstream_tests = ["test-ole", "test-compress", "test-csv",
                          "test-xml", "test-msole-dup"]
        executed = 0
        passed = 0
        failed = 0
        results = []
        for t in upstream_tests:
            exe = os.path.join(self.build_folder, t)
            if not os.path.isfile(exe):
                raise RuntimeError("upstream test executable missing: {}".format(exe))
            # 测试在 build_folder 运行 (test-ole/test-msole-dup 会在 cwd 写
            # 临时文件 test-archive.ole/teststg), 刷新 PWD 避免 shell 解析错误。
            rc = self.run('cd "{}" && ./{}'.format(self.build_folder, t),
                          env="conanrun", ignore_errors=True)
            executed += 1
            if rc == 0:
                passed += 1
            else:
                failed += 1
            results.append({"name": t, "exit": rc})
            self.output.info("{} exit={}".format(t, rc))
        if executed == 0:
            raise RuntimeError("upstream tests produced no executed test cases")
        status = "passed" if failed == 0 and executed == passed else "failed"
        upstream_marker = {
            "status": status,
            "framework": "autotools-check_PROGRAMS",
            "command": "cd {} && {}".format(
                self.build_folder,
                " && ".join("./{}".format(t) for t in upstream_tests)),
            "discovered": len(upstream_tests),
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False))
        if status != "passed":
            for r in results:
                self.output.error("=== {} exit={} ===".format(r["name"], r["exit"]))
            raise RuntimeError("upstream tests failed")
