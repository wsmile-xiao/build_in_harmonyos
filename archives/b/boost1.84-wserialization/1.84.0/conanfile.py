#!/usr/bin/env python3
"""Conan recipe — boost1.84-wserialization 1.84.0 (manual compilation).

Boost.Wserialization provides wide-character (wchar_t) archive support for
Boost.Serialization (text_wiarchive/text_woarchive, xml_wiarchive/xml_woarchive
and their polymorphic wrappers). Upstream builds it as libboost_wserialization
which links against libboost_serialization.

Boost b2 build system is incompatible with OHOS (E068), so — following the
boost/1.84.0 recipe in this repo — we manually compile the required sources
into static archives:
  * libboost_serialization.a  (35 core sources, SOURCES + std_wstreambuf set)
  * libboost_wserialization.a (11 wide-char sources, WSOURCES)

The wide-char sources require std::wstreambuf (musl provides it — verified by
the successful build of text_wiarchive.cpp etc.).
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostWserializationConan(ConanFile):
    name = "boost1.84-wserialization"
    version = "1.84.0"
    description = "Boost 1.84.0 Wserialization 组件（宽字符序列化 archive，静态编译 libboost_wserialization + libboost_serialization，鸿蒙 PC 适配）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    # Boost b2 build system is incompatible with OHOS, so we manually compile
    # the serialization/wserialization sources into static archives. See
    # notes.md for the rationale (mirrors the boost/1.84.0 recipe approach).

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def _compile_lib(self, lib_name, src_files, cxx, ar, cxxflags):
        """Compile source files and archive into a static library."""
        boost_root = self.source_folder
        src_dir = os.path.join(boost_root, "libs", "serialization", "src")
        objects = []
        obj_dir = os.path.join(self.build_folder, f"obj_{lib_name}")
        os.makedirs(obj_dir, exist_ok=True)
        for src in src_files:
            src_path = os.path.join(src_dir, f"{src}.cpp")
            obj_path = os.path.join(obj_dir, f"{src}.o")
            cmd = f"{cxx} {cxxflags} -c {src_path} -o {obj_path}"
            self.run(cmd)
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
        # Optimization flags driven by build_type (R8: no hardcoded build profile).
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
            "-DBOOST_SYSTEM_NO_DEPRECATED",
            # R8 compliance: skip pthread_setcancelstate (not available on OHOS
            # musl) via the feature-detection macro consumed by patches/0001
            # (identical to the boost/1.84.0 recipe in this repository).
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ])

        # ── Source sets from upstream libs/serialization/build/Jamfile.v2 ──
        # SOURCES (core, narrow) — 33 entries
        core_src = [
            "archive_exception", "basic_archive", "basic_iarchive",
            "basic_iserializer", "basic_oarchive", "basic_oserializer",
            "basic_pointer_iserializer", "basic_pointer_oserializer",
            "basic_serializer_map", "basic_text_iprimitive",
            "basic_text_oprimitive", "basic_xml_archive",
            "binary_iarchive", "binary_oarchive",
            "extended_type_info", "extended_type_info_typeid",
            "extended_type_info_no_rtti",
            "polymorphic_iarchive", "polymorphic_oarchive", "stl_port",
            "text_iarchive", "text_oarchive",
            "polymorphic_text_iarchive", "polymorphic_text_oarchive",
            "polymorphic_binary_iarchive", "polymorphic_binary_oarchive",
            "polymorphic_xml_iarchive", "polymorphic_xml_oarchive",
            "void_cast", "xml_grammar", "xml_iarchive",
            "xml_archive_exception", "codecvt_null",
        ]
        # SOURCES_HAS_STD_WSTREAMBUF — 2 entries (compiled when std::wstreambuf
        # exists; musl provides it, verified during adaptation)
        std_wstreambuf_src = ["xml_oarchive", "utf8_codecvt_facet"]
        # WSOURCES (wide-char, the libboost_wserialization payload) — 11 entries
        w_src = [
            "basic_text_wiprimitive", "basic_text_woprimitive",
            "text_wiarchive", "text_woarchive",
            "polymorphic_text_wiarchive", "polymorphic_text_woarchive",
            "xml_wgrammar", "xml_wiarchive", "xml_woarchive",
            "polymorphic_xml_wiarchive", "polymorphic_xml_woarchive",
        ]

        # libboost_serialization: core + std_wstreambuf set (35 objects)
        self._compile_lib("serialization", core_src + std_wstreambuf_src, cxx, ar, cxxflags)
        # libboost_wserialization: wide-char set (11 objects)
        self._compile_lib("wserialization", w_src, cxx, ar, cxxflags)

    def package(self):
        # Install headers: copy entire boost/ include directory
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

        # Install compiled static libraries
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")

        # Main "headers" component (always needed)
        self.cpp_info.components["boost_headers"].includedirs = ["include"]
        # R8 compliance: expose BOOST_SP_NO_PTHREAD_SETCANCELSTATE to all
        # consumers so the patched sp_thread_sleep.hpp skips the
        # pthread_setcancelstate path (not available on OHOS musl) without
        # relying on a platform macro (same as boost/1.84.0 recipe).
        self.cpp_info.components["boost_headers"].defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.components["boost_headers"].set_property("cmake_target_name", "Boost::headers")

        # Serialization (narrow-char core; wserialization depends on it)
        self.cpp_info.components["boost_serialization"].includedirs = []
        self.cpp_info.components["boost_serialization"].libs = ["boost_serialization"]
        self.cpp_info.components["boost_serialization"].requires = ["boost_headers"]
        self.cpp_info.components["boost_serialization"].set_property("cmake_target_name", "Boost::serialization")

        # Wserialization (wide-char archives — this package's namesake)
        self.cpp_info.components["boost_wserialization"].includedirs = []
        self.cpp_info.components["boost_wserialization"].libs = ["boost_wserialization"]
        self.cpp_info.components["boost_wserialization"].requires = ["boost_headers", "boost_serialization"]
        self.cpp_info.components["boost_wserialization"].set_property("cmake_target_name", "Boost::wserialization")
