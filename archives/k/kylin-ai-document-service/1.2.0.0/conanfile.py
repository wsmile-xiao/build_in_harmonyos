#!/usr/bin/env python3
"""Conan recipe for kylin-ai-document-service 1.2.0.0 (CMake, shared library).

Upstream: https://gitee.com/openkylin/kylin-ai-document-service
Tag:      build/1.2.0.0-ok0.6 (commit ef12f7fae2cbc6a2f5d3c3626c96f35b5935a832)

The library is the gRPC client of the Kylin AI document chunking service:
src/client.cpp + src/stub_manager.cpp plus the protobuf/gRPC code generated
from the in-tree document.proto.  It also ships the Python service payload
and the systemd user unit as data (share/ and lib/systemd/user/).

Adaptation notes (HarmonyOS PC / aarch64, native build):

- grpc and protobuf export ``cmake_find_mode=none``, so CMakeDeps generates
  no config files for them; ``gRPC_DIR`` / ``Protobuf_DIR`` / ``absl_DIR`` /
  ``utf8_range_DIR`` are pinned at the configs inside the registry packages
  (the same wiring the grpc recipe and its consumers use).
- protoc and grpc_cpp_plugin are pinned explicitly: the OHOS toolchain sets
  CMAKE_SYSTEM_NAME=HarmonyOS, so CMake considers this a cross build and
  would otherwise search a PATH that does not carry the registry bins.
- Upstream finds gRPC/systemd through pkg-config.  The registry grpc.pc
  ``Requires:`` a long list of absl_* modules that are not installed, and the
  registry systemd package ships an empty ``lib/pkgconfig/`` (no
  libsystemd.pc), so both are switched to the CMake config packages
  (patch 0001).
- The in-tree document.proto is the code-generation source: the registry
  kylin-ai-proto copy is older (no max_doc_chars_count/callback_data/Status)
  while src/client.cpp calls ``add_max_doc_chars_count()``, and both copies
  would emit the same ``document.pb.*`` output names.
- ``PROTO_*``/install() paths are absolute ``/usr/...`` upstream; they are
  relocated to GNUInstallDirs so ``conan package()`` stays inside the package
  folder (patch 0001).
- R51: the upstream test program (test/test.cpp) is built and executed from
  ``build()``; see test_package/MANIFEST.yml for the census and its limits.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class KylinAiDocumentServiceConan(ConanFile):
    name = "kylin-ai-document-service"
    version = "1.2.0.0"
    description = ("Kylin AI document service client library "
                   "(gRPC chunking client)")
    license = "GPL-3.0-or-later"
    homepage = "https://gitee.com/openkylin/kylin-ai-document-service"
    url = "https://gitee.com/openkylin/kylin-ai-document-service"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # grpc/1.84.0 pins protobuf/33.6; requiring 33.6.1 makes the graph
        # fail with "Version conflict ... originates from grpc/1.84.0".
        self.requires("grpc/1.84.0")
        self.requires("protobuf/33.6")
        # Provides the KylinAiProto CMake package (KylinAiProto::KylinAiProto)
        # together with KylinAiProtoFunctions.cmake / KylinAiProtoGenerate.cmake,
        # which this project's CMakeLists calls for proto code generation.
        # kylin-ai-proto is not published in the registry, so this is the only
        # published provider of find_package(KylinAiProto).
        self.requires("libkylin-ai-system-private/1.2.0.0")
        # src/client.cpp includes <systemd/sd-bus.h> (sd-bus client library).
        self.requires("systemd/261")
        # src/client.cpp includes <nlohmann/json.hpp>.
        self.requires("nlohmann_json/3.12.0")
        # zlib arrives transitively (protobuf/grpc).  The published
        # zlib/1.3.1 archive is static-only with non-PIC objects (the platform
        # provides a system libz.so, so R26 forbids shipping another one), and
        # on aarch64 those objects cannot be absorbed into a shared library:
        #   ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used
        #   against symbol 'z_errmsg'; recompile with -fPIC
        # Overriding to the PIC build (zlib/1.3.1.1) would change this package's
        # dependency graph and also invalidate the published systemd/261 binary
        # (it pins zlib/1.3.1), forcing a dependency rebuild — contrary to R36.
        # Instead the non-PIC archive is linked with --exclude-libs,ALL (see
        # generate()), which makes its symbols non-preemptible and lets lld
        # resolve the relocations internally.  Same technique as harfbuzz.
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # The Gitee archive endpoint answers a curl user-agent; without it the
        # downloader receives an HTML page instead of the tarball.
        get(self, **self.conan_data["sources"],
            headers={"User-Agent": "curl/8.0"}, strip_root=True)

    def generate(self):
        VirtualRunEnv(self).generate()
        CMakeDeps(self).generate()

        # aarch64 GNUInstallDirs may select lib64/, while Conan's cpp_info and
        # CMakeDeps look under lib/.
        protobuf = self.dependencies["protobuf"]
        grpc = self.dependencies["grpc"]
        abseil = self.dependencies["abseil-cpp"]
        openssl = self.dependencies["openssl"]
        kylin_ai = self.dependencies["libkylin-ai-system-private"]

        tc = CMakeToolchain(self)
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # find_package(KylinAiProto): the provider publishes the KylinAiProto
        # CMake package (config + KylinAiProtoFunctions.cmake /
        # KylinAiProtoGenerate.cmake, which this project's CMakeLists calls to
        # generate the gRPC/protobuf sources).  It is a *component* of that
        # package, and CMakeDeps only emits the top-level
        # <package>-config.cmake, so point find_package at the config the
        # provider installs for this component.
        tc.variables["KylinAiProto_DIR"] = os.path.join(
            kylin_ai.package_folder, "share", "KylinAiProto", "cmake"
        ).replace("\\", "/")
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")
        tc.variables["gRPC_DIR"] = os.path.join(
            grpc.package_folder, "lib", "cmake", "grpc"
        ).replace("\\", "/")
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        # grpc's ssl.cmake locates OpenSSL through the built-in FindOpenSSL
        # module, which needs the registry package root.
        tc.variables["OPENSSL_ROOT_DIR"] = openssl.package_folder.replace("\\", "/")
        # Protobuf's CMake config only defines protobuf_generate_cpp() when
        # MODULE_COMPATIBLE is on, and KylinAiProtoGenerate.cmake calls it.
        tc.variables["protobuf_MODULE_COMPATIBLE"] = "ON"
        # Codegen binaries (see the module docstring).
        tc.variables["Protobuf_PROTOC_EXECUTABLE"] = os.path.join(
            protobuf.package_folder, "bin", "protoc"
        ).replace("\\", "/")
        tc.variables["GRPC_CPP_PLUGIN"] = os.path.join(
            grpc.package_folder, "bin", "grpc_cpp_plugin"
        ).replace("\\", "/")
        # R51: build the upstream test program so build() can run it.
        tc.variables["ENABLE_TEST"] = "ON"
        # Absorb the non-PIC zlib/1.3.1 static objects (see requirements()):
        # --exclude-libs,ALL makes archive symbols non-preemptible, so lld
        # resolves the R_AARCH64_ADR_PREL_PG_HI21 / ADD_ABS_LO12_NC relocations
        # inside the DSO instead of rejecting them.  It also keeps the linked
        # static-dependency symbols out of this library's dynamic symbol table.
        # CMakeToolchain exposes these as extra_*linkflags -> CMAKE_*_LINKER_FLAGS.
        tc.extra_sharedlinkflags = ["-Wl,--exclude-libs,ALL"]
        tc.extra_exelinkflags = ["-Wl,--exclude-libs,ALL"]
        # CMake has no Platform/HarmonyOS.cmake, so the SONAME flags stay empty
        # and shared libraries are linked without DT_SONAME.  The target does
        # set VERSION/SOVERSION (2.0.0 / 2), so supplying the flag makes lld
        # emit a real soname: the library gets libkylin-ai-document-service.so.2
        # and consumers record that bare name instead of a path-form DT_NEEDED
        # (which the loader cannot resolve).  CI L5a requires DT_SONAME.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # ── 上游官方测试（R51 三步法第 2 步：实际运行）──
        # The upstream test program is the only test artifact in the source
        # tree (no enable_testing()/add_test() anywhere).  Run it and let its
        # output land in the build log so L1c can see the execution trace.
        upstream_test = os.path.join(self.build_folder, "test", "test")
        if not os.path.isfile(upstream_test):
            raise ConanException(
                "upstream test program not built: {0} (ENABLE_TEST=ON was "
                "requested)".format(upstream_test))
        # The test binary lives one level below the build tree and carries no
        # RPATH (CMake build-tree RPATH is disabled under the OHOS toolchain),
        # so both this library and libsystemd.so.0 must be resolved explicitly.
        run_env = Environment()
        run_env.prepend_path("LD_LIBRARY_PATH", self.build_folder)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                run_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        with run_env.vars(self).apply():
            self.run(upstream_test)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["kylin-ai-document-service"]
        # Headers install to include/kylin-ai-document-service/ (upstream
        # layout), so consumers include <client.h> from that directory.
        self.cpp_info.includedirs = ["include/kylin-ai-document-service"]
