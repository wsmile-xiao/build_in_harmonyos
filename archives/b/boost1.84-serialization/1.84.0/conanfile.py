#!/usr/bin/env python3
"""Conan recipe — boost1.84-serialization 1.84.0 (Boost.Serialization component package).

Boost 1.84.0 单组件包（boost1.84-serialization）：从 boost 完整源码裁剪编译
boost_serialization 静态库（窄字符部分；wide 字符的 boost_wserialization 是
独立组件包）。b2 在 OHOS 不兼容（E068），沿用 archives/b/boost/1.84.0 元包
验证过的手动 clang++ 裁剪编译方法论。

上游测试（libs/serialization/test/ 的 122 个 .cpp 测试源）在 build() 中真实
编译运行，绕过 b2（test_tools.hpp 自带 main + lightweight_test 框架，不依赖
boost.test 库）。纳入 91 个：78 个 run 类（含多编译单元 polymorphic 类，按
上游 b2 规则传 -DBOOST_ARCHIVE_TEST=polymorphic_text_archive.hpp）、4 个
compile-only 类、9 个 compile-fail 类（上游要求编译失败，实测编译失败=通过）。
容器类测试需链接测试夹具 A.cpp；test_tools.hpp 的 tmpnam 依赖
boost::filesystem，故为测试额外编译 boost_filesystem.a（仅测试用，不入
package 产物）。其余 31 个未纳入（dll 共享库类/多共享库类/需 SGI hash 或
slist 扩展/上游遗留未注册文件等），逐类理由见 PR 描述与 notes.md。
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostSerializationConan(ConanFile):
    name = "boost1.84-serialization"
    version = "1.84.0"
    description = "Boost.Serialization 1.84.0 组件包（窄字符序列化库，鸿蒙 PC 适配，手动裁剪编译 boost_serialization 静态库）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Boost.Serialization 核心无外部依赖（测试工具 tmpnam 用到的
        # boost::filesystem 仅在 build() 测试阶段本地编译，不入 package）。
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def _compile_lib(self, lib_name, src_files, cxx, ar, cxxflags, obj_dirname=None):
        """Compile source files and archive into a static library.

        obj 命名用「相对 boost_root 路径转下划线」保持唯一（见
        boost1.84-url 的 ar 同名覆盖教训）。
        """
        objects = []
        obj_dir = os.path.join(self.build_folder, obj_dirname or f"obj_{lib_name}")
        os.makedirs(obj_dir, exist_ok=True)
        for src in src_files:
            rel = os.path.relpath(src, self.source_folder)
            obj_name = rel.replace("/", "_").replace(".cpp", ".o")
            obj_path = os.path.join(obj_dir, obj_name)
            self.run(f"{cxx} {cxxflags} -c {src} -o {obj_path}")
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
        base_flags = " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            *opt_flags,
            "-fPIC",
            f"-I{boost_root}",
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ])

        ser_src_dir = os.path.join(boost_root, "libs", "serialization", "src")
        # 上游 Jamfile 的 boost_serialization 目标 = SOURCES + SOURCES_HAS_STD_WSTREAMBUF
        # （xml_oarchive/utf8_codecvt_facet 依赖 std::wstreambuf，musl 提供）
        ser_files = [
            "archive_exception", "basic_archive", "basic_iarchive",
            "basic_iserializer", "basic_oarchive", "basic_oserializer",
            "basic_pointer_iserializer", "basic_pointer_oserializer",
            "basic_serializer_map", "basic_text_iprimitive",
            "basic_text_oprimitive", "basic_xml_archive",
            "binary_iarchive", "binary_oarchive", "codecvt_null",
            "extended_type_info", "extended_type_info_no_rtti",
            "extended_type_info_typeid", "polymorphic_iarchive",
            "polymorphic_oarchive", "stl_port", "text_iarchive",
            "text_oarchive", "polymorphic_text_iarchive",
            "polymorphic_text_oarchive", "polymorphic_binary_iarchive",
            "polymorphic_binary_oarchive", "polymorphic_xml_iarchive",
            "polymorphic_xml_oarchive", "void_cast", "xml_grammar",
            "xml_iarchive", "xml_archive_exception",
            "xml_oarchive", "utf8_codecvt_facet",
        ]
        self._compile_lib("serialization",
                          [os.path.join(ser_src_dir, f + ".cpp") for f in ser_files],
                          cxx, ar, base_flags)

        self._run_upstream_tests(boost_root, cxx, base_flags)

    def _run_upstream_tests(self, boost_root, cxx, cxxflags):
        """编译并运行 Boost.Serialization 上游测试（绕过 b2）。

        覆盖 libs/serialization/test/ 122 个 .cpp 测试源中的 91 个：
        - RUN 类 78 个：test_tools.hpp 自带 main（lightweight_test 框架），
          编译+链接+运行，rc=0 判过；
        - COMPILE_ONLY 类 4 个：上游 b2 `[ compile ]` 规则只要求编译通过
          （无 main，不链接），-c 编译 rc=0 判过；
        - COMPILE_FAIL 类 9 个：上游 b2 `[ compile-fail ]` 规则要求编译
          必须失败，实测编译失败=通过。
        多编译单元测试（polymorphic 系列）按上游 test-bsl-run_polymorphic_files
        规则传 -DBOOST_ARCHIVE_TEST=polymorphic_text_archive.hpp。
        容器类测试需链接测试夹具 A.cpp；test_tools.hpp 的 tmpnam 用到
        boost::filesystem::unique_path，为测试编译 boost_filesystem.a。
        """
        import subprocess
        lib_dir = self.build_folder
        test_dir = os.path.join(boost_root, "libs", "serialization", "test")
        fs_src_dir = os.path.join(boost_root, "libs", "filesystem", "src")

        # 测试辅助库：boost_filesystem（tmpnam 依赖）
        fs_files = ["codecvt_error_category", "directory", "exception",
                    "operations", "path", "path_traits", "portability",
                    "unique_path", "utf8_codecvt_facet"]
        fs_flags = cxxflags + " -DBOOST_FILESYSTEM_NO_CXX20_CHAR8_T -DBOOST_FILESYSTEM_NO_CXX20_ATOMIC_REF -DBOOST_SYSTEM_NO_DEPRECATED"
        self._compile_lib("filesystem",
                          [os.path.join(fs_src_dir, f + ".cpp") for f in fs_files],
                          cxx, self.conf.get("tools.build:compiler_executables",
                                              default={}, check_type=dict).get("ar", "llvm-ar"),
                          fs_flags, obj_dirname="obj_fs_testonly")

        # ── RUN 类测试（78 个）────────────────────────────────────────
        # (测试名, 额外源[夹具/多TU源], polymorphic_define)
        # 额外源中 A.cpp 为测试夹具；polymorphic_*/test_polymorphic_* 为多
        # 编译单元测试的同套 TU 源（上游 Jamfile <source> 指定）。
        run_cases = [
            # ── 单 TU，text_archive（上游 test-bsl-run_files 默认归档）──
            ("test_array", ["A.cpp"], False),
            ("test_boost_array", ["A.cpp"], False),
            ("test_native_array", ["A.cpp"], False),
            ("test_binary", [], False),
            ("test_class_info_save", [], False),
            ("test_class_info_load", [], False),
            ("test_bitset", [], False),
            ("test_complex", [], False),
            ("test_contained_class", ["A.cpp"], False),
            ("test_cyclic_ptrs", ["A.cpp"], False),
            ("test_delete_pointer", [], False),
            ("test_deque", ["A.cpp"], False),
            ("test_derived", [], False),
            ("test_derived_class", ["A.cpp"], False),
            ("test_derived_class_ptr", ["A.cpp"], False),
            ("test_diamond", [], False),
            ("test_diamond_complex", [], False),
            ("test_forward_list", ["A.cpp"], False),
            ("test_forward_list_ptrs", ["A.cpp"], False),
            ("test_helper_support", [], False),
            ("test_interrupts", [], False),
            ("test_list", ["A.cpp"], False),
            ("test_list_ptrs", ["A.cpp"], False),
            ("test_map", ["A.cpp"], False),
            ("test_mi", [], False),
            ("test_multiple_ptrs", ["A.cpp"], False),
            ("test_multiple_inheritance", [], False),
            ("test_new_operator", ["A.cpp"], False),
            ("test_optional", [], False),
            ("test_non_intrusive", [], False),
            ("test_non_default_ctor", [], False),
            ("test_non_default_ctor2", [], False),
            ("test_null_ptr", [], False),
            ("test_nvp", ["A.cpp"], False),
            ("test_object", [], False),
            ("test_primitive", [], False),
            ("test_priority_queue", ["A.cpp"], False),
            ("test_queue", ["A.cpp"], False),
            ("test_recursion", ["A.cpp"], False),
            ("test_registered", [], False),
            ("test_set", ["A.cpp"], False),
            ("test_simple_class", ["A.cpp"], False),
            ("test_simple_class_ptr", ["A.cpp"], False),
            ("test_split", [], False),
            ("test_stack", ["A.cpp"], False),
            ("test_tracking", [], False),
            ("test_unregistered", [], False),
            ("test_unique_ptr", [], False),
            ("test_valarray", [], False),
            ("test_variant", ["A.cpp"], False),
            ("test_vector", ["A.cpp"], False),
            ("test_shared_ptr", [], False),
            ("test_shared_ptr_multi_base", [], False),
            ("test_shared_ptr_132", [], False),
            ("test_inclusion", [], False),
            ("test_inclusion2", [], False),
            ("test_private_ctor", [], False),
            ("test_reset_object_address", ["A.cpp"], False),
            ("test_void_cast", [], False),
            ("test_mult_archive_types", [], False),
            ("test_iterators", [], False),
            ("test_iterators_base64", [], False),
            ("test_smart_cast", [], False),
            ("test_codecvt_null", [], False),
            ("test_singleton", [], False),
            ("test_singleton_inherited", [], False),
            ("test_singleton_plain", [], False),
            ("test_static_warning", [], False),
            ("test_strong_typedef", [], False),
            ("test_traits_pass", [], False),
            ("test_private_base", [], False),
            ("test_private_base2", [], False),
            ("test_dll_simple", ["dll_a.cpp"], False),
            # ── 多编译单元 polymorphic 类（上游 test-bsl-run_polymorphic_files）──
            # b2 传 BOOST_ARCHIVE_TEST=polymorphic_text_archive.hpp（窄字符）
            ("test_polymorphic", ["test_polymorphic_A.cpp", "A.cpp"], True),
            ("test_polymorphic2", ["test_polymorphic2imp.cpp"], True),
            ("test_p_helper", [], True),
            ("test_no_rtti", ["polymorphic_base.cpp", "polymorphic_derived1.cpp", "polymorphic_derived2.cpp"], True),
            ("test_exported", ["polymorphic_base.cpp", "polymorphic_derived1.cpp", "polymorphic_derived2.cpp"], True),
        ]
        # ── COMPILE_ONLY 类（4 个）：上游 [ compile ] 规则，无 main，只编译 ──
        compile_only_cases = [
            "test_const_save_warn1", "test_const_save_warn2",
            "test_const_save_warn3", "test_const_pass",
        ]
        # ── COMPILE_FAIL 类（9 个）：上游 [ compile-fail ] 规则，编译必须失败 ──
        compile_fail_cases = [
            "test_not_serializable", "test_traits_fail",
            "test_const_load_fail1", "test_const_load_fail2", "test_const_load_fail3",
            "test_const_load_fail1_nvp", "test_const_load_fail2_nvp",
            "test_const_load_fail3_nvp", "test_check",
        ]

        fixture_dir = test_dir
        report_lines = []
        passed, failed = 0, 0

        def _record(ok, kind, name, rc, note=""):
            nonlocal passed, failed
            status = "PASS" if ok else "FAIL"
            line = f"{status} [{kind}] {name} rc={rc}"
            if note:
                line += f" :: {note}"
            report_lines.append(line)
            if ok:
                passed += 1
            else:
                failed += 1

        # RUN 类：编译 + 链接 + 运行
        for name, extra_srcs, poly in run_cases:
            src = os.path.join(test_dir, f"{name}.cpp")
            extras = " ".join(os.path.join(fixture_dir, s) for s in extra_srcs)
            exe = os.path.join(lib_dir, f"test_{name}")
            define = " -DBOOST_ARCHIVE_TEST=polymorphic_text_archive.hpp" if poly else ""
            test_flags = cxxflags + f" -I{test_dir} -static-libstdc++{define}"
            cmd = (f"{cxx} {test_flags} {src} {extras} "
                   f"-L{lib_dir} -lboost_serialization -lboost_filesystem -o {exe}")
            proc = subprocess.run(cmd, shell=True, cwd=lib_dir,
                                  capture_output=True, text=True, timeout=900)
            if proc.returncode != 0:
                err_lines = [l for l in proc.stderr.strip().splitlines() if l]
                head = " | ".join(err_lines[:3])
                _record(False, "RUN", name, proc.returncode, head[:300])
                continue
            run = subprocess.run([exe], capture_output=True, text=True,
                                 timeout=300)
            _record(run.returncode == 0, "RUN", name, run.returncode,
                    "" if run.returncode == 0 else (run.stderr or run.stdout)[:150])

        # COMPILE_ONLY 类：只编译不链接（上游 b2 [ compile ] 语义）
        for name in compile_only_cases:
            src = os.path.join(test_dir, f"{name}.cpp")
            obj = os.path.join(lib_dir, f"{name}.o")
            test_flags = cxxflags + f" -I{test_dir}"
            proc = subprocess.run(f"{cxx} {test_flags} -c {src} -o {obj}",
                                  shell=True, cwd=lib_dir,
                                  capture_output=True, text=True, timeout=900)
            _record(proc.returncode == 0, "COMPILE_ONLY", name, proc.returncode,
                    "" if proc.returncode == 0 else
                    " ".join(proc.stderr.strip().splitlines()[:3])[:300])

        # COMPILE_FAIL 类：编译必须失败（上游 b2 [ compile-fail ] 语义）
        for name in compile_fail_cases:
            src = os.path.join(test_dir, f"{name}.cpp")
            obj = os.path.join(lib_dir, f"{name}.fail.o")
            test_flags = cxxflags + f" -I{test_dir}"
            proc = subprocess.run(f"{cxx} {test_flags} -c {src} -o {obj}",
                                  shell=True, cwd=lib_dir,
                                  capture_output=True, text=True, timeout=900)
            expected_fail = proc.returncode != 0
            _record(expected_fail, "COMPILE_FAIL", name, proc.returncode,
                    "compile failed as expected" if expected_fail else
                    "UNEXPECTED compile success (should have failed)")

        report_lines.append(f"TOTAL {passed + failed}: {passed} passed / {failed} failed")
        report_lines.append(
            "SCOPE: 91/122 included (78 RUN + 4 COMPILE_ONLY + 9 COMPILE_FAIL); "
            "31 excluded (dll/multi-shared-lib class 10, hashed 2, slist 2, "
            "upstream legacy unregistered 13, misc 4) - see PR description")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(f"上游测试报告: {report_path} ({passed}/{passed + failed} 通过)")
        for line in report_lines:
            self.output.info(f"[upstream-tests] {line}")

    def package(self):
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_serialization.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")

        self.cpp_info.components["boost_headers"].includedirs = ["include"]
        self.cpp_info.components["boost_headers"].defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.components["boost_headers"].set_property("cmake_target_name", "Boost::headers")

        self.cpp_info.components["boost_serialization"].includedirs = []
        self.cpp_info.components["boost_serialization"].libs = ["boost_serialization"]
        self.cpp_info.components["boost_serialization"].requires = ["boost_headers"]
        self.cpp_info.components["boost_serialization"].set_property("cmake_target_name", "Boost::serialization")
