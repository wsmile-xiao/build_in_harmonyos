#!/usr/bin/env python3
"""Conan recipe — juise 3.0.0 (Autotools).

JUISE: The JUNOS User Interface Scripting Environment. Builds libjuise
(shared library) plus the juise and juise-askpass command-line tools.
Adapted to OpenHarmony PC (aarch64).

Deps (all published on ohpcd, verified W0):
  - libslax/3.1.6  (provides bin/slax-config; juise configure requires it)
  - libxml2/2.15.3
  - libxslt/1.1.45.2
  - libssh2/1.11.1 (configure PKG_CHECK_MODULES libssh2 is mandatory)
  - openssl/3.5.6.1 (AC_CHECK_LIB crypto MD5_Init; aligned with curl)

Notes:
  - mixer/clira are disabled by default (NEED_MIXER=no); only the core
    libjuise + juise + juise-askpass + juise-config are built.
  - config.guess/config.sub do not recognize HarmonyOS; patched to emit
    aarch64-unknown-linux-ohos (patch 0001).
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, check_sha256, copy, export_conandata_patches, get, unzip
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class JuiseConan(ConanFile):
    name = "juise"
    version = "3.0.0"
    description = "JUNOS User Interface Scripting Environment"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Juniper/juise"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"juise supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libslax/3.1.6")
        self.requires("libxml2/2.15.3")
        self.requires("libxslt/1.1.45.2")
        self.requires("libssh2/1.11.1")
        self.requires("openssl/3.5.6.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        staged = os.path.join(
            os.path.expanduser("~"), "Download", source["filename"]
        )
        if os.path.isfile(staged):
            check_sha256(self, staged, source["sha256"])
            unzip(
                self,
                staged,
                destination=self.source_folder,
                strip_root=True,
            )
        else:
            get(self, **source, strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()

        runtime_env = VirtualRunEnv(self).environment()
        tmpdir = os.path.join(self._build_root(), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        runtime_env.define("TMPDIR", tmpdir)
        runtime_env.vars(self, scope="build").save_script("juise_native_env")

        tc = AutotoolsToolchain(self)
        libslax = self.dependencies["libslax"].package_folder
        libxml2 = self.dependencies["libxml2"].package_folder
        libxslt = self.dependencies["libxslt"].package_folder
        libssh2 = self.dependencies["libssh2"].package_folder

        tc.configure_args.extend(
            [
                f"--with-libslax-prefix={libslax}",
                f"--with-libxml-prefix={libxml2}",
                # The conan libxml2 package's xml2-config hardcodes the
                # build-time prefix (/usr/local) and juise's configure invokes
                # it without --prefix, so its LIBXML_CFLAGS/LIBS point at the
                # nonexistent system paths.  These two options prepend the
                # conan paths (append semantics keep the config-script output
                # after ours), so the linker finds libxml2 in the package.
                f"--with-libxml-include-prefix={os.path.join(libxml2, 'include', 'libxml2')}",
                f"--with-libxml-libs-prefix={os.path.join(libxml2, 'lib')}",
                f"--with-libxslt-prefix={libxslt}",
                f"--with-ssh2={libssh2}",
                "--disable-clira",
                "--disable-mixer",
                "--disable-debug",
            ]
        )

        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])

        tc.generate()

    def _build_root(self):
        return "/data/storage/el2/base/.conan-build-juise-3.0.0"

    def build(self):
        apply_conandata_patches(self)

        root = self._build_root()
        work = os.path.join(root, "src")
        tmpdir = os.path.join(root, "tmp")

        if os.path.isdir(root):
            shutil.rmtree(root, ignore_errors=True)

        os.makedirs(work, exist_ok=True)
        os.makedirs(tmpdir, exist_ok=True)
        shutil.copytree(self.source_folder, work, dirs_exist_ok=True)

        # OHOS: bash 5.3 cannot getcwd() when $PWD is unset/mismatched —
        # the kernel returns EPERM for getcwd(2) here, and bash's fallback
        # walk needs read permission on root-owned 0711 ancestors, so the
        # conan-run bash wrapper dies with "getcwd: cannot access parent
        # directories".  Seeding $PWD makes bash skip getcwd entirely;
        # configure/make run under /bin/sh (mksh) which is unaffected.
        os.environ["PWD"] = work

        libslax = self.dependencies["libslax"].package_folder
        libxml2 = self.dependencies["libxml2"].package_folder
        libxslt = self.dependencies["libxslt"].package_folder
        libssh2 = self.dependencies["libssh2"].package_folder

        config_shell = shutil.which("sh") or "/bin/sh"
        cc_program = shutil.which("clang") or "/data/service/hnp/bin/clang"
        cxx_program = shutil.which("clang++") or "/data/service/hnp/bin/clang++"

        # NOTE: do NOT export LD_LIBRARY_PATH here — it shadows lld's libxml2
        # (clang ships its own RPATH for libxml2.so.16) and breaks configure
        # compile tests ("C compiler cannot create executables").
        #
        # On CI workers conanbuild.sh's LD_LIBRARY_PATH (all dep lib dirs,
        # including the conan libxml2 package) is inherited by configure's
        # conftest link step; lld loads that libxml2.so.16, whose symbol set
        # does not satisfy lld's own needs, so lld dies at startup
        # ("Error loading shared library libxml2.so.16 ... symbol not found")
        # and clang reports "linker command failed".  The local device lld
        # happens to use RPATH (searched before LD_LIBRARY_PATH) so it is
        # unaffected — unset LD_LIBRARY_PATH here so both environments use
        # lld's bundled libxml2.  The dep -L flags and -Wl,-rpath below keep
        # conftest/make links resolving the conan libraries.
        build_tool_env = (
            "CONFIG_SHELL="
            + shlex.quote(config_shell)
            + " SHELL="
            + shlex.quote(config_shell)
            + " CC="
            + shlex.quote(cc_program)
            + " CXX="
            + shlex.quote(cxx_program)
        )

        # juise configure needs libssh2/libxslt/libxml2/libslax pkg-config
        # metadata on PKG_CONFIG_PATH for PKG_CHECK_MODULES lookups.
        # libssh2.pc has `Requires: openssl`, so the openssl .pc files must
        # be reachable too.  generators_folder is the conan-generated .pc dir
        # (build_folder/conan) and carries the full Requires chain
        # (openssl-crypto/ssl); the dependency lib/pkgconfig dirs are added
        # as a fallback.
        openssl = self.dependencies["openssl"].package_folder
        pkg_config_path = os.pathsep.join(
            [self.generators_folder]
            + [
                os.path.join(p, "lib", "pkgconfig")
                for p in (libslax, libxml2, libxslt, libssh2, openssl)
            ]
        )

        configure_args = [
            "--prefix=/",
            "--bindir=/bin",
            "--sbindir=/bin",
            "--libdir=/lib",
            "--includedir=/include",
            f"--with-libslax-prefix={libslax}",
            f"--with-libxml-prefix={libxml2}",
            # conan libxml2's xml2-config reports /usr/local (build-time
            # prefix) and juise's configure calls it bare, so prepend the
            # conan include/lib paths via the append-semantics options.
            f"--with-libxml-include-prefix={os.path.join(libxml2, 'include', 'libxml2')}",
            f"--with-libxml-libs-prefix={os.path.join(libxml2, 'lib')}",
            f"--with-libxslt-prefix={libxslt}",
            f"--with-ssh2={libssh2}",
            "--disable-clira",
            "--disable-mixer",
            "--disable-debug",
        ]

        if self.options.shared:
            configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            configure_args.extend(["--disable-shared", "--enable-static"])

        # rpath every host dependency's lib dir (direct + transitive, e.g.
        # libslax pulls in curl) so that, with LD_LIBRARY_PATH unset,
        # configure's link-time probes and run-time conftest executions can
        # still resolve the conan shared libraries.
        dep_ldflags = " ".join(
            "-L"
            + shlex.quote(os.path.join(dep.package_folder, "lib"))
            + " -Wl,-rpath,"
            + os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep.package_folder
        )

        # The tarball ships a pre-generated configure; patch 0006 adds an
        # AC_CHECK_DECL([_res]) probe to configure.ac, so regenerate the
        # configure script with autoconf before running it.  autoconf alone
        # suffices: the tarball carries aclocal.m4 (AM_*/LT_* macros) and
        # LT_INIT's ltmain.sh is left untouched; the config.guess/config.sub
        # changes from patch 0001 live in separate scripts (not embedded in
        # configure) and survive the regeneration.
        self.run(build_tool_env + " autoconf", cwd=work)

        # Applying patch 0006 bumps configure.ac's mtime past the shipped
        # aclocal.m4 / Makefile.in, so make would fire the maintainer rules
        # and try to rebuild them via aclocal/automake — perl-based tools
        # that are absent on the device ("Error 127").  Pin configure.ac's
        # mtime back to aclocal.m4's (equal mtimes do not trigger make's
        # out-of-date check); configure was just regenerated by autoconf and
        # is newer than both, so it stays put too.
        self.run("touch -r aclocal.m4 configure.ac", cwd=work)

        try:
            self.run(
                "unset LD_LIBRARY_PATH; "
                "PKG_CONFIG_PATH="
                + shlex.quote(pkg_config_path)
                + build_tool_env
                + " CPPFLAGS=\"$CPPFLAGS\" LDFLAGS=\"$LDFLAGS "
                + dep_ldflags
                + "\" ./configure "
                + " ".join(shlex.quote(arg) for arg in configure_args),
                cwd=work,
            )
        except Exception:
            config_log = os.path.join(work, "config.log")
            if os.path.isfile(config_log):
                print("===== BEGIN config.log =====")
                with open(config_log, "r", errors="replace") as f:
                    print(f.read())
                print("===== END config.log =====")
            raise
        self.run("unset LD_LIBRARY_PATH; " + build_tool_env + " make -j1", cwd=work)

    def package(self):
        root = self._build_root()
        work = os.path.join(root, "src")
        install_dir = os.path.join(root, "install")

        if os.path.isdir(install_dir):
            shutil.rmtree(install_dir, ignore_errors=True)
        os.makedirs(install_dir, exist_ok=True)

        cc_program = shutil.which("clang") or "/data/service/hnp/bin/clang"
        clang_real = os.path.realpath(cc_program)
        llvm_root = os.path.dirname(os.path.dirname(clang_real))
        llvm_lib = os.path.join(llvm_root, "lib")
        llvm_libxml = os.path.join(llvm_lib, "libxml2.so.16")

        install_env = ""
        if os.path.isfile(llvm_libxml):
            install_env = (
                "LD_LIBRARY_PATH="
                + shlex.quote(llvm_lib)
                + ":${LD_LIBRARY_PATH:-} "
            )

        self.run(
            install_env
            + "make install DESTDIR="
            + shlex.quote(install_dir),
            cwd=work,
        )
        shutil.copytree(
            install_dir, self.package_folder, dirs_exist_ok=True, symlinks=True
        )
        for dirpath, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                if filename.endswith(".la"):
                    os.remove(os.path.join(dirpath, filename))

        # juise's install-exec-hook registers the libjuise extension with
        # libslax via SLAX_EXTDIR, which resolves to the libslax package's
        # absolute cache path.  Under DESTDIR that materializes a
        # <package>/storage/... tree of symlinks that pollutes the package
        # with machine-specific paths — strip it; the extension registration
        # belongs to the libslax runtime, not to the juise artifact.
        leaked = os.path.join(self.package_folder, "storage")
        if os.path.isdir(leaked):
            shutil.rmtree(leaked, ignore_errors=True)

        # NOTE: bin/juise keeps the libtool build-dir RUNPATH (.libs).  Do
        # NOT patchelf it — rewriting the ELF makes OHOS refuse to exec the
        # binary ("Operation not permitted"); and the stale RUNPATH is
        # harmless in the conan runtime since VirtualRunEnv's
        # LD_LIBRARY_PATH (conanrun.sh) takes precedence at load time.

        copy(
            self,
            "Copyright",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["juise"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "juise")
