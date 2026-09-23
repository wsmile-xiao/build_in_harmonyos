#!/usr/bin/env python3
"""Conan recipe — boost1.84-url 1.84.0 (Boost.URL component package).

Boost 1.84.0 单组件包（boost1.84-url）：从 boost 完整源码中裁剪编译
boost_url 静态库。b2 构建系统在 OHOS 不兼容（E068），沿用 archives/b/boost/1.84.0
元包配方验证过的"手动 clang++ 裁剪编译"方法论：直接编译 libs/url/src 下全部
66 个源文件（与上游 Jamfile 的 glob-tree-ex 定义一致）。

上游测试（libs/url/test/，92 个 .cpp）在 build() 中全量真实编译运行，
绕过 b2：
- test/unit/（84 个 .cpp）：Boost.URL 自带 test_suite 框架
  （extra/test_main.cpp + test_suite.hpp，不依赖 boost.test）。其中
  70 个 SOURCES 型 + doc_3_urls/doc_grammar/example/router 3 个额外 run
  规则为可执行测试（共 73 个）；其余 10 个为自包含头测试
  （error_types/encoding_opts/grammar/host_type/ignore_case/optional/
  string_view/urls/variant/rfc-query_rule，上游设计即仅验证头文件可自包含
  编译，无 main 无断言——按编译验证纳入）。
- test/extra/test_suite.cpp（1 个）：run 规则注册的自测（0 断言空转）。
- test/limits/limits.cpp（1 个）：BOOST_URL_MAX_SIZE=16 限制编译验证。
- test/fuzz/（5 个 .cpp）：LLVMFuzzer 驱动入口，用 standalone 驱动
  （嵌入式固定语料回放 LLVMFuzzerTestOneInput）验证非崩溃语义。
- test/cmake_test/main.cpp（1 个）：sizeof(url) 非零断言，编译运行。
snippets.cpp 引用 boost::filesystem::path 符号（Jamfile 声明
<library>/boost/filesystem//boost_filesystem），故同步从源码树裁剪编译
libboost_filesystem.a 供其链接（filesystem 源码 atomic_ref 需 C++20 而
OHOS libc++ 15 缺失，用 BOOST_FILESYSTEM_SINGLE_THREADED 降级路径绕过）。
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostUrlConan(ConanFile):
    name = "boost1.84-url"
    version = "1.84.0"
    description = "Boost.URL 1.84.0 组件包（RFC 3986 URL 解析库，鸿蒙 PC 适配，手动裁剪编译 boost_url 静态库）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    # b2 在 OHOS 不可用（E068），手动 clang++ 裁剪编译产出静态库，
    # 产物仅 libboost_url.a 与 boost/ 头文件子集。
    # （libboost_filesystem.a 仅为上游测试 snippets.cpp 链接所需，不进包。）

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Boost.URL 源码仅依赖 boost 头文件（header-only core），无外部依赖。
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def _compile_lib(self, lib_name, src_files, cxx, ar, cxxflags,
                     extra_defines=""):
        """Compile source files and archive into a static library.

        obj 命名用「相对于 boost_root 的路径转下划线」保持唯一：
        url 组件的 src/ 与 src/grammar/ 下存在同名 error.cpp / error.cpp，
        仅用 basename 会让两个 error.o 在 ar 归档时互相覆盖
        （实测丢失 urls::detail::error_cat 符号导致链接失败）。
        """
        objects = []
        obj_dir = os.path.join(self.build_folder, f"obj_{lib_name}")
        os.makedirs(obj_dir, exist_ok=True)
        for src in src_files:
            rel = os.path.relpath(src, self.source_folder)
            obj_name = rel.replace("/", "_").replace(".cpp", ".o")
            obj_path = os.path.join(obj_dir, obj_name)
            self.run(f"{cxx} {cxxflags} {extra_defines} -c {src} -o {obj_path}")
            objects.append(obj_path)
        lib_path = os.path.join(self.build_folder, f"libboost_{lib_name}.a")
        self.run(f"{ar} rcs {lib_path} {' '.join(objects)}")
        return lib_path

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")

        boost_root = self.source_folder
        if self.settings.build_type == "Debug":
            opt_flags = ["-O0", "-g"]
        else:
            opt_flags = ["-O2", "-DNDEBUG"]
        cxxflags = " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            *opt_flags,
            "-fPIC",
            f"-I{boost_root}",
            "-DBOOST_ALL_NO_LIB",
            # R8: 用特性检测宏而非平台宏，补丁消费该宏跳过
            # pthread_setcancelstate（OHOS musl 无此符号）
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ])

        # URL：上游 Jamfile 用 glob-tree-ex 收集 src/ 全部 *.cpp（66 个文件）
        url_src = sorted(glob.glob(
            os.path.join(boost_root, "libs", "url", "src", "**", "*.cpp"),
            recursive=True))
        self._compile_lib("url", url_src, cxx, ar, cxxflags)

        # Filesystem：仅为上游测试 snippets.cpp 链接所需（Jamfile 声明
        # <library>/boost/filesystem//boost_filesystem）。不进包产物。
        # OHOS libc++ 15 无 std::atomic_ref（C++20），filesystem 1.84 的
        # atomic_tools.hpp 走 atomic_ref 路径编译失败；上游提供
        # BOOST_FILESYSTEM_SINGLE_THREADED 守卫的单线程降级路径（功能一致，
        # 仅全局 locale 改用非原子访问），测试场景下无并发访问。
        fs_src = sorted(glob.glob(
            os.path.join(boost_root, "libs", "filesystem", "src", "*.cpp")))
        self._compile_lib("filesystem", fs_src, cxx, ar, cxxflags,
                          extra_defines="-DBOOST_FILESYSTEM_SOURCE "
                                        "-DBOOST_FILESYSTEM_STATIC_LINK "
                                        "-DBOOST_FILESYSTEM_SINGLE_THREADED")

        self._run_upstream_tests(boost_root, cxx, cxxflags)

    def _run_upstream_tests(self, boost_root, cxx, cxxflags):
        """全量编译并运行 Boost.URL 上游测试（92 个 .cpp），绕过 b2。

        分类执行：
        1) run 类（73+1+1=75 个可执行）：unit 全部 TEST_SUITE 测试 +
           extra/test_suite.cpp + limits/limits.cpp——框架来自
           libs/url/extra/（test_main.cpp + test_suite.hpp，不依赖
           boost.test），以进程退出码 0 判定通过。
        2) 自包含头测试（10 个）：上游设计即无 main 无断言（仅
           #include 单个头文件验证自包含），按编译验证（-fsyntax-only）
           纳入。
        3) fuzz（5 个）：LLVMFuzzerTestOneInput 入口，用 standalone
           驱动以固定语料回放验证非崩溃语义（不依赖 libFuzzer 运行时）。
        4) cmake_test（1 个）：sizeof(url) 断言，编译运行。
        报告写入 build_folder/upstream-tests-report.txt。

        测试可执行文件用 -static-libstdc++ 链接：conan buildenv 的
        LD_LIBRARY_PATH 前置了 llvm/lib（不含 libc++_shared.so，它在
        aarch64-linux-ohos/c++ 子目录），动态链接的测试二进制会因
        加载器找不到 libc++_shared.so 返回 rc=127。静态打入 libc++
        后测试仅依赖 libc.so，可在干净环境直接运行。
        """
        import subprocess
        lib_dir = self.build_folder
        extra_dir = os.path.join(boost_root, "libs", "url", "extra")
        unit_dir = os.path.join(boost_root, "libs", "url", "test", "unit")
        example_router_dir = os.path.join(boost_root, "libs", "url", "example", "router")
        test_router_dir = os.path.join(unit_dir, "example", "router")
        fuzz_dir = os.path.join(boost_root, "libs", "url", "test", "fuzz")
        link_flags = f"-L{lib_dir} -lboost_url -lboost_filesystem"
        test_flags = (cxxflags + f" -I{extra_dir} -I{unit_dir} "
                      f"-I{example_router_dir} -I{test_router_dir} "
                      "-static-libstdc++")

        # (测试标识, 源文件列表相对 unit_dir 的路径)
        suite_tests = {
            "authority_view": ["authority_view.cpp"],
            "error": ["error.cpp"],
            "encode": ["encode.cpp"],
            "decode_view": ["decode_view.cpp"],
            "format": ["format.cpp"],
            "ipv4_address": ["ipv4_address.cpp"],
            "ipv6_address": ["ipv6_address.cpp"],
            "param": ["param.cpp"],
            "params_base": ["params_base.cpp"],
            "params_encoded_view": ["params_encoded_view.cpp"],
            "params_view": ["params_view.cpp"],
            "params_encoded_base": ["params_encoded_base.cpp"],
            "params_encoded_ref": ["params_encoded_ref.cpp"],
            "params_ref": ["params_ref.cpp"],
            "parse": ["parse.cpp"],
            "parse_path": ["parse_path.cpp"],
            "parse_query": ["parse_query.cpp"],
            "pct_string_view": ["pct_string_view.cpp"],
            "scheme": ["scheme.cpp"],
            "segments_base": ["segments_base.cpp"],
            "segments_encoded_base": ["segments_encoded_base.cpp"],
            "segments_encoded_ref": ["segments_encoded_ref.cpp"],
            "segments_encoded_view": ["segments_encoded_view.cpp"],
            "segments_ref": ["segments_ref.cpp"],
            "segments_view": ["segments_view.cpp"],
            "snippets": ["snippets.cpp"],
            "static_url": ["static_url.cpp"],
            "url": ["url.cpp"],
            "url_base": ["url_base.cpp"],
            "url_view": ["url_view.cpp"],
            "url_view_base": ["url_view_base.cpp"],
            "natvis": ["natvis.cpp"],
            "grammar/alnum_chars": ["grammar/alnum_chars.cpp"],
            "grammar/alpha_chars": ["grammar/alpha_chars.cpp"],
            "grammar/charset": ["grammar/charset.cpp"],
            "grammar/ci_string": ["grammar/ci_string.cpp"],
            "grammar/dec_octet_rule": ["grammar/dec_octet_rule.cpp"],
            "grammar/delim_rule": ["grammar/delim_rule.cpp"],
            "grammar/digit_chars": ["grammar/digit_chars.cpp"],
            "grammar/grammar_error": ["grammar/grammar_error.cpp"],
            "grammar/grammar_parse": ["grammar/grammar_parse.cpp"],
            "grammar/hexdig_chars": ["grammar/hexdig_chars.cpp"],
            "grammar/literal_rule": ["grammar/literal_rule.cpp"],
            "grammar/lut_chars": ["grammar/lut_chars.cpp"],
            "grammar/not_empty_rule": ["grammar/not_empty_rule.cpp"],
            "grammar/optional_rule": ["grammar/optional_rule.cpp"],
            "grammar/range_rule": ["grammar/range_rule.cpp"],
            "grammar/recycled": ["grammar/recycled.cpp"],
            "grammar/string_token": ["grammar/string_token.cpp"],
            "grammar/string_view_base": ["grammar/string_view_base.cpp"],
            "grammar/token_rule": ["grammar/token_rule.cpp"],
            "grammar/tuple_rule": ["grammar/tuple_rule.cpp"],
            "grammar/type_traits": ["grammar/type_traits.cpp"],
            "grammar/unsigned_rule": ["grammar/unsigned_rule.cpp"],
            "grammar/variant_rule": ["grammar/variant_rule.cpp"],
            "grammar/vchars": ["grammar/vchars.cpp"],
            "rfc/absolute_uri_rule": ["rfc/absolute_uri_rule.cpp"],
            "rfc/authority_rule": ["rfc/authority_rule.cpp"],
            "rfc/gen_delim_chars": ["rfc/gen_delim_chars.cpp"],
            "rfc/ipv4_address_rule": ["rfc/ipv4_address_rule.cpp"],
            "rfc/ipv6_address_rule": ["rfc/ipv6_address_rule.cpp"],
            "rfc/origin_form_rule": ["rfc/origin_form_rule.cpp"],
            "rfc/pchars": ["rfc/pchars.cpp"],
            "rfc/pct_encoded_rule": ["rfc/pct_encoded_rule.cpp"],
            "rfc/relative_ref_rule": ["rfc/relative_ref_rule.cpp"],
            "rfc/reserved_chars": ["rfc/reserved_chars.cpp"],
            "rfc/sub_delim_chars": ["rfc/sub_delim_chars.cpp"],
            "rfc/unreserved_chars": ["rfc/unreserved_chars.cpp"],
            "rfc/uri_rule": ["rfc/uri_rule.cpp"],
            "rfc/uri_reference_rule": ["rfc/uri_reference_rule.cpp"],
            "compat/ada": ["compat/ada.cpp"],
            "doc_3_urls": ["doc_3_urls.cpp"],
            "doc_grammar": ["doc_grammar.cpp"],
            "example/router/router": [
                "example/router/router.cpp",
                "../../example/router/impl/matches.cpp",
                "../../example/router/detail/impl/router.cpp",
            ],
        }
        header_only_tests = [
            "error_types", "encoding_opts", "grammar", "host_type",
            "ignore_case", "optional", "string_view", "urls", "variant",
            "rfc/query_rule",
        ]
        fuzz_tests = [
            "uri", "absolute_uri", "origin_form", "relative_ref",
            "uri_reference",
        ]

        fuzz_driver = os.path.join(self.build_folder, "fuzz_driver.cpp")
        with open(fuzz_driver, "w", encoding="utf-8") as fh:
            fh.write(
                "// Standalone driver: replays LLVMFuzzerTestOneInput over a\n"
                "// fixed corpus (semantics check without libFuzzer runtime).\n"
                "#include <cstdint>\n"
                "#include <cstdio>\n"
                "#include <string>\n"
                "#include <vector>\n"
                "extern \"C\" int LLVMFuzzerTestOneInput(const uint8_t*, size_t);\n"
                "int main() {\n"
                "    std::vector<std::string> corpus = {\n"
                "        \"\", \"http://example.com/path?q=1#f\", \"/relative\",\n"
                "        \"//host/p\",\n"
                "        \"https://user:pass@host:8080/a/b/c?x=y&z=w#frag\",\n"
                "        std::string(\"a\\0b\", 3), std::string(256, 'x'),\n"
                "        std::string(64, '\\xff')\n"
                "    };\n"
                "    for (auto& s : corpus)\n"
                "        if (LLVMFuzzerTestOneInput(\n"
                "                (const uint8_t*)s.data(), s.size()) != 0)\n"
                "            return 1;\n"
                "    printf(\"fuzz replay: %zu inputs OK\\n\", corpus.size());\n"
                "    return 0;\n"
                "}\n")

        test_main = os.path.join(extra_dir, "test_main.cpp")
        report_lines = []
        passed, failed = 0, 0

        def record(kind, name, ok, detail=""):
            nonlocal passed, failed
            report_lines.append(
                f"{'PASS' if ok else 'FAIL'} [{kind}] {name} {detail}".rstrip())
            if ok:
                passed += 1
            else:
                failed += 1

        # 1) run-executable tests
        for name, srcs in sorted(suite_tests.items()):
            src_paths = [os.path.join(unit_dir, s) for s in srcs]
            exe = os.path.join(lib_dir, "t_" + name.replace("/", "_"))
            cmd = (f"{cxx} {test_flags} {' '.join(src_paths)} {test_main} "
                   f"{link_flags} -o {exe}")
            proc = subprocess.run(cmd, shell=True, cwd=lib_dir,
                                  capture_output=True, text=True, timeout=1800)
            if proc.returncode != 0:
                tail = proc.stderr.strip().splitlines()[-1] if proc.stderr else ""
                record("run", name, False, f"COMPILE_FAIL: {tail}")
                continue
            run = subprocess.run([exe], capture_output=True, text=True,
                                 timeout=600)
            total_asserts = 0
            for line in (run.stdout or "").splitlines():
                if "total." in line:
                    try:
                        total_asserts = int(line.strip().split(",")[-1]
                                            .split()[0])
                    except (ValueError, IndexError):
                        pass
            record("run", name, run.returncode == 0,
                   f"(asserts={total_asserts}) rc={run.returncode}")

        # extra/test_suite.cpp
        exe = os.path.join(lib_dir, "t_extra_test_suite")
        cmd = (f"{cxx} {test_flags} "
               f"{os.path.join(boost_root, 'libs', 'url', 'test', 'extra', 'test_suite.cpp')} "
               f"{test_main} {link_flags} -o {exe}")
        proc = subprocess.run(cmd, shell=True, cwd=lib_dir,
                              capture_output=True, text=True, timeout=1800)
        if proc.returncode != 0:
            tail = proc.stderr.strip().splitlines()[-1] if proc.stderr else ""
            record("run", "extra/test_suite", False, f"COMPILE_FAIL: {tail}")
        else:
            run = subprocess.run([exe], capture_output=True, text=True,
                                 timeout=600)
            record("run", "extra/test_suite", run.returncode == 0,
                   f"rc={run.returncode}")

        # limits/limits.cpp
        exe = os.path.join(lib_dir, "t_limits")
        limits_flags = (test_flags
                        + " -DBOOST_URL_MAX_SIZE=16 -DBOOST_URL_NO_LIB "
                          "-DBOOST_URL_STATIC_LINK")
        cmd = (f"{cxx} {limits_flags} "
               f"{os.path.join(boost_root, 'libs', 'url', 'test', 'limits', 'limits.cpp')} "
               f"{test_main} "
               f"{os.path.join(boost_root, 'libs', 'url', 'src', 'url.cpp')} "
               f"{os.path.join(boost_root, 'libs', 'url', 'src', 'parse.cpp')} "
               f"{link_flags} -o {exe}")
        proc = subprocess.run(cmd, shell=True, cwd=lib_dir,
                              capture_output=True, text=True, timeout=1800)
        if proc.returncode != 0:
            tail = proc.stderr.strip().splitlines()[-1] if proc.stderr else ""
            record("run", "limits/limits", False, f"COMPILE_FAIL: {tail}")
        else:
            run = subprocess.run([exe], capture_output=True, text=True,
                                 timeout=600)
            record("run", "limits/limits", run.returncode == 0,
                   f"rc={run.returncode}")

        # 2) header-only tests: compile check
        for name in sorted(header_only_tests):
            src = os.path.join(unit_dir, f"{name}.cpp")
            cmd = f"{cxx} {test_flags} -fsyntax-only {src}"
            proc = subprocess.run(cmd, shell=True, cwd=lib_dir,
                                  capture_output=True, text=True, timeout=600)
            record("header-only", name, proc.returncode == 0,
                   f"(compile-check) rc={proc.returncode}")

        # 3) fuzz replay
        for name in sorted(fuzz_tests):
            src = os.path.join(fuzz_dir, f"{name}.cpp")
            exe = os.path.join(lib_dir, "t_fuzz_" + name)
            cmd = (f"{cxx} {test_flags} {src} {fuzz_driver} "
                   f"-L{lib_dir} -lboost_url -o {exe}")
            proc = subprocess.run(cmd, shell=True, cwd=lib_dir,
                                  capture_output=True, text=True, timeout=1800)
            if proc.returncode != 0:
                tail = proc.stderr.strip().splitlines()[-1] if proc.stderr else ""
                record("fuzz-replay", name, False, f"COMPILE_FAIL: {tail}")
                continue
            run = subprocess.run([exe], capture_output=True, text=True,
                                 timeout=600)
            record("fuzz-replay", name, run.returncode == 0,
                   f"(8-corpus replay) rc={run.returncode}")

        # 4) cmake_test
        exe = os.path.join(lib_dir, "t_cmake_test")
        cmd = (f"{cxx} {test_flags} "
               f"{os.path.join(boost_root, 'libs', 'url', 'test', 'cmake_test', 'main.cpp')} "
               f"-L{lib_dir} -lboost_url -o {exe}")
        proc = subprocess.run(cmd, shell=True, cwd=lib_dir,
                              capture_output=True, text=True, timeout=1800)
        if proc.returncode != 0:
            tail = proc.stderr.strip().splitlines()[-1] if proc.stderr else ""
            record("run", "cmake_test", False, f"COMPILE_FAIL: {tail}")
        else:
            run = subprocess.run([exe], capture_output=True, text=True,
                                 timeout=600)
            record("run", "cmake_test", run.returncode == 0,
                   f"rc={run.returncode}")

        report_lines.append(
            f"TOTAL {passed + failed}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(
            f"upstream-tests-report: {report_path} ({passed}/{passed + failed} passed)")
        for line in report_lines:
            self.output.info(f"[upstream-tests] {line}")
        if failed:
            raise Exception(
                f"upstream tests failed: {failed}/{passed + failed} (see {report_path})")

    def package(self):
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_url.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")

        self.cpp_info.components["boost_headers"].includedirs = ["include"]
        self.cpp_info.components["boost_headers"].defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.components["boost_headers"].set_property("cmake_target_name", "Boost::headers")

        self.cpp_info.components["boost_url"].includedirs = []
        self.cpp_info.components["boost_url"].libs = ["boost_url"]
        self.cpp_info.components["boost_url"].requires = ["boost_headers"]
        self.cpp_info.components["boost_url"].set_property("cmake_target_name", "Boost::url")
