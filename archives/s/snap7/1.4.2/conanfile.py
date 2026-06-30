#!/usr/bin/env python3
"""Conan recipe for snap7 1.4.2 — custom Makefile build system.

snap7 uses custom Makefiles in build/unix/ rather than standard autotools.
This recipe builds a static library (R26: BUILD_SHARED_LIBS=OFF).

Source modifications applied in build():
- Create aarch64_linux.mk for ARM64 platform
- Patch common.mk to use clang++ and build static library
- Fix pthread_cancel/pthread_setcancelstate not available on HarmonyOS
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import download, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Snap7Conan(ConanFile):
    name = "snap7"
    version = "1.4.2"
    description = "Ethernet communication suite that works natively with Siemens S7 PLCs"
    license = "LGPL-3.0-or-later"
    homepage = "https://snap7.sourceforge.net/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # snap7 source is distributed as .7z, which conan's get() cannot extract.
        # Download manually and use 7za to extract.
        src_data = self.conan_data["sources"]
        url = src_data["url"]
        sha256 = src_data.get("sha256", "")
        filename = os.path.basename(url)
        # Check if file exists in local cache (e.g. CI with slow network)
        local_cache = os.path.join(os.environ.get("TMPDIR", "/tmp"), "builds", filename)
        if os.path.exists(local_cache):
            shutil.copy(local_cache, filename)
        else:
            download(self, url, filename, sha256=sha256)
        # Verify SHA256 if provided
        if sha256:
            import hashlib
            h = hashlib.sha256()
            with open(filename, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            actual = h.hexdigest()
            if actual != sha256:
                raise Exception(f"SHA256 mismatch: expected {sha256}, got {actual}")
        # Extract using 7za
        self.run(f"7za x {filename} -o. -y")
        # Strip root directory if there's only one top-level dir
        entries = [d for d in os.listdir(".")
                   if not d.startswith('.') and os.path.isdir(d)]
        if len(entries) == 1:
            root_dir = entries[0]
            for item in os.listdir(root_dir):
                src_item = os.path.join(root_dir, item)
                dst_item = os.path.join(".", item)
                if os.path.exists(dst_item):
                    import shutil as sh
                    sh.rmtree(dst_item) if os.path.isdir(dst_item) else os.remove(dst_item)
                shutil.move(src_item, dst_item)
            os.rmdir(root_dir)
        # Clean up archive
        if os.path.exists(filename):
            os.remove(filename)

    def generate(self):
        # R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF)
        # snap7 builds a static library (libsnap7.a) via patched common.mk
        pass

    def _patch_sources(self):
        """Apply source patches for HarmonyOS/aarch64 compatibility."""
        build_unix = os.path.join(self.source_folder, "build", "unix")

        # 1. Create aarch64_linux.mk
        aarch64_mk = os.path.join(build_unix, "aarch64_linux.mk")
        with open(aarch64_mk, "w") as f:
            f.write("""##
## AArch64 (ARMv8) Linux Makefile
##
TargetCPU  :=aarch64
OS         :=linux
CXXFLAGS   := -O3 -fPIC

include common.mk
""")

        # 2. Patch common.mk: use clang, build static library
        common_mk = os.path.join(build_unix, "common.mk")
        with open(common_mk, "r") as f:
            content = f.read()
        content = content.replace("LinkerName             :=g++",
                                  "LinkerName             :=clang++")
        content = content.replace("SharedObjectLinkerName :=g++ -shared -fPIC",
                                  "SharedObjectLinkerName :=llvm-ar rcs")
        content = content.replace('OutputFile             :=../bin/$(Platform)/libsnap7.so',
                                  'OutputFile             :=../bin/$(Platform)/libsnap7.a')
        content = content.replace("AR       := ar rcus",
                                  "AR       := llvm-ar rcus")
        content = content.replace("CXX      := g++",
                                  "CXX      := clang++")
        content = content.replace("CC       := gcc",
                                  "CC       := clang")
        # Fix link command: remove shared linker flags, use ar syntax
        content = content.replace(
            "\t$(SharedObjectLinkerName) $(OutputSwitch)$(OutputFile) @$(ObjectsFileList) $(LibPath) $(Libs) $(LinkOptions)",
            "\t$(SharedObjectLinkerName) $(OutputFile) @$(ObjectsFileList)")
        # Fix install target
        content = content.replace(
            "install: all\n\tcp -f $(OutputFile) $(LibInstall)",
            "install: all\n\tinstall -d $(DESTDIR)$(LibInstall)\n\tinstall -d $(DESTDIR)/usr/include\n\tinstall -m 644 $(OutputFile) $(DESTDIR)$(LibInstall)\n\tinstall -m 644 ../../release/Wrappers/c-cpp/snap7.h $(DESTDIR)/usr/include/")
        with open(common_mk, "w") as f:
            f.write(content)

        # 3. Fix pthread_cancel not available on HarmonyOS
        unix_threads_h = os.path.join(self.source_folder, "src", "sys", "unix_threads.h")
        with open(unix_threads_h, "r") as f:
            content = f.read()
        content = content.replace(
            "    void ThreadKill() \n    {\n        pthread_cancel(th);\n    };",
            "    void ThreadKill() \n    {\n        // pthread_cancel not available on HarmonyOS\n    };")
        with open(unix_threads_h, "w") as f:
            f.write(content)

        # 4. Fix pthread_setcanceltype/pthread_setcancelstate
        snap_threads_cpp = os.path.join(self.source_folder, "src", "sys", "snap_threads.cpp")
        with open(snap_threads_cpp, "r") as f:
            content = f.read()
        content = content.replace(
            "    int last_type, last_state;\n    pthread_setcanceltype(PTHREAD_CANCEL_ASYNCHRONOUS, &last_type);\n    pthread_setcancelstate(PTHREAD_CANCEL_ENABLE, &last_state);",
            "    // pthread cancellation not available on HarmonyOS\n    // int last_type, last_state;\n    // pthread_setcanceltype(PTHREAD_CANCEL_ASYNCHRONOUS, &last_type);\n    // pthread_setcancelstate(PTHREAD_CANCEL_ENABLE, &last_state);")
        with open(snap_threads_cpp, "w") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)
        self._patch_sources()
        build_unix = os.path.join(self.source_folder, "build", "unix")
        self.run(f"make -C {build_unix} -f aarch64_linux.mk -j1")

    def package(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        include_dir = os.path.join(self.package_folder, "include")
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(include_dir, exist_ok=True)
        # Library is at build/bin/aarch64-linux/libsnap7.a (OutputFile uses ../bin/)
        lib_path = os.path.join(self.source_folder, "build", "bin", "aarch64-linux", "libsnap7.a")
        if os.path.exists(lib_path):
            shutil.copy(lib_path, lib_dir)
        else:
            # Fallback: search for libsnap7.a in build directory
            for root, dirs, files in os.walk(os.path.join(self.source_folder, "build")):
                if "libsnap7.a" in files:
                    shutil.copy(os.path.join(root, "libsnap7.a"), lib_dir)
                    break
        header_src = os.path.join(self.source_folder, "release", "Wrappers", "c-cpp", "snap7.h")
        if os.path.exists(header_src):
            shutil.copy(header_src, include_dir)

    def package_info(self):
        self.cpp_info.libs = ["snap7"]
        # snap7 is a C++ library; C++ runtime must be linked by consumers
        self.cpp_info.system_libs = ["c++", "c++abi"]
