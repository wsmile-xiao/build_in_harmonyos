#!/usr/bin/env python3
"""Conan recipe for upb 0.0.0-git200730 - the micro protocol buffers runtime.

This is the 2020-07-30 snapshot of google/upb (the C runtimes for protobuf).
Upstream's generated CMakeLists is incomplete (it never defines the
``descriptor_upb_proto`` target that the library sources need, defines no test
targets and has no install rules), so the recipe compiles the C sources
directly into ``libupb.a`` and installs the public headers.

Upstream tests are C/C++ programs driven by ``tests/testmain.cc``.  The two
that need no protoc-generated ``*.upb.h`` headers (``pb/test_varint.c`` and
``table.cc``) are built and run here; the remaining ones require
protoc + the protoc-gen-upb plugin (Bazel toolchain), which is not available
in this environment - see test_package/MANIFEST.yml.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# All C sources for the runtime (+ the two checked-in generated files).
SOURCES = (
    "upb/decode.c",
    "upb/def.c",
    "upb/encode.c",
    "upb/handlers.c",
    "upb/json_decode.c",
    "upb/json_encode.c",
    "upb/msg.c",
    "upb/port.c",
    "upb/reflection.c",
    "upb/sink.c",
    "upb/table.c",
    "upb/text_encode.c",
    "upb/upb.c",
    "upb/json/printer.c",
    "upb/pb/compile_decoder.c",
    "upb/pb/decoder.c",
    "upb/pb/encoder.c",
    "upb/pb/textprinter.c",
    "upb/pb/varint.c",
    "generated_for_cmake/google/protobuf/descriptor.upb.c",
    "generated_for_cmake/upb/json/parser.c",
)

# Upstream tests that build without protoc-generated headers.
RUNNABLE_TESTS = (
    "tests/pb/test_varint.c",
    "tests/test_table.cc",
)


class UpbConan(ConanFile):
    name = "upb"
    version = "0.0.0-git200730"
    description = "micro protobuf (upb) C runtime"
    license = "MIT"
    homepage = "https://github.com/protocolbuffers/upb"
    url = ""

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "upb OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        cxx = self._compiler("cpp", "clang++")
        ar = os.path.join(os.path.dirname(cc), "llvm-ar")
        if not os.path.isfile(ar):
            ar = "ar"

        inc = ' -I. -Igenerated_for_cmake'
        objs = []
        for src in SOURCES:
            obj = src.replace("/", "_") + ".o"
            self.run('"{}" -O2 -fPIC -std=gnu99{} -c "{}" -o "{}"'
                     .format(cc, inc, src, obj), cwd=self.source_folder)
            objs.append(obj)
        self.run('"{}" rcs libupb.a {}'.format(ar, " ".join(objs)),
                 cwd=self.source_folder)

        # Build and run the runnable upstream tests.
        for test in RUNNABLE_TESTS:
            name = os.path.splitext(os.path.basename(test))[0]
            ext = os.path.splitext(test)[1]
            if ext == ".cc":
                tcc, tstd = cxx, "-std=gnu++14"
            else:
                tcc, tstd = cc, "-std=gnu99"
            self.run('"{}" -O2 {} {} -c "{}" -o "{}.o"'
                     .format(tcc, tstd, inc, test, name), cwd=self.source_folder)
            self.run('"{}" -O2 -std=gnu++14{} -c tests/testmain.cc -o testmain.o'
                     .format(cxx, inc), cwd=self.source_folder)
            self.run('"{}" -O2 {}.o testmain.o libupb.a -o "{}"'
                     .format(cxx, name, name), cwd=self.source_folder)
            self.run('"./{}"'.format(name), cwd=self.source_folder)
            self.output.info("upstream %s passed" % name)

    def package(self):
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "libupb.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        for pattern in ("*.h", "*.hpp", "*.inc"):
            copy(self, pattern, os.path.join(self.source_folder, "upb"),
                 os.path.join(self.package_folder, "include", "upb"))
        copy(self, "descriptor.upb.h",
             os.path.join(self.source_folder, "generated_for_cmake", "google", "protobuf"),
             os.path.join(self.package_folder, "include", "google", "protobuf"))

    def package_info(self):
        self.cpp_info.libs = ["upb"]
