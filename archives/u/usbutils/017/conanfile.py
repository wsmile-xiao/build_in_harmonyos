#!/usr/bin/env python3
"""Conan recipe for usbutils 017."""
import os
import shutil
import shlex
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy, get, replace_in_file, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class UsbutilsConan(ConanFile):
    name = "usbutils"
    version = "017"
    description = "USB utilities for Linux including lsusb"
    license = "GPL-2.0-only"
    homepage = "https://github.com/gregkh/usbutils"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("libusb/1.0.27")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        self._patch_sources()

    def _patch_sources(self):
        """Fix umask 077 issue on HMDFS (same pattern as libusb)."""
        for cfg_path in (
            os.path.join(self.source_folder, "configure"),
            os.path.join(self.source_folder, "usbhid-dump", "configure"),
        ):
            if not os.path.isfile(cfg_path):
                continue
            replace_in_file(
                self, cfg_path,
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                'tmp=`(umask 022 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            )
            replace_in_file(
                self, cfg_path,
                '(umask 077 && mkdir "$tmp")',
                '(umask 022 && mkdir "$tmp")',
            )

    def generate(self):
        if str(self.settings.os) in ("Linux", "OHOS"):
            self._create_fake_libudev()

        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-musl",
                "--host=aarch64-unknown-linux-musl",
            ])
        tc.generate()

        deps = AutotoolsDeps(self)
        if str(self.settings.os) in ("Linux", "OHOS"):
            fake_pc = os.path.join(self.build_folder, "fake_libudev", "lib", "pkgconfig")
            deps.environment.append("PKG_CONFIG_PATH", fake_pc)
        deps.generate()

    def _create_fake_libudev(self):
        """Create stub libudev header, library, and pkgconfig file."""
        fake_dir = os.path.join(self.build_folder, "fake_libudev")
        inc_dir = os.path.join(fake_dir, "include")
        lib_dir = os.path.join(fake_dir, "lib")
        pc_dir = os.path.join(fake_dir, "lib", "pkgconfig")
        for d in (inc_dir, lib_dir, pc_dir):
            os.makedirs(d, exist_ok=True)

        with open(os.path.join(inc_dir, "libudev.h"), "w") as f:
            f.write("""#ifndef _LIBUDEV_H_
#define _LIBUDEV_H_
#ifdef __cplusplus
extern "C" {
#endif
struct udev;
struct udev_hwdb;
struct udev_list_entry;
struct udev *udev_new(void);
struct udev *udev_ref(struct udev *udev);
struct udev *udev_unref(struct udev *udev);
struct udev_hwdb *udev_hwdb_new(struct udev *udev);
struct udev_hwdb *udev_hwdb_ref(struct udev_hwdb *hwdb);
struct udev_hwdb *udev_hwdb_unref(struct udev_hwdb *hwdb);
struct udev_list_entry *udev_hwdb_get_properties_list_entry(
    struct udev_hwdb *hwdb, const char *modalias, unsigned int flag);
struct udev_list_entry *udev_list_entry_get_next(struct udev_list_entry *entry);
const char *udev_list_entry_get_name(struct udev_list_entry *entry);
const char *udev_list_entry_get_value(struct udev_list_entry *entry);
#define udev_list_entry_foreach(entry, first) \\
    for (entry = first; entry != NULL; entry = udev_list_entry_get_next(entry))
#ifdef __cplusplus
}
#endif
#endif /* _LIBUDEV_H_ */
""")

        stub_c = os.path.join(lib_dir, "libudev_stub.c")
        with open(stub_c, "w") as f:
            f.write('#include "libudev.h"\n\n'
                    'struct udev *udev_new(void) { return (void*)0; }\n'
                    'struct udev *udev_ref(struct udev *u) { return (void*)0; }\n'
                    'struct udev *udev_unref(struct udev *u) { return (void*)0; }\n'
                    'struct udev_hwdb *udev_hwdb_new(struct udev *u) { return (void*)0; }\n'
                    'struct udev_hwdb *udev_hwdb_ref(struct udev_hwdb *h) { return (void*)0; }\n'
                    'struct udev_hwdb *udev_hwdb_unref(struct udev_hwdb *h) { return (void*)0; }\n'
                    'struct udev_list_entry *udev_hwdb_get_properties_list_entry'
                    '(struct udev_hwdb *h, const char *m, unsigned int f) { return (void*)0; }\n'
                    'struct udev_list_entry *udev_list_entry_get_next(struct udev_list_entry *e) { return (void*)0; }\n'
                    'const char *udev_list_entry_get_name(struct udev_list_entry *e) { return (const char*)0; }\n'
                    'const char *udev_list_entry_get_value(struct udev_list_entry *e) { return (const char*)0; }\n')

        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = comp.get("c") or os.environ.get("CC") or "clang"
        ar = os.path.join(os.path.dirname(cc), "llvm-ar")
        if not os.path.isfile(ar):
            ar = "llvm-ar"

        obj = os.path.join(lib_dir, "libudev_stub.o")
        lib = os.path.join(lib_dir, "libudev.a")
        subprocess.run([cc, "-c", "-fPIC", "-I" + inc_dir, stub_c, "-o", obj], check=True)
        subprocess.run([ar, "rcs", lib, obj], check=True)

        with open(os.path.join(pc_dir, "libudev.pc"), "w") as f:
            f.write(
                "prefix=${pcfiledir}/../..\n"
                "exec_prefix=${prefix}\n"
                "libdir=${exec_prefix}/lib\n"
                "includedir=${prefix}/include\n\n"
                "Name: libudev\n"
                "Description: stub libudev for OHOS (udev not available)\n"
                "Version: 251\n"
                "Libs: -L${libdir} -ludev\n"
                "Cflags: -I${includedir}\n"
            )

    def build(self):
        apply_conandata_patches(self)
        for helper in ("configure", "install-sh", "missing", "compile", "depcomp"):
            path = os.path.join(self.source_folder, helper)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
        usbhid_configure = os.path.join(self.source_folder, "usbhid-dump", "configure")
        if os.path.isfile(usbhid_configure):
            os.chmod(usbhid_configure, 0o755)

        if str(self.settings.os) == "OHOS":
            build_folder = self._prepare_ohos_build_folder()
            self._configure_ohos(build_folder)
            self._fix_makefile_install_tools(build_folder)
            self._make_ohos(build_folder, args=["-j1"])
            return

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _prepare_ohos_build_folder(self):
        build_folder = self._ohos_build_folder()
        shutil.rmtree(build_folder, ignore_errors=True)
        os.makedirs(build_folder, exist_ok=True)
        src = self.source_folder
        for item in os.listdir(src):
            src_path = os.path.join(src, item)
            dst_path = os.path.join(build_folder, item)
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dst_path)
        return build_folder

    def _ohos_build_folder(self):
        token = os.path.basename(os.path.dirname(os.path.dirname(self.build_folder)))
        return os.path.join(os.path.expanduser("~"), ".conan-ohos-build",
                            f"{self.name}-{self.version}-{token}")

    def _configure_ohos(self, build_folder):
        shell = self._ohos_shell()
        configure = os.path.join(build_folder, "configure")
        fake_dir = os.path.join(self.build_folder, "fake_libudev")
        fake_inc = os.path.join(fake_dir, "include")
        fake_lib = os.path.join(fake_dir, "lib")
        fake_pc = os.path.join(fake_lib, "pkgconfig")

        libusb_cflags = []
        libusb_libs = []
        for _, dep in self.dependencies.items():
            info = dep.cpp_info
            for incdir in info.includedirs:
                libusb_cflags.append(f"-I{os.path.join(dep.package_folder, incdir)}")
            for libdir in info.libdirs:
                libusb_libs.append(f"-L{os.path.join(dep.package_folder, libdir)}")
            for lib in info.libs:
                libusb_libs.append(f"-l{lib}")
            for lib in info.system_libs:
                libusb_libs.append(f"-l{lib}")

        conandir = os.path.join(self.build_folder, "conan")
        conanbuild = os.path.join(conandir, "conanbuild.sh")
        conanrun = os.path.join(conandir, "conanrun.sh")
        if not os.path.isfile(conanbuild):
            conandir = os.path.join(self.build_folder, "build-release", "conan")
            conanbuild = os.path.join(conandir, "conanbuild.sh")
            conanrun = os.path.join(conandir, "conanrun.sh")

        cmd = f'export TMPDIR="{build_folder}" CONFIG_SHELL="{shell}" SHELL="{shell}"'
        if os.path.isfile(conanbuild):
            cmd += f' && . "{conanbuild}"'
        if os.path.isfile(conanrun):
            cmd += f' && . "{conanrun}"'
        cmd += f' && export PKG_CONFIG_PATH="{fake_pc}:${{PKG_CONFIG_PATH:-}}"'
        cmd += f' && export LIBUSB_CFLAGS="{" ".join(libusb_cflags)}"'
        cmd += f' && export LIBUSB_LIBS="{" ".join(libusb_libs)}"'
        cmd += f' && export UDEV_CFLAGS="-I{fake_inc}"'
        cmd += f' && export UDEV_LIBS="-L{fake_lib} -ludev"'
        cmd += f' && "{shell}" "{configure}" --prefix= --build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl'
        self.run(cmd, cwd=build_folder)

    def _make_ohos(self, build_folder, target=None, args=None):
        make = self.conf.get("tools.gnu:make_program", default="make")
        parts = [f'"{make}"']
        if target:
            parts.append(target)
        parts.extend(args or [])
        make_cmd = " ".join(parts)
        shell = self._ohos_shell()
        conandir = os.path.join(self.build_folder, "conan")
        conanbuild = os.path.join(conandir, "conanbuild.sh")
        conanrun = os.path.join(conandir, "conanrun.sh")
        if not os.path.isfile(conanbuild):
            conandir = os.path.join(self.build_folder, "build-release", "conan")
            conanbuild = os.path.join(conandir, "conanbuild.sh")
            conanrun = os.path.join(conandir, "conanrun.sh")
        cmd = f'export TMPDIR="{build_folder}" SHELL="{shell}"'
        if os.path.isfile(conanbuild):
            cmd += f' && . "{conanbuild}"'
        if os.path.isfile(conanrun):
            cmd += f' && . "{conanrun}"'
        cmd += f' && {make_cmd}'
        self.run(cmd, cwd=build_folder)

    def _fix_makefile_install_tools(self, build_folder):
        for root, _, files in os.walk(build_folder):
            if "Makefile" not in files:
                continue
            makefile = os.path.join(root, "Makefile")
            with open(makefile, encoding="utf-8") as handle:
                lines = handle.readlines()
            fixed = []
            for line in lines:
                if line.startswith("install_sh = "):
                    line = "install_sh = /system/bin/install\n"
                elif line.startswith("MKDIR_P = "):
                    line = "MKDIR_P = /system/bin/install -d\n"
                fixed.append(line)
            with open(makefile, "w", encoding="utf-8", newline="") as handle:
                handle.writelines(fixed)

    def _ohos_shell(self):
        return "/system/bin/sh" if os.path.isfile("/system/bin/sh") else "/bin/sh"

    def package(self):
        if str(self.settings.os) == "OHOS":
            build_folder = self._ohos_build_folder()
            self._make_ohos(build_folder, target="install",
                           args=[f'DESTDIR="{self.package_folder}"', "prefix="])
        else:
            autotools = Autotools(self)
            autotools.install()
        licenses_dir = os.path.join(self.source_folder, "LICENSES")
        if os.path.isdir(licenses_dir):
            copy(self, "*", licenses_dir, os.path.join(self.package_folder, "licenses"))
        else:
            copy(self, "COPYING", self.source_folder,
                 os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
