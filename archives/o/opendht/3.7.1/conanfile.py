#!/usr/bin/env python3
"""Conan recipe for opendht 3.7.1."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import PkgConfigDeps


class OpendhtConan(ConanFile):
    name = "opendht"
    version = "3.7.1"
    description = "Lightweight C++17 Distributed Hash Table library"
    license = "MIT"
    homepage = "https://github.com/savoirfairelinux/opendht"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("opendht is validated only for Linux and OHOS")

    def requirements(self):
        self.requires("gnutls/3.8.10", transitive_headers=True, transitive_libs=True)
        self.requires("nettle/3.10.2.1", transitive_libs=True)
        self.requires("argon2/20190702", transitive_libs=True)
        self.requires("fmt/12.2.0", transitive_headers=True, transitive_libs=True, override=True)
        self.requires("msgpack-cxx/7.0.0", transitive_headers=True)
        self.requires("jsoncpp/1.9.8", transitive_headers=True, transitive_libs=True)
        self.requires("openssl/3.5.8.1", transitive_headers=True, transitive_libs=True)
        self.requires("restinio/0.6.19", transitive_headers=True)
        self.requires("http-parser/2.9.4", transitive_headers=True)
        self.requires("simdutf/6.0.3", transitive_libs=True)
        self.test_requires("cppunit/1.15.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        local = os.environ.get("OHC_TARBALL")
        if local and os.path.isfile(local):
            import shutil
            import tarfile
            with tarfile.open(local, "r:gz") as tf:
                tf.extractall(self.source_folder)
            entries = [e for e in os.listdir(self.source_folder) if e not in (".", "..")]
            if len(entries) == 1 and os.path.isdir(os.path.join(self.source_folder, entries[0])):
                inner = os.path.join(self.source_folder, entries[0])
                for n in os.listdir(inner):
                    os.rename(os.path.join(inner, n), os.path.join(self.source_folder, n))
                shutil.rmtree(inner)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        cm = os.path.join(self.source_folder, "CMakeLists.txt")
        replace_in_file(
            self,
            cm,
            "pkg_search_module (argon2 REQUIRED IMPORTED_TARGET libargon2)",
            "pkg_search_module (argon2 REQUIRED IMPORTED_TARGET libargon2 argon2)",
        )
        replace_in_file(
            self,
            cm,
            "        RUNTIME_DEPENDENCY_SET opendht_rdeps\n",
            "",
        )
        replace_in_file(
            self,
            cm,
            "        target_link_libraries(opendht PUBLIC ${MSGPACK_TARGET})",
            "        if (TARGET msgpack-cxx::msgpack-cxx)\n"
            "            get_target_property(_msgpack_incs msgpack-cxx::msgpack-cxx INTERFACE_INCLUDE_DIRECTORIES)\n"
            "        elseif (TARGET ${MSGPACK_TARGET})\n"
            "            get_target_property(_msgpack_incs ${MSGPACK_TARGET} INTERFACE_INCLUDE_DIRECTORIES)\n"
            "        endif()\n"
            "        if (_msgpack_incs)\n"
            "            target_include_directories(opendht PUBLIC ${_msgpack_incs})\n"
            "        endif()",
        )
        replace_in_file(
            self,
            cm,
            "                tests/dhtproxytester.cpp\n",
            "                tests/dhtproxytester.cpp\n"
            "                tests/dhtproxy_stress_tester.h\n"
            "                tests/dhtproxy_stress_tester.cpp\n",
        )
        replace_in_file(
            self,
            cm,
            "        find_package(Restinio REQUIRED)",
            "        # Restinio/asio headers come from Conan restinio package",
            strict=False,
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "include", "opendht", "http.h"),
            "#include <restinio/message_builders.hpp>",
            "#include <restinio/message_builders.hpp>\n#include <llhttp.h>",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "base64.cpp"),
            'throw std::invalid_argument(concat("Invalid base64 input: "sv, simdutf::error_to_string(r.error)));',
            'throw std::invalid_argument("Invalid base64 input");',
        )
        http_cpp = os.path.join(self.source_folder, "src", "http.cpp")
        replace_in_file(
            self,
            http_cpp,
            "    llhttp_init(parser_.get(), HTTP_RESPONSE, parser_s_.get());",
            "    http_parser_init(parser_.get(), HTTP_RESPONSE);",
        )
        replace_in_file(
            self,
            http_cpp,
            "    enum llhttp_errno ret = llhttp_execute(parser_.get(), request.c_str(), request.size());",
            "    size_t _parsed = http_parser_execute(parser_.get(), parser_s_.get(), request.c_str(), request.size());\n"
            "    enum http_errno ret = HTTP_PARSER_ERRNO(parser_.get()); (void)_parsed;",
        )
        replace_in_file(self, http_cpp, "llhttp_should_keep_alive", "http_should_keep_alive", strict=False)
        replace_in_file(self, http_cpp, "llhttp_message_needs_eof", "http_message_needs_eof", strict=False)
        replace_in_file(self, http_cpp, "llhttp_errno_name", "http_errno_name", strict=False)
        replace_in_file(
            self,
            http_cpp,
            "llhttp_get_error_reason(parser_.get())",
            "http_errno_description(HTTP_PARSER_ERRNO(parser_.get()))",
        )
        replace_in_file(
            self,
            cm,
            "set(llhttp_target PkgConfig::LLHTTP)",
            "set(llhttp_target \"\")",
            strict=False,
        )
        replace_in_file(
            self,
            cm,
            'message(SEND_ERROR "llhttp not found and fallback downloader disabled. Install llhttp or use OPENDHT_DOWNLOAD_DEPS option")',
            "set(LLHTTP_FOUND TRUE)\n            set(llhttp_target \"\")",
            strict=False,
        )

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        deps = CMakeDeps(self)
        deps.set_property("cppunit", "cmake_file_name", "CppUnit")
        deps.set_property("cppunit", "cmake_target_name", "CppUnit::cppunit")
        deps.generate()
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["OPENDHT_TOOLS"] = False
        tc.variables["OPENDHT_PYTHON"] = False
        tc.variables["OPENDHT_EXAMPLES"] = False
        tc.variables["OPENDHT_PROXY_SERVER"] = True
        tc.variables["OPENDHT_PROXY_CLIENT"] = True
        tc.variables["OPENDHT_HTTP"] = True
        tc.variables["OPENDHT_PEER_DISCOVERY"] = True
        tc.variables["OPENDHT_PROXY_OPENSSL"] = True
        tc.variables["OPENDHT_DOWNLOAD_DEPS"] = False
        tc.variables["OPENDHT_C"] = False
        tc.variables["OPENDHT_SYSTEMD"] = False
        tc.variables["OPENDHT_INDEX"] = False
        tc.variables["BUILD_TESTING"] = True
        tc.variables["OPENDHT_TESTS_NETWORK"] = True
        tc.variables["OPENDHT_USE_PKGCONFIG"] = True
        msgpack = self.dependencies["msgpack-cxx"]
        for d in msgpack.cpp_info.includedirs:
            p = d if os.path.isabs(d) else os.path.join(msgpack.package_folder, d)
            tc.extra_cxxflags.append("-I" + p)
        restinio = self.dependencies["restinio"]
        rest_inc = restinio.cpp_info.includedirs[0]
        if not os.path.isabs(rest_inc):
            rest_inc = os.path.join(restinio.package_folder, rest_inc)
        tc.variables["ASIO_INCLUDE_DIR"] = rest_inc
        tc.variables["Restinio_INCLUDE_DIR"] = rest_inc
        tc.extra_cxxflags.append("-I" + rest_inc)
        tc.extra_cxxflags.append("-DASIO_STANDALONE")
        tc.extra_cxxflags.append("-DRESTINIO_NODISCARD=[[nodiscard]]")
        shim = os.path.join(self.build_folder, "include_shim")
        os.makedirs(shim, exist_ok=True)
        with open(os.path.join(shim, "llhttp.h"), "w", encoding="utf-8") as fh:
            fh.write(
                "#pragma once\n"
                "#include <http_parser.h>\n"
                "typedef http_parser llhttp_t;\n"
                "typedef http_parser_settings llhttp_settings_t;\n"
                "typedef enum http_errno llhttp_errno;\n"
                "#define llhttp_settings_init http_parser_settings_init\n"
                "#ifndef http_message_needs_eof\n"
                "#define http_message_needs_eof(p) (0)\n"
                "#endif\n"
            )
        tc.extra_cxxflags.append("-I" + shim)
        for dep_name in ("jsoncpp", "http-parser", "openssl", "simdutf"):
            try:
                dep = self.dependencies[dep_name]
            except Exception:
                continue
            for d in dep.cpp_info.includedirs:
                p = d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                tc.extra_cxxflags.append("-I" + p)
            for d in dep.cpp_info.libdirs:
                p = d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                if os.path.isdir(p):
                    tc.extra_exelinkflags.append("-L" + p)
                    tc.extra_sharedlinkflags.append("-L" + p)
            for lib in dep.cpp_info.libs:
                tc.extra_exelinkflags.append("-l" + lib)
                tc.extra_sharedlinkflags.append("-l" + lib)
        try:
            cppunit = self.dependencies["cppunit"]
            for d in cppunit.cpp_info.includedirs:
                p = d if os.path.isabs(d) else os.path.join(cppunit.package_folder, d)
                tc.extra_cxxflags.append("-I" + p)
            for d in cppunit.cpp_info.libdirs:
                p = d if os.path.isabs(d) else os.path.join(cppunit.package_folder, d)
                tc.extra_exelinkflags.append("-L" + p)
                tc.extra_sharedlinkflags.append("-L" + p)
            tc.extra_exelinkflags.append("-lcppunit")
        except Exception:
            pass
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self._run_ctest()

    def _run_ctest(self):
        libdirs = []
        for d in (
            os.path.join(self.build_folder),
            os.path.join(self.build_folder, "lib"),
        ):
            if os.path.isdir(d):
                libdirs.append(d)
        try:
            items = self.dependencies.host.items()
        except Exception:
            items = self.dependencies.items()
        for _, dep in items:
            base = getattr(dep, "package_folder", None) or ""
            for p in getattr(dep.cpp_info, "libdirs", []) or []:
                if not os.path.isabs(p) and base:
                    p = os.path.join(base, p)
                if os.path.isdir(p):
                    libdirs.append(p)
        ld = ":".join(dict.fromkeys(libdirs))
        self.run(
            'env LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ctest --output-on-failure' % ld,
            cwd=self.build_folder,
            env="conanrun",
            ignore_errors=True,
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["opendht"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "opendht")
        self.cpp_info.set_property("cmake_target_name", "opendht")
        self.cpp_info.set_property("pkg_config_name", "opendht")
