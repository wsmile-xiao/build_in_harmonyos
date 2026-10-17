#!/usr/bin/env python3
"""Conan recipe — scws 1.2.3 (autotools)

SCWS (Simple Chinese Word Segmentation) is a mechanical Chinese word
segmentation engine by hightman (xunsearch project): a C library
(libscws) plus two CLI tools (scws / scws-gen-dict).

HarmonyOS PC adaptation notes:
  - No source-level C changes are needed; the port is limited to the
    autotools platform-recognition layer:
      0001-config.guess-harmonyos.patch  config.guess learns the
        *:HarmonyOS:*:* uname triple reported by OHOS PC workers
        (maps to <machine>-unknown-linux-ohos).
      0002-config.sub-linux-ohos.patch   config.sub validates the
        linux-ohos OS family (both aarch64-linux-ohos and the
        canonical aarch64-unknown-linux-ohos forms).
      0003-configure-umask-022.patch     config.status tmp dir uses
        umask 022 (HMDFS always sets the setgid bit on new dirs;
        umask 077 yields drwx--S--- which blocks even the owner, so
        config.status fails with "could not setup config files
        machinery" on the OHOS CI worker).
  - --host=aarch64-unknown-linux-ohos is passed explicitly: the
    vendor-less form would leave host_os=ohos, which misses libtool's
    `linux*)` shared-library branch and silently produces no .so
    (see archives/l/libopendbx/1.4.6 notes; knowledge E072/E122/E268).
  - Runtime autoconf probes (AC_FUNC_MMAP, AC_FUNC_MEMCMP,
    AC_FUNC_LSTAT*) cannot execute under a cross build; the cache
    results are pinned to the values a native OHOS configure detects
    (OHOS/musl provides working mmap, memcmp and POSIX lstat), keeping
    the local cross build bit-identical in behaviour to the CI native
    build. HAVE_MMAP in particular selects the mmap-backed dictionary
    reader in libscws/xdb.c.

Upstream ships one auto-test script, phpext/scws_test.php (17 data
cases: input text + multi/ignore/duality options + expected segmented
output). It is not wired into `make check` (no such target exists) and
needs a PHP + php-scws extension host, which is out of scope here; the
17 cases are therefore replayed verbatim through the public C API in
test_package/upstream_test.c (see test_package/MANIFEST.yml for the
counting convention).

 --enable-namerule is required for the upstream cases to reproduce:
without people/road-name recognition the reference outputs for
"马明练" / "李姚明" cannot be reached. The official simplified-Chinese
dictionary (scws-dict-chs-utf8.tar.bz2, the same release the upstream
PHP test loads) is fetched as a second source and installed under
share/scws/ so both the test suite and downstream users have it.
"""
from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                                export_conandata_patches, get)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class ScwsConan(ConanFile):
    name = "scws"
    version = "1.2.3"
    description = "SCWS — Simple Chinese Word Segmentation engine (libscws C library + scws/scws-gen-dict CLI)"
    license = "BSD-2-Clause"
    homepage = "http://www.xunsearch.com/scws/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Official simplified-Chinese dictionary (separate upstream
        # release; the source tarball itself ships no .xdb dictionary).
        # That tarball holds a single root-level file, so strip_root must
        # stay disabled.
        get(self, **self.conan_data["dict"], strip_root=False,
            destination=self.source_folder)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # People/road-name recognition: required by the upstream test
        # cases (phpext/scws_test.php expects 马明练 / 李姚明 to segment
        # as names).
        tc.configure_args.append("--enable-namerule")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        if self.settings.os == "OHOS":
            # Keep the vendor field: aarch64-linux-ohos canonicalizes to
            # host_os=ohos which misses libtool's linux*) shared branch;
            # aarch64-unknown-linux-ohos yields host_os=linux-ohos.
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
            native_sim = self.conf.get("user.build:flex_bison_native",
                                       default=False)
            if self.settings_build.os == "OHOS" and not native_sim:
                # CI worker: native OHOS build (build == host, configure
                # may execute its runtime probes).
                tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
            else:
                # Cross build (macOS dev box, either with a separate macOS
                # build profile or with the OHOS-settings simulation profile
                # flagged via user.build:flex_bison_native): the runtime
                # probes cannot run, so pin the cache results to the values
                # a native OHOS configure detects (musl: working mmap,
                # memcmp, POSIX lstat without trailing-slash/empty-string
                # bugs). This keeps cross-built packages identical in
                # behaviour to CI-built ones (HAVE_MMAP selects the
                # mmap-backed xdb dictionary reader). --build pins a
                # triplet the bundled 2014 config.sub understands so
                # configure enters cross mode and skips run-time probes.
                tc.configure_args.append("--build=x86_64-apple-darwin")
                # libtool's LT_PATH_LD asks the compiler driver for its
                # linker; the cross wrapper resolves that to the macOS
                # /usr/bin/ld, which leaves libtool's archive_cmds EMPTY
                # (with_gnu_ld=no) — the .so is silently never created and
                # only the symlinks appear. ld.lld reports "compatible with
                # GNU linkers", so pointing LD at it yields the correct
                # GNU-style archive_cmds. ld.lld/llvm-ar/llvm-ranlib are on
                # PATH via the ohos-local profile's buildenv.
                tc.configure_args.extend([
                    "LD=ld.lld",
                    "AR=llvm-ar",
                    "RANLIB=llvm-ranlib",
                    "ac_cv_func_mmap_fixed_mapped=yes",
                    "ac_cv_func_memcmp_working=yes",
                    "ac_cv_func_lstat_dereferences_slashed_symlink=yes",
                    "ac_cv_func_lstat_empty_string_bug=no",
                ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Upstream has no test suite (no make check target); consumer
        # verification lives in test_package/.

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Install the official dictionary alongside the package so that
        # consumers (and the upstream-case replay in test_package) can do
        # scws_set_dict("<pkg>/share/scws/dict.utf8.xdb", SCWS_XDICT_XDB).
        copy(self, "dict.utf8.xdb",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "scws"))
        # Drop libtool .la files and (macOS-only) .dylib artifacts.
        for root, _dirs, files in os.walk(self.package_folder):
            for f in files:
                if f.endswith(".la") or f.endswith(".dylib"):
                    os.unlink(os.path.join(root, f))

    def package_info(self):
        # Headers install to include/scws/*.h; consumers use
        # #include <scws/scws.h> via the default "include" root.
        self.cpp_info.libs = ["scws"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
