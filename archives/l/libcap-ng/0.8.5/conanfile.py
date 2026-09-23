#!/usr/bin/env python3
"""Conan recipe for libcap-ng 0.8.5.

libcap-ng is an alternate POSIX capabilities library. The GitHub archive
tarball only contains configure.ac (no pre-generated configure script),
and the CI environment lacks automake/libtool. This recipe builds the
library by directly compiling source files with the Conan toolchain.
"""
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibcapngConan(ConanFile):
    name = "libcap-ng"
    version = "0.8.5"
    description = "An alternate POSIX capabilities library for Linux"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/stevegrubb/libcap-ng"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass  # No autotools toolchain needed; we compile directly

    def build(self):
        apply_conandata_patches(self)
        self._create_config_h()
        self._compile()

    def _get_cc(self):
        """Get C compiler from conan configuration or environment."""
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", os.environ.get("CC", "clang"))
        return cc

    def _create_config_h(self):
        """Create config.h with platform detection results."""
        src = self.source_folder
        config_h = os.path.join(src, "config.h")
        cc = self._get_cc()

        cap_defs = subprocess.run(
            [cc, "-E", "-dM", "-include", "linux/capability.h", "-x", "c", "/dev/null"],
            capture_output=True, text=True
        ).stdout
        prctl_defs = subprocess.run(
            [cc, "-E", "-dM", "-include", "sys/prctl.h", "-x", "c", "/dev/null"],
            capture_output=True, text=True
        ).stdout

        has_cap_epollwakeup = "CAP_EPOLLWAKEUP" in cap_defs
        has_pr_cap_ambient = "PR_CAP_AMBIENT" in prctl_defs

        lines = [
            "#ifndef CONFIG_H",
            "#define CONFIG_H",
            "",
            "#define HAVE_LINUX_CAPABILITY_H 1",
            "#define HAVE_SYS_XATTR_H 1",
            "#define HAVE_LINUX_SECUREBITS_H 1",
            "#define HAVE_PTHREAD_H 1",
            "#define HAVE_SYS_VFS_H 1",
            "#define HAVE_LINUX_MAGIC_H 1",
            "#define HAVE_SYSCALL_H 1",
        ]
        if has_pr_cap_ambient:
            lines.append("#define HAVE_DECL_PR_CAP_AMBIENT 1")
        lines += [
            "#define HAVE_DECL_VFS_CAP_REVISION_2 1",
            "#define HAVE_DECL_VFS_CAP_REVISION_3 1",
        ]
        if has_cap_epollwakeup:
            lines.append("#define HAVE_DECL_CAP_EPOLLWAKEUP 1")
        lines += [
            "#define HAVE_DECL_CAP_WAKE_ALARM 1",
            "#define HAVE_DECL_CAP_BLOCK_SUSPEND 1",
            "#define HAVE_DECL_CAP_AUDIT_READ 1",
            "#define HAVE_DECL_CAP_PERFMON 1",
            "#define HAVE_DECL_CAP_BPF 1",
            "#define HAVE_DECL_CAP_CHECKPOINT_RESTORE 1",
            "",
            '#define PACKAGE "libcap-ng"',
            '#define PACKAGE_NAME "libcap-ng"',
            '#define PACKAGE_VERSION "0.8.5"',
            '#define VERSION "0.8.5"',
            "",
            "#endif /* CONFIG_H */",
            "",
        ]
        with open(config_h, "w") as f:
            f.write("\n".join(lines))

    def _compile(self):
        """Compile library and utilities from source."""
        src = self.source_folder
        build_dir = self.build_folder

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", os.environ.get("CC", "clang"))
        ar = shutil.which("llvm-ar") or shutil.which("ar") or os.environ.get("AR", "llvm-ar")
        cflags_str = os.environ.get("CFLAGS", "-fPIC -O2")
        cflags_str += " -fPIC -DPIC -W -Wall -Wshadow -Wundef -D_GNU_SOURCE"
        cflags_str += f" -I{src} -I{src}/src"
        cflags = shlex.split(cflags_str)
        ldflags_str = os.environ.get("LDFLAGS", "")
        ldflags_str += " -Wl,-z,relro"
        ldflags = shlex.split(ldflags_str)
        shared = self.options.get_safe("shared", False)

        def run(cmd):
            self.output.info(f"  $ {' '.join(cmd)}")
            subprocess.run(cmd, check=True)

        # Compile library objects
        objs = []
        for srcf in ["cap-ng.c", "lookup_table.c"]:
            obj = os.path.join(build_dir, srcf.replace(".c", ".o"))
            run([cc] + cflags + ["-c", os.path.join(src, "src", srcf), "-o", obj])
            objs.append(obj)

        if shared:
            soname = "libcap-ng.so.0"
            libfile = os.path.join(build_dir, "libcap-ng.so.0.0.1")
            run([cc, "-shared", f"-Wl,-soname,{soname}"] + ldflags + ["-o", libfile] + objs)
            for link, target in [("libcap-ng.so.0", "libcap-ng.so.0.0.1"),
                                 ("libcap-ng.so", "libcap-ng.so.0")]:
                lpath = os.path.join(build_dir, link)
                if os.path.islink(lpath) or os.path.exists(lpath):
                    os.remove(lpath)
                os.symlink(target, lpath)
        else:
            libfile = os.path.join(build_dir, "libcap-ng.a")
            run([ar, "rcs", libfile] + objs)

        # Compile libdrop_ambient
        drop_obj = os.path.join(build_dir, "libdrop_ambient.o")
        run([cc] + cflags + ["-c", os.path.join(src, "src", "libdrop_ambient.c"), "-o", drop_obj])
        if shared:
            drop_lib = os.path.join(build_dir, "libdrop_ambient.so.0.0.0")
            run([cc, "-shared", "-Wl,-soname,libdrop_ambient.so.0"] + ldflags + ["-o", drop_lib, drop_obj])
            for link, target in [("libdrop_ambient.so.0", "libdrop_ambient.so.0.0.0"),
                                 ("libdrop_ambient.so", "libdrop_ambient.so.0")]:
                lpath = os.path.join(build_dir, link)
                if os.path.islink(lpath) or os.path.exists(lpath):
                    os.remove(lpath)
                os.symlink(target, lpath)
        else:
            drop_lib = os.path.join(build_dir, "libdrop_ambient.a")
            run([ar, "rcs", drop_lib, drop_obj])

        # Compile utilities (statically linked against libcap-ng)
        utils = [
            (["pscap.c"], "pscap"),
            (["netcap.c", "proc-llist.c"], "netcap"),
            (["filecap.c"], "filecap"),
            (["captest.c"], "captest"),
        ]
        ucflags_str = f"-fPIC -DPIC -W -Wall -Wshadow -Wundef -D_GNU_SOURCE -I{src} -I{src}/src"
        ucflags = shlex.split(ucflags_str)
        for srcs_list, name in utils:
            uobjs = []
            for sf in srcs_list:
                obj = os.path.join(build_dir, f"u_{sf.replace('.c', '.o')}")
                run([cc] + ucflags + ["-c", os.path.join(src, "utils", sf), "-o", obj])
                uobjs.append(obj)
            binfile = os.path.join(build_dir, name)
            run([cc] + uobjs + [libfile, "-lpthread"] + ldflags + ["-o", binfile])

    def package(self):
        src = self.source_folder
        build_dir = self.build_folder
        shared = self.options.get_safe("shared", False)

        copy(self, "cap-ng.h", os.path.join(src, "src"),
             os.path.join(self.package_folder, "include"))

        if shared:
            copy(self, "libcap-ng.so*", build_dir, os.path.join(self.package_folder, "lib"))
            copy(self, "libdrop_ambient.so*", build_dir, os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libcap-ng.a", build_dir, os.path.join(self.package_folder, "lib"))
            copy(self, "libdrop_ambient.a", build_dir, os.path.join(self.package_folder, "lib"))

        for name in ["pscap", "netcap", "filecap", "captest"]:
            copy(self, name, build_dir, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["cap-ng", "drop_ambient"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_target_name", "libcap-ng::libcap-ng")
        self.cpp_info.set_property("pkg_config_name", "libcap-ng")
        if self.options.shared:
            self.cpp_info.defines.append("CAPNG_SHARED")
