#!/usr/bin/env python3
"""Conan recipe — bcc 0.37.0 (CMake project).

bcc (BPF Compiler Collection) builds with CMake. The upstream tarball does NOT
contain the libbpf git submodule (src/cc/libbpf is empty), so the recipe
fetches the official libbpf source in source() and builds it in-tree
(CMAKE_USE_LIBBPF_PACKAGE=OFF); no external libbpf conan requirement.

OHOS toolchain constraint (see notes.md, adapted in Step 2):
  * Published llvm packages (llvm/15.0.4/20.1.0/22.1.0) build AArch64 target
    only — bcc's clang frontend requires the LLVM BPF backend
    (LLVMInitializeBPFTarget), which only the OHOS SDK LLVM 15.0.4 provides.
  * The SDK LLVM embeds a libc++ with ABI inline namespace `std::__h` (device
    default libcxx-ohos uses `std::__n1`); bcc must compile with `__h` headers
    and needs a small shim for the iostream globals the SDK libs do not export.
  This recipe therefore drives the SDK LLVM exactly as the local Step 2 build:
  LLVM_DIR shim -> SDK LLVM, `__h` libcxx headers, and an iostream shim
  static lib, all materialized in generate()/build() (reproducible in CI where
  the profile already pins /data/service/hnp/bin/clang).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

SDK_LLVM = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm"
LIBCXX_OHOS = SDK_LLVM + "/include/libcxx-ohos/include/c++/v1"

LLVM_SHIM_CONFIG = """# Minimal LLVMConfig.cmake shim -> OHOS SDK LLVM 15.0.4 (has BPF target).
# The SDK's stock LLVMConfig.cmake -> LLVMExports.cmake references per-component
# static libs stripped from the SDK, so it cannot be consumed directly. bcc with
# ENABLE_LLVM_SHARED=ON only needs the monolithic libLLVM.so + include tree.
set(LLVM_PACKAGE_VERSION "15.0.4")
set(LLVM_VERSION_MAJOR 15)
set(LLVM_VERSION_MINOR 0)
set(LLVM_VERSION_PATCH 4)
set(LLVM_INCLUDE_DIRS "{sdk}/include")
set(LLVM_LIBRARY_DIRS "{sdk}/lib")
set(LLVM_DEFINITIONS "")
set(LLVM_AVAILABLE_LIBS "LLVM;clang-cpp")
set(LLVM_FOUND TRUE)
set(LLVM_CONFIGURATION_TYPES Release)
if(NOT TARGET LLVM)
  add_library(LLVM SHARED IMPORTED)
  set_target_properties(LLVM PROPERTIES
    IMPORTED_LOCATION "{sdk}/lib/libLLVM.so")
endif()
function(llvm_map_components_to_libnames out_var)
  set(${{out_var}} "LLVM" PARENT_SCOPE)
endfunction()
function(llvm_expand_dependencies out_var)
  set(${{out_var}} "LLVM" PARENT_SCOPE)
endfunction()
"""

IOSTREAM_SHIM_CC = """// iostream globals shim for bcc on OHOS (__h ABI libc++).
#include <streambuf>
#include <ostream>
#include <unistd.h>
namespace std { namespace __h {
ios_base::Init::Init() {}
ios_base::Init::~Init() {}
namespace {
class FdStreambuf : public basic_streambuf<char> {
 public:
  explicit FdStreambuf(int fd) : fd_(fd) {}
 protected:
  int_type overflow(int_type c) override {
    if (c != traits_type::eof()) {
      char ch = traits_type::to_char_type(c);
      if (write(fd_, &ch, 1) != 1) return traits_type::eof();
    }
    return c;
  }
  streamsize xsputn(const char *s, streamsize n) override {
    ssize_t r = write(fd_, s, static_cast<size_t>(n));
    return r < 0 ? 0 : r;
  }
  int sync() override { return 0; }
 private:
  int fd_;
};
FdStreambuf cout_buf(1);
FdStreambuf cerr_buf(2);
}  // namespace
basic_ostream<char> cout(&cout_buf);
basic_ostream<char> cerr(&cerr_buf);
basic_ostream<char> clog(&cerr_buf);
}  // namespace __h
}  // namespace std
"""


LIBBPF_URL = "https://github.com/libbpf/libbpf/archive/refs/tags/v1.4.5.tar.gz"
LIBBPF_SHA256 = "e225c1fe694b9540271b1f2f15eb882c21c34511ba7b8835b0a13003b3ebde8c"


class BccConan(ConanFile):
    name = "bcc"
    version = "0.37.0"
    description = "bcc 0.37.0 — BPF Compiler Collection (libbcc)"
    license = "Apache-2.0"
    homepage = "https://github.com/iovisor/bcc"
    url = "https://github.com/iovisor/bcc"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # bcc links libelf (elfutils) for ELF parsing; zlib for bcc_zip.
        # Use elfutils (complete libelf headers, incl. libelf_config.h) rather
        # than libelf/0.8.13 whose packaged headers lack libelf_config.h.
        self.requires("elfutils/0.195")
        self.requires("zlib/1.3.1.1")
        # libbpf is NOT published to the ohpcd registry (registry probe on the
        # remote returns a missing-package error). Upstream bcc vendors libbpf
        # as a git submodule (src/cc/libbpf, absent from the release tarball),
        # so the recipe fetches the official libbpf source in source() and
        # builds it in-tree (CMAKE_USE_LIBBPF_PACKAGE stays default off).
        # No conan requires() for libbpf here.

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Populate the vendored libbpf submodule (absent from the bcc tarball).
        get(self, url=LIBBPF_URL, sha256=LIBBPF_SHA256,
            destination="src/cc/libbpf", strip_root=True)
        # bcc-specific BPF map types (INSN_ARRAY/RHASH) live only in
        # compat/linux/virtual_bpf.h; generate compat/linux/bpf.h exactly as
        # src/cc/CMakeLists.txt does in CMAKE_USE_LIBBPF_PACKAGE mode, so the
        # augmented header (with bcc's extra enum members) is available to the
        # in-tree build too.
        compat_bpf_h = os.path.join(self.source_folder, "src/cc/compat",
                                    "linux", "bpf.h")
        if not os.path.exists(compat_bpf_h):
            self.run(
                "sh -c \"cd %s/src/cc/compat/linux && "
                "grep -ve '\\*\\*\\*\\*' virtual_bpf.h > bpf.h\""
                % self.source_folder)
        # In-tree mode the introspection target includes only
        # libbpf/include/uapi, whose bpf.h lacks bcc's extra map enums; add the
        # compat dir (holding the generated augmented bpf.h) to its includes.
        iml = os.path.join(self.source_folder, "introspection",
                           "CMakeLists.txt")
        with open(iml) as f:
            iml_text = f.read()
        if "src/cc/compat)  # added by ohc recipe" not in iml_text:
            iml_text = iml_text.replace(
                "else()\n"
                "include_directories(${PROJECT_SOURCE_DIR}/src/cc/libbpf/"
                "include/uapi)\n",
                "else()\n"
                "include_directories(${PROJECT_SOURCE_DIR}/src/cc/compat)  # "
                "added by ohc recipe\n"
                "include_directories(${PROJECT_SOURCE_DIR}/src/cc/libbpf/"
                "include/uapi)\n", 1)
            with open(iml, "w") as f:
                f.write(iml_text)
        # Vendored libbpf's netlink.c hits the OHOS sockaddr_storage
        # redefinition conflict (linux/socket.h vs sys/socket.h); apply the
        # same guard used for bcc's own libbpf.c (see patch 0001).
        netlink = os.path.join(self.source_folder, "src/cc/libbpf", "src",
                               "netlink.c")
        with open(netlink) as f:
            nl_text = f.read()
        if "_UAPI_LINUX_SOCKET_H" not in nl_text:
            nl_text = nl_text.replace(
                "#include <arpa/inet.h>\n",
                "#include <arpa/inet.h>\n"
                "#ifdef __OHOS__\n"
                "#include <sys/socket.h>\n"
                "typedef unsigned short __kernel_sa_family_t;\n"
                "#define _UAPI_LINUX_SOCKET_H\n"
                "#endif\n", 1)
            nl_text = nl_text.replace(
                "#include <linux/netdev.h>\n"
                "#include <sys/socket.h>\n",
                "#include <linux/netdev.h>\n"
                "#ifndef __OHOS__\n"
                "#include <sys/socket.h>\n"
                "#endif\n", 1)
            with open(netlink, "w") as f:
                f.write(nl_text)

    def generate(self):
        # 1) LLVM shim config -> SDK LLVM (with BPF target)
        shim_dir = os.path.join(self.build_folder, "llvm-shim")
        os.makedirs(shim_dir, exist_ok=True)
        with open(os.path.join(shim_dir, "LLVMConfig.cmake"), "w") as f:
            f.write(LLVM_SHIM_CONFIG.format(sdk=SDK_LLVM))

        # 2) `__h` ABI libc++ headers: copy libcxx-ohos and flip ABI namespace
        hdr = os.path.join(self.build_folder, "libcxx-h", "v1")
        if os.path.isdir(LIBCXX_OHOS) and not os.path.exists(hdr):
            os.makedirs(hdr, exist_ok=True)
            shutil.copytree(LIBCXX_OHOS, hdr, dirs_exist_ok=True)
            cfg = os.path.join(hdr, "__config_site")
            if os.path.exists(cfg):
                with open(cfg) as f:
                    data = f.read()
                data = data.replace(
                    "#define _LIBCPP_ABI_NAMESPACE __n1",
                    "#define _LIBCPP_ABI_NAMESPACE __h")
                with open(cfg, "w") as f:
                    f.write(data)

        # 3) iostream shim source (compiled in build())
        with open(os.path.join(self.build_folder, "ohos_iostream_shim.cc"),
                  "w") as f:
            f.write(IOSTREAM_SHIM_CC)

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Build the vendored libbpf (fetched in source()) in-tree, so no
        # external/unpublished libbpf package is required. With
        # CMAKE_USE_LIBBPF_PACKAGE=OFF, bcc's src/cc globs libbpf/src/*.c
        # into bpf-static/bcc_bpf.
        tc.variables["CMAKE_USE_LIBBPF_PACKAGE"] = "OFF"
        tc.variables["NO_BLAZESYM"] = "ON"
        tc.variables["ENABLE_EXAMPLES"] = "OFF"
        # python bindings build a setuptools sdist (bcc_py_python3) which fails
        # on the OHOS CI (no setuptools in the clean build env); disable it.
        tc.variables["ENABLE_PYTHON_BINDINGS"] = "OFF"
        tc.variables["LLVM_DIR"] = shim_dir
        # bcc's cmake/version.cmake falls back to a malformed "0.0.0+GITDIR-N"
        # revision when there is no git tag in the tarball, which breaks
        # VERSION/SOVERSION and leaves libbcc.so without a DT_SONAME (W3 L5
        # gate). Pin REVISION so SOVERSION 0 emits a proper SONAME.
        tc.variables["REVISION"] = self.version
        # CMake does not know the "HarmonyOS" platform, so it leaves the shared
        # library SONAME flag undefined and never emits DT_SONAME even when
        # SOVERSION is set (W3 L5 gate). Supply the flag explicitly.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_CXX_FLAGS"] = (
            "-nostdinc++ -isystem " + os.path.join(self.build_folder,
                                                   "libcxx-h", "v1"))
        # SDK libs + conan zlib/elfutils/libbpf lib dirs must be link-searchable
        # for bare `-lz` / `-lelf` (bcc links by bare name) and SDK .so deps;
        # EXE gets the iostream shim too.
        dep_lib_dirs = []
        # libbpf is built in-tree (vendored submodule), so only zlib/elfutils
        # contribute conan package lib dirs for bare -lz / -lelf resolution.
        for dep in ("zlib", "elfutils"):
            pkg = self.dependencies.get(dep)
            if pkg and pkg.package_folder:
                pf = pkg.package_folder
                dep_lib_dirs.extend(
                    d for d in (os.path.join(pf, "lib"),
                                os.path.join(pf, "usr/lib64")) if
                    os.path.isdir(d))
        lib_dirs = " ".join(
            ["-L" + d for d in [SDK_LLVM + "/lib",
                                SDK_LLVM + "/lib/aarch64-linux-ohos"]
             + dep_lib_dirs])
        rpaths = " ".join(
            ["-Wl,-rpath," + d for d in [SDK_LLVM + "/lib",
                                         SDK_LLVM + "/lib/aarch64-linux-ohos"]])
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = (
            lib_dirs + " " + rpaths + " -lz")
        # Final executables (tests) must resolve libbcc.so's undefined __h-ABI
        # symbols from the SDK clang/LLVM shared libs (as in the local build),
        # plus zlib for bcc_zip and the iostream shim for Catch iostream use.
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
            lib_dirs + " " + rpaths + " -lz "
            + SDK_LLVM + "/lib/libclang-cpp.so "
            + SDK_LLVM + "/lib/libLLVM.so "
            + "-L" + self.build_folder + " -lohos_iostream_shim")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E540: ensure the OHOS toolchain (clang++/llvm-ar) is on PATH.
        toolchain_bin = "/data/service/hnp/bin"
        os.environ["PATH"] = toolchain_bin + ":" + os.environ.get("PATH", "")
        # Compile the iostream shim against the `__h` headers first.
        cc = "clang++"
        shim = os.path.join(self.build_folder, "ohos_iostream_shim")
        self.run("%s -std=c++17 -c %s.cc -o %s.o -nostdinc++ -isystem %s"
                 % (cc, shim, shim,
                    os.path.join(self.build_folder, "libcxx-h", "v1")))
        # Archive must be named lib*.a so `-lohos_iostream_shim` resolves.
        self.run("llvm-ar rcs %s/libohos_iostream_shim.a %s.o"
                 % (self.build_folder, shim))
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["bcc"]
