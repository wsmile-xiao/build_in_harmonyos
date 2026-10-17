#!/usr/bin/env python3
"""Conan recipe — gpgme 1.24.0 (GPGME, autotools) on HarmonyOS PC (aarch64).

GPGME is a library providing easy access to GnuPG cryptographic operations.

OHOS-specific adaptations:
  1. E007 — config.guess/config.sub patched to recognize `linux-ohos`
     (patches/0001, 0002). Native build, no --build/--host.
  2. E011 — configure umask 077 -> 022 for HMDFS temp dirs (patches/0003).
  3. E027 — --disable-nls: published libgpg-error/1.55 is built --disable-nls,
     so we do the same (no libintl/gettext dependency required).
  4. gpgrt-config hang: libgpg-error's gpgrt-config hangs under OHOS /bin/sh
     (mksh). A build-local bash wrapper is prepended to PATH so configure's
     gpg-error-config check succeeds.
  5. E012 — libgpg-error/libassuan .pc/.la from the conan packages use
     prefix=/ (wrong absolute paths). config-overrides provides corrected
     gpg-error.pc + libassuan-config wrapper + corrected .la files, and the
     build-local la dir is prepended to LDFLAGS so libtool resolves the
     dependency .la files correctly.
  6. make -j1 (E074: OHOS SELinux forbids FIFO jobserver).
  7. Tests/ tree requires a real `gpg` binary (GnuPG runtime, not published on
     OHOS PC) — only src/ (lib + tools) is built and installed.
"""
import os
import shlex

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GpgmeConan(ConanFile):
    name = "gpgme"
    version = "1.24.0"
    description = "Library providing easy access to GnuPG for cryptographic operations"
    license = "LGPL-2.1-or-later"
    homepage = "https://gnupg.org/software/gpgme/"
    url = "https://git.gnupg.org/cgi-bin/gitweb.cgi?p=gpgme.git"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires(
            "libgpg-error/1.55",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libassuan/3.0.2",
            transitive_headers=True,
            transitive_libs=True,
        )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # config-overrides: correct the dependency config scripts / .la files #
    # ------------------------------------------------------------------ #
    def _co_dir(self):
        return os.path.join(self.build_folder, "config-overrides")

    def _create_config_overrides(self):
        lgp = self.dependencies["libgpg-error"].package_folder
        las = self.dependencies["libassuan"].package_folder
        co = self._co_dir()
        for d in ("bin", "lib/pkgconfig"):
            os.makedirs(os.path.join(co, d), exist_ok=True)

        bash = "/data/service/hnp/bin/bash"

        # 1) gpgrt-config wrapper: force bash (OHOS /bin/sh = mksh hangs).
        with open(os.path.join(co, "bin", "gpgrt-config"), "w") as f:
            f.write(
                "#!/bin/sh\n"
                f"exec {bash} {shlex.quote(os.path.join(lgp, 'bin', 'gpgrt-config'))} \"$@\"\n"
            )
        os.chmod(os.path.join(co, "bin", "gpgrt-config"), 0o755)

        # 2) libassuan-config wrapper: return correct flags (package .pc uses prefix=/).
        with open(os.path.join(co, "bin", "libassuan-config"), "w") as f:
            f.write(
                "#!/bin/sh\n"
                'case "$1" in\n'
                "  --version) echo 3.0.2 ;;\n"
                "  --api-version) echo 3 ;;\n"
                "  --host) echo aarch64-unknown-linux-ohos ;;\n"
                f"  --cflags) echo -I{os.path.join(las, 'include')} ;;\n"
                f"  --libs) echo -L{os.path.join(las, 'lib')} -lassuan "
                f"-L{os.path.join(lgp, 'lib')} -lgpg-error ;;\n"
                "  *) echo 3.0.2 ;;\n"
                "esac\n"
            )
        os.chmod(os.path.join(co, "bin", "libassuan-config"), 0o755)

        # 3) corrected gpg-error.pc (package .pc uses prefix=/ -> /lib, /include).
        pc_src = os.path.join(lgp, "lib", "pkgconfig", "gpg-error.pc")
        pc_dst = os.path.join(co, "lib", "pkgconfig", "gpg-error.pc")
        with open(pc_src, "r", encoding="utf-8") as f:
            text = f.read()
        text = text.replace("prefix=/", "prefix={}".format(lgp), 1)
        with open(pc_dst, "w", encoding="utf-8") as f:
            f.write(text)

        # 4) corrected .la files so libtool resolves dependency paths correctly.
        with open(os.path.join(co, "lib", "libgpg-error.la"), "w") as f:
            f.write(
                "# libgpg-error.la - a libtool library file\n"
                "# Generated by libtool (GNU libtool) 2.4.7\n"
                "# Fixed for OHOS: correct libdir/dependency_libs to conan package paths.\n"
                "dlname='libgpg-error.so.0'\n"
                "library_names='libgpg-error.so.0.39.3 libgpg-error.so.0 libgpg-error.so'\n"
                "old_library=''\n"
                "inherited_linker_flags=''\n"
                "dependency_libs=''\n"
                "weak_library_names=''\n"
                "current=39\nage=39\nrevision=3\n"
                "installed=yes\nshouldnotlink=no\n"
                "dlopen=''\ndlpreopen=''\n"
                "libdir='{}/lib'\n".format(lgp)
            )
        with open(os.path.join(co, "lib", "libassuan.la"), "w") as f:
            f.write(
                "# libassuan.la - a libtool library file\n"
                "# Generated by libtool (GNU libtool) 2.4.2\n"
                "# Fixed for OHOS: correct libdir/dependency_libs to conan package paths.\n"
                "dlname='libassuan.so.9'\n"
                "library_names='libassuan.so.9.0.2 libassuan.so.9 libassuan.so'\n"
                "old_library=''\n"
                "inherited_linker_flags=''\n"
                "dependency_libs=' -L{}/lib -lgpg-error -lpthread'\n".format(lgp) +
                "weak_library_names=''\n"
                "current=9\nage=0\nrevision=2\n"
                "installed=yes\nshouldnotlink=no\n"
                "dlopen=''\ndlpreopen=''\n"
                "libdir='{}/lib'\n".format(las)
            )
        return co

    def _build_env(self, co):
        """Environment for configure/make/install runs (applied on top of the
        default process env; conanbuild env is NOT applied)."""
        lgp = self.dependencies["libgpg-error"].package_folder
        las = self.dependencies["libassuan"].package_folder
        env = Environment()
        env.define("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        env.define("TMPDIR", self.build_folder)
        env.prepend_path("PATH", os.path.join(co, "bin"))
        # R33 + E001: 显式指定 CC/CXX（从 Conan toolchain 获取，避免 configure
        # 在 PATH 中探测到 gcc→clang 时链接失败——CI 环境实测
        # "checking for gcc... clang" 后 "C compiler cannot create executables"）。
        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        if tools.get("c"):
            env.define("CC", tools["c"])
        if tools.get("cpp"):
            env.define("CXX", tools["cpp"])
        env.define(
            "CPPFLAGS",
            "-I{} -I{}".format(os.path.join(lgp, "include"), os.path.join(las, "include")),
        )
        env.define(
            "LDFLAGS",
            "-L{} -L{} -L{}".format(
                os.path.join(co, "lib"), os.path.join(lgp, "lib"), os.path.join(las, "lib")
            ),
        )
        return env

    # ------------------------------------------------------------------ #
    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        AutotoolsDeps(self).generate()

    def _configure_args(self):
        args = [
            "./configure",
            "--prefix=/",
            "--libdir=/lib",
            "--includedir=/include",
            "--disable-nls",
            "--disable-doc",
            "--disable-werror",
            "--enable-languages=",
        ]
        if self.options.shared:
            args += ["--enable-shared", "--disable-static"]
        else:
            args += ["--disable-shared", "--enable-static"]
        args.append(
            "--with-libgpg-error-prefix={}".format(
                shlex.quote(self.dependencies["libgpg-error"].package_folder)
            )
        )
        return args

    def build(self):
        apply_conandata_patches(self)
        co = self._create_config_overrides()
        env = self._build_env(co)
        with env.vars(self).apply():
            self.run(" ".join(self._configure_args()), env=None, cwd=self.source_folder)
            # Only src/ — the tests/ tree requires a real `gpg` binary (GnuPG
            # runtime, unavailable on OHOS PC). Upstream tests documented in
            # notes.md / reports/test-report.md.
            self.run("make -C src -j1", env=None, cwd=self.source_folder)

    def package(self):
        co = self._co_dir()
        env = self._build_env(co)
        with env.vars(self).apply():
            self.run(
                "make -C src install DESTDIR={} -j1".format(shlex.quote(self.package_folder)),
                env=None,
                cwd=self.source_folder,
            )
        # Remove build-machine-specific libtool .la files.
        import glob

        for la in glob.glob(os.path.join(self.package_folder, "**", "*.la"), recursive=True):
            os.unlink(la)

    def package_info(self):
        self.cpp_info.libs = ["gpgme"]
        self.cpp_info.requires = [
            "libgpg-error::libgpg-error",
            "libassuan::libassuan",
        ]
        self.cpp_info.set_property("pkg_config_name", "gpgme")
        self.cpp_info.set_property("cmake_file_name", "gpgme")
        self.cpp_info.set_property("cmake_target_name", "gpgme::gpgme")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
