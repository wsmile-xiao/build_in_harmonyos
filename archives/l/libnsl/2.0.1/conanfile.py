# conanfile.py - libnsl 2.0.1
# HarmonyOS PC adaptation (OHOS 6.0 / aarch64 / musl / clang 15, native build).
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                            get, replace_in_file, rm)
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps

required_conan_version = ">=1.52.0"


class LibnslConan(ConanFile):
    name = "libnsl"
    version = "2.0.1"
    description = "Public client interface for NIS(YP) and NIS+ in an IPv6 ready version"
    homepage = "https://github.com/thkukuk/libnsl"
    license = "LGPL-2.1-or-later"
    url = "https://github.com/thkukuk/libnsl"
    topics = ("nis", "yp", "rpc", "tirpc")

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "conandata.yml", "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Pure C library: the C++ only settings are meaningless here.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def requirements(self):
        # libnsl 2.x is a TI-RPC client: every RPC/XDR primitive (xdr_*,
        # clnt_create, netconfig) lives in libtirpc, never in the system libc.
        # configure.ac: PKG_CHECK_MODULES([TIRPC], [libtirpc]) +
        # AC_DEFINE(HAVE_TIRPC); without a resolvable libtirpc.pc the package
        # silently degrades to a stub library, so this is a hard requires().
        self.requires("libtirpc/1.3.7")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], destination=self.source_folder, strip_root=True)

    def layout(self):
        # Autotools project: configure/make run in the source tree.
        pass

    def generate(self):
        # Emits libtirpc.pc into the generators folder.
        deps = PkgConfigDeps(self)
        deps.generate()
        # AutotoolsToolchain still owns the compiler/flag/PKG_CONFIG_PATH
        # environment (applied by the `conanbuild` env). Its configure()
        # helper is deliberately not used, see build().
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _relax_configure_temp_umask(self):
        """
        HMDFS/setgid portability: autoconf's `configure` creates its scratch
        directory with `(umask 077 && mktemp -d ./confXXXXXX)`. On the OHOS
        hmfs/hmdfs mount a 0700 directory created below a setgid directory is
        not writable by the very next process, so `config.status` dies with:

            ./config.status[NNNN]: can't create ./confXXXXXX/subs1.awk: Permission denied
            config.status: error could not setup config files machinery

        Relaxing the scratch-dir umask to 022 fixes it. Same treatment as the
        merged gmime/3.0.6 recipe (in-build umask handling) and the
        classads/1.0.10 patches/0002-configure.patch.
        """
        if str(self.settings.os) != "OHOS":
            return
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            replace_in_file(self, cfg, "umask 077", "umask 022", strict=False)

    def build(self):
        """
        Configure + build libnsl.

        Two HarmonyOS PC portability constraints force an explicit
        ``configure`` invocation here instead of ``Autotools.configure()``:

        1. ``CONFIG_SHELL`` must be ``/bin/sh``.
           libnsl ships an autoconf 2.69 ``configure``. Autoconf probes the
           shell that started it; if that shell lacks the bash-isms it needs it
           scans ``/bin``, ``/usr/bin``, ``$PATH`` for the first of
           ``sh bash ksh sh5`` and re-executes itself with it. On HarmonyOS PC
           ``/bin/sh`` fails that probe, so autoconf re-execs through ``bash``,
           and bash cannot resolve a non-root working directory
           (``pwd``/``getcwd()`` fail with EACCES/ENOTSUP on the hmfs/hmdfs
           mount). The re-executed configure then dies immediately:
               ac_pwd=`pwd` && test -n "$ac_pwd" && ... ||
                 as_fn_error $? "working directory cannot be determined"
           ``/bin/sh`` has no such defect and autoconf honours a pre-set
           CONFIG_SHELL, skipping the search and the re-exec. The profile's
           ``[buildenv]`` exports ``CONFIG_SHELL=/data/service/hnp/bin/bash``,
           and ``ConanFile.run()`` always wraps commands with that aggregated
           ``conanbuild`` env, so an inline command-prefix assignment is the
           only injection point that wins.
           Matches knowledge drafts DRAFT-E551 / DRAFT-6487.

        2. The bundled ``config.guess`` (GNU Autoconf 2.69, 2015) does not
           recognise ``uname -s`` = ``HarmonyOS`` and aborts with
           ``configure: error: cannot guess build type; you must specify one``.
           An explicit native GNU triplet (``--build`` == ``--host``) skips
           config.guess/config.sub entirely; the compiler still comes from the
           profile's ``tools.build:compiler_executables`` (OHOS clang), and the
           platform branch is taken as Linux. Matches the classads/1.0.10 and
           cityhash/1.1.1 precedent. (Alternative: re-anchor a config.guess/
           config.sub portability patch, see DRAFT-E564.)

        The command also ``cd``s into the source tree instead of passing
        ``cwd=``: on HMDFS a conan-provided cwd triggers a getcwd storm in the
        child shell, while an internal ``cd`` tracks PWD and avoids it
        (DRAFT-6487).
        """
        apply_conandata_patches(self)
        self._relax_configure_temp_umask()
        src = self.source_folder
        shared_flag = ("--enable-shared --disable-static" if self.options.shared
                       else "--disable-shared --enable-static")
        self.run(
            f'cd "{src}" && umask 022 && '
            f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
            # PkgConfigDeps writes libtirpc.pc into the generators folder.
            f'PKG_CONFIG_PATH="{self.generators_folder}'
            f'${{PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}}" '
            f'sh "./configure" '
            f"--prefix=/ "
            f"'--bindir=${{prefix}}/bin' '--sbindir=${{prefix}}/bin' "
            f"'--libdir=${{prefix}}/lib' '--includedir=${{prefix}}/include' "
            f"'--oldincludedir=${{prefix}}/include' "
            f"--build=aarch64-unknown-linux-gnu "
            f"--host=aarch64-unknown-linux-gnu "
            f"{shared_flag} --disable-nls --disable-dependency-tracking",
            env="conanbuild",
        )
        self.run(f'cd "{src}" && make -j1', env="conanbuild")
        # Upstream libnsl 2.0.1 ships NO test suite: no TESTS/check_PROGRAMS in
        # any Makefile.am and no test directory in the release tarball, so there
        # is nothing to execute here. Evidence recorded in
        # test_package/MANIFEST.yml.

    def package(self):
        src = self.source_folder
        # Autotools.install() uses DESTDIR, which is why configure is given
        # --prefix=/ above on purpose.
        self.run(f'cd "{src}" && make -j1 install DESTDIR="{self.package_folder}"',
                 env="conanbuild")
        copy(self, "COPYING", src=src, dst=os.path.join(self.package_folder, "licenses"))
        # libtool archives leak build paths and are useless to consumers.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libnsl")
        self.cpp_info.libs = ["nsl"]
        # libnsl's public headers are not self-contained: rpcsvc/yp_prot.h
        # includes <rpc/rpc.h> and the taddr2*() API uses struct netconfig /
        # struct netbuf, all of which live in libtirpc (installed under
        # include/tirpc). Declaring the requirement is what makes ConanDeps
        # propagate those include dirs to consumers; without it a consumer
        # fails with "fatal error: 'rpc/rpc.h' file not found".
        self.cpp_info.requires = ["libtirpc::libtirpc"]
