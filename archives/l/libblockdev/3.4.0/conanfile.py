#!/usr/bin/env python3
"""Conan recipe — libblockdev 3.4.0 (Autotools).

libblockdev is a C library for manipulating block devices with a
plugin-based architecture. Adapted to HarmonyOS PC (aarch64) with
only the loop plugin enabled; all other plugins are disabled since
HarmonyOS lacks the required system libraries (LVM, Btrfs, dm-crypt,
etc.).

Key adaptations:
  - libudev provided by libudev-zero conan package
  - libkmod provided by an inline stub (HarmonyOS has no kmod subsystem)
  - uname sysname check patched to accept HarmonyOS
  - config.guess patched for aarch64-unknown-linux-ohos
  - umask 077 → 022 (HMDFS limitation)
  - libtool/automake m4 downgraded for toolchain compatibility
"""
import os
import textwrap

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibblockdevConan(ConanFile):
    name = "libblockdev"
    version = "3.4.0"
    description = "Library for manipulating block devices with plugin-based architecture"
    license = "LGPL-2.0"
    homepage = "https://github.com/storaged-project/libblockdev"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # Generate .pc files for conan dependencies so autotools configure
    # can find glib-2.0, libudev, etc. via pkg-config.
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib2/2.88.0")
        self.requires("zlib/1.3.1")
        self.requires("libudev-zero/1.0.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Disable all plugins except loop (HarmonyOS lacks LVM, Btrfs, etc.)
        for plugin in ("btrfs", "lvm", "lvm-dbus", "mpath", "dm", "crypto",
                       "escrow", "nvdimm", "nvme", "smart", "smartmontools",
                       "s390", "fs", "part", "swap", "tools", "python3", "mdraid"):
            tc.configure_args.append(f"--without-{plugin}")
        tc.configure_args.append("--with-loop")
        # HarmonyOS has no /bin/bash; use /bin/sh for Makefile SHELL
        tc.configure_args.append("SHELL=/bin/sh")
        # Workaround: Conan 2.x may use a stale build folder for cached
        # dependencies. Explicitly add include paths from the actual package
        # folders to ensure headers like libudev.h are found.
        for dep_name in ("glib2", "libudev-zero", "zlib", "pcre2"):
            dep = self.dependencies.get(dep_name)
            if dep:
                inc_dir = os.path.join(dep.package_folder, "include")
                if os.path.isdir(inc_dir):
                    tc.extra_cflags.append(f"-I{inc_dir}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Create libkmod stub (HarmonyOS has no kernel module loading subsystem)
        self._create_kmod_stub()

        # Add dependency package pkgconfig directories to PKG_CONFIG_PATH.
        # glib2 installs glib-2.0.pc, gobject-2.0.pc, gio-2.0.pc etc. in its
        # package folder; libudev-zero installs libudev.pc. PkgConfigDeps only
        # generates .pc files for deps with pkg_config_name property, so we
        # also need the real installed .pc files.
        pkg_config_dirs = []
        for dep_name in ("glib2", "libudev-zero", "zlib", "pcre2"):
            dep = self.dependencies.get(dep_name)
            if dep:
                pc_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
                if os.path.isdir(pc_dir):
                    pkg_config_dirs.append(pc_dir)
        if pkg_config_dirs:
            existing = os.environ.get("PKG_CONFIG_PATH", "")
            all_dirs = pkg_config_dirs + ([existing] if existing else [])
            os.environ["PKG_CONFIG_PATH"] = ":".join(all_dirs)
            self.output.info(f"PKG_CONFIG_PATH set to: {os.environ['PKG_CONFIG_PATH']}")

        autotools = Autotools(self)
        autotools.configure()
        # Touch generated files to prevent make from trying to run
        # aclocal/automake (not available on HarmonyOS). When conan copies
        # source to the build folder, timestamps get reset and make thinks
        # generated files need regeneration.
        src = self.source_folder
        for name in ("aclocal.m4", "configure", "config.guess", "config.sub"):
            p = os.path.join(src, name)
            if os.path.exists(p):
                os.utime(p, None)
        for root, _, files in os.walk(src):
            for fname in files:
                if fname in ("Makefile.in", "ltmain.sh"):
                    os.utime(os.path.join(root, fname), None)
        # Remove .la files from dependency packages to prevent libtool from
        # following incorrect libdir paths (e.g. //lib/libpcre2-8.la from
        # prefix=/). Static .a files are sufficient for static linking.
        for dep_name in ("glib2", "libudev-zero", "zlib", "pcre2"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    for fname in os.listdir(lib_dir):
                        if fname.endswith(".la"):
                            la_path = os.path.join(lib_dir, fname)
                            try:
                                os.remove(la_path)
                                self.output.info(f"Removed .la: {la_path}")
                            except OSError:
                                pass
        # Override SHELL in make to /bin/sh (HarmonyOS has no /bin/bash)
        autotools.make(args=["-j1", "SHELL=/bin/sh"])

    def _create_kmod_stub(self):
        """Create a minimal libkmod stub library and pkg-config file.

        HarmonyOS has no libkmod; we provide a stub that returns NULL from
        kmod_new() so all bd_utils_*_kernel_module() functions gracefully
        report failure instead of crashing.
        """
        stub_dir = os.path.join(self.build_folder, "kmod_stub")
        os.makedirs(stub_dir, exist_ok=True)

        # --- libkmod.h ---
        libkmod_h = textwrap.dedent("""\
            #ifndef LIBKMOD_H
            #define LIBKMOD_H

            #include <stddef.h>
            #include <stdbool.h>

            #ifdef __cplusplus
            extern "C" {
            #endif

            struct kmod_ctx;
            struct kmod_module;
            struct kmod_list;

            enum kmod_module_initstate {
                KMOD_MODULE_BUILTIN = 2,
            };

            enum kmod_probe_flags {
                KMOD_PROBE_FAIL_ON_LOADED = 0,
            };

            struct kmod_ctx *kmod_new(const char *dirname, const char * const *config_paths);
            struct kmod_ctx *kmod_ref(struct kmod_ctx *ctx);
            struct kmod_ctx *kmod_unref(struct kmod_ctx *ctx);
            void kmod_set_log_priority(struct kmod_ctx *ctx, int priority);
                typedef void (*kmod_log_fn)(void *log_data, int priority,
                                           const char *file, int line,
                                           const char *fn, const char *format,
                                           __builtin_va_list args);
            void kmod_set_log_fn(struct kmod_ctx *ctx, kmod_log_fn log_fn, void *log_data);

            int kmod_module_new_from_lookup(struct kmod_ctx *ctx, const char *name,
                                            struct kmod_list **list);
            int kmod_module_new_from_name(struct kmod_ctx *ctx, const char *name,
                                          struct kmod_module **mod);
            int kmod_module_new_from_loaded(struct kmod_ctx *ctx, struct kmod_list **list);
            struct kmod_module *kmod_module_get_module(struct kmod_list *entry);
            const char *kmod_module_get_path(const struct kmod_module *mod);
            const char *kmod_module_get_name(const struct kmod_module *mod);
            int kmod_module_get_initstate(const struct kmod_module *mod);
            int kmod_module_probe_insert_module(struct kmod_module *mod,
                                                unsigned int flags, const char *options,
                                                int (*run_install)(struct kmod_module *m, const char *opts),
                                                void *data, void (*print_action)(struct kmod_module *m, bool action, const char *opts));
            int kmod_module_remove_module(struct kmod_module *mod, unsigned int flags);
            struct kmod_module *kmod_module_unref(struct kmod_module *mod);
            int kmod_module_unref_list(struct kmod_list *list);
            struct kmod_list *kmod_list_next(struct kmod_list *list, struct kmod_list *curr);

            #ifdef __cplusplus
            }
            #endif

            #endif /* LIBKMOD_H */
        """)

        # --- libkmod_stub.c ---
        libkmod_c = textwrap.dedent("""\
            #include "libkmod.h"

            /* Stub: HarmonyOS has no kernel module loading subsystem.
               kmod_new() returns NULL so callers gracefully report failure. */
            struct kmod_ctx *kmod_new(const char *dirname, const char * const *config_paths) {
                (void)dirname; (void)config_paths;
                return NULL;
            }
            struct kmod_ctx *kmod_ref(struct kmod_ctx *ctx) { return ctx; }
            struct kmod_ctx *kmod_unref(struct kmod_ctx *ctx) { return NULL; }
            void kmod_set_log_priority(struct kmod_ctx *ctx, int priority) { (void)ctx; (void)priority; }
            void kmod_set_log_fn(struct kmod_ctx *ctx, kmod_log_fn log_fn, void *log_data) { (void)ctx; (void)log_fn; (void)log_data; }
            int kmod_module_new_from_lookup(struct kmod_ctx *ctx, const char *name, struct kmod_list **list) {
                (void)ctx; (void)name; *list = NULL; return -1;
            }
            int kmod_module_new_from_name(struct kmod_ctx *ctx, const char *name, struct kmod_module **mod) {
                (void)ctx; (void)name; *mod = NULL; return -1;
            }
            int kmod_module_new_from_loaded(struct kmod_ctx *ctx, struct kmod_list **list) {
                (void)ctx; *list = NULL; return -1;
            }
            struct kmod_module *kmod_module_get_module(struct kmod_list *entry) { (void)entry; return NULL; }
            const char *kmod_module_get_path(const struct kmod_module *mod) { (void)mod; return NULL; }
            const char *kmod_module_get_name(const struct kmod_module *mod) { (void)mod; return NULL; }
            int kmod_module_get_initstate(const struct kmod_module *mod) { (void)mod; return 0; }
            int kmod_module_probe_insert_module(struct kmod_module *mod, unsigned int flags, const char *options,
                                                int (*run_install)(struct kmod_module *m, const char *opts),
                                                void *data, void (*print_action)(struct kmod_module *m, bool action, const char *opts)) {
                (void)mod; (void)flags; (void)options; (void)run_install; (void)data; (void)print_action;
                return -1;
            }
            int kmod_module_remove_module(struct kmod_module *mod, unsigned int flags) { (void)mod; (void)flags; return -1; }
            struct kmod_module *kmod_module_unref(struct kmod_module *mod) { (void)mod; return NULL; }
            int kmod_module_unref_list(struct kmod_list *list) { (void)list; return 0; }
            struct kmod_list *kmod_list_next(struct kmod_list *list, struct kmod_list *curr) { (void)list; (void)curr; return NULL; }
        """)

        # Write stub source files
        with open(os.path.join(stub_dir, "libkmod.h"), "w") as f:
            f.write(libkmod_h)
        with open(os.path.join(stub_dir, "libkmod_stub.c"), "w") as f:
            f.write(libkmod_c)

        # Write pkg-config file
        pc_content = textwrap.dedent(f"""\
            prefix={stub_dir}
            exec_prefix=${{prefix}}
            libdir=${{prefix}}
            includedir=${{prefix}}

            Name: libkmod
            Description: libkmod stub for HarmonyOS
            Version: 33
            Libs: -L${{libdir}} -lkmod
            Cflags: -I${{includedir}}
        """)
        with open(os.path.join(stub_dir, "libkmod.pc"), "w") as f:
            f.write(pc_content)

        # Compile the stub library
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        ar = "llvm-ar"

        self.run(f'{cc} -c -fPIC -o "{stub_dir}/libkmod_stub.o" "{stub_dir}/libkmod_stub.c" -I"{stub_dir}"')
        self.run(f'{ar} rcs "{stub_dir}/libkmod.a" "{stub_dir}/libkmod_stub.o"')

        # Make stub discoverable by configure (pkg-config)
        pkg_config_path = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = stub_dir + (":" + pkg_config_path if pkg_config_path else "")

        self.output.info(f"libkmod stub created at {stub_dir}")

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["SHELL=/bin/sh"])

    def package_info(self):
        self.cpp_info.libs = ["blockdev", "bd_utils"]
        self.cpp_info.system_libs = ["m", "dl", "pthread"]
        self.cpp_info.set_property("pkg_config_name", "libblockdev")
