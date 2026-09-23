#!/usr/bin/env python3
"""Conan recipe — dwarves 1.30 (CMake, C).

dwarves (pahole) is the DWARF/CTF/BTF debugging-information toolkit:
it produces the libdwarves analysis library plus the pahole/codiff/pfunct
family of CLI tools used by the Linux kernel community and BTF-aware
toolchains. Upstream repo: https://github.com/acmel/dwarves

OHOS adaptation notes:
- The GitHub release tarball omits the lib/bpf submodule content that
  LIBBPF_EMBEDDED=ON (the default) compiles; the submodule commit pinned at
  this release is fetched separately into lib/bpf in source().
- musl (OHOS libc) has no glibc argp/obstack; both are provided by
  argp-standalone and musl-obstack, whose libdirs are fed to the custom
  Findargp/Findobstack modules via CMAKE_LIBRARY_PATH.
- libdw/libelf come from elfutils; the custom FindDWARF module needs
  CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH to see the conan-provided headers.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class DwarvesConan(ConanFile):
    name = "dwarves"
    version = "1.30"
    description = "DWARF/CTF/BTF debugging information analysis tools (pahole et al.)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/acmel/dwarves"
    url = "https://github.com/acmel/dwarves"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("elfutils/0.195")          # libdw + libelf (FindDWARF)
        self.requires("zlib/1.3.1.1")            # FindZLIB
        self.requires("argp-standalone/1.5.0")   # musl: glibc argp 缺失，需垫片
        self.requires("musl-obstack/1.2.3")      # musl: glibc obstack 缺失，需垫片

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # GitHub release tarball 不含 lib/bpf 子模块；按本版本锁定 commit 补齐，
        # 否则 CMakeLists 因 lib/bpf/src/btf.h 缺失直接 FATAL_ERROR。
        lb = self.conan_data["libbpf"]
        get(self, url=lb["url"], sha256=lb["sha256"],
            destination="lib/bpf", strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 自定义 FindDWARF/Findargp/Findobstack 模块用 find_path/find_library
        # 探测 conan 依赖（默认只查 /usr 路径），必须显式注入 include/lib 搜索路径。
        include_dirs, lib_dirs = [], []
        for _ref, _dep in self.dependencies.items():
            _pf = _dep.package_folder or ""
            for _p in _dep.cpp_info.includedirs or []:
                _abs = _p if os.path.isabs(_p) else os.path.join(_pf, _p)
                if _abs not in include_dirs:
                    include_dirs.append(_abs)
            for _p in _dep.cpp_info.libdirs or []:
                _abs = _p if os.path.isabs(_p) else os.path.join(_pf, _p)
                if _abs not in lib_dirs:
                    lib_dirs.append(_abs)
        if include_dirs:
            tc.variables["CMAKE_INCLUDE_PATH"] = ";".join(include_dirs)
            # 上游 Findargp/Findobstack 只 find_library、不注入头目录，而
            # dwarves.h 直接 #include <obstack.h>/<argp.h>（musl 垫片），
            # 必须把依赖 include 目录真正放进编译搜索路径。
            tc.variables["CMAKE_C_FLAGS"] = " ".join("-I" + d for d in include_dirs)
        if lib_dirs:
            tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(lib_dirs)
        # OHOS 无 CMake 平台模块（"System is unknown to cmake"），
        # CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 未定义，SOVERSION 不会产出
        # DT_SONAME（W3 L5a 门禁）。补上 soname 链接 flag，使 libdwarves*.so
        # 带 DT_SONAME，下游可按 SONAME 寻址。
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["dwarves_reorganize", "dwarves_emit", "dwarves"]
        self.cpp_info.includedirs = ["include/dwarves", "include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "dwarves")
        self.cpp_info.set_property("cmake_target_name", "dwarves::dwarves")
        # 公开头 dwarves.h 直接 #include <obstack.h>/<argp.h>（musl 垫片），
        # 消费者仅 link dwarves::dwarves 时也必须拿到这些头的 include 路径，
        # 故通过 requires 把依赖 target 传递出去（CMakeDeps 会展开 INTERFACE）。
        self.cpp_info.requires = [
            "elfutils::elfutils",
            "zlib::zlib",
            "argp-standalone::argp-standalone",
            "musl-obstack::musl-obstack",
        ]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))