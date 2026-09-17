#!/usr/bin/env python3
"""Conan recipe for liblastlog2 2.42.2 - the Y2038-safe lastlog library.

Builds ONLY the liblastlog2 shared/static library (SQLite3 backend) from the
full util-linux source tree.  All programs and all other libraries are
disabled via --disable-all-programs; liblastlog2 itself must be re-enabled
explicitly because the global switch also flips its own default state to
"no" (configure.ac: UL_DEFAULT_ENABLE([liblastlog2], [check])).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class Liblastlog2Conan(ConanFile):
    name = "liblastlog2"
    version = "2.42.2"
    description = "Y2038-safe lastlog library with SQLite3 backend from util-linux"
    license = "BSD-2-Clause"
    homepage = "https://github.com/util-linux/util-linux"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def requirements(self):
        self.requires("sqlite3/3.49.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "liblastlog2 requires a POSIX environment with sqlite3"
            )

    def source(self):
        data = self.conan_data["sources"][self.version]
        urls = data["url"]
        if isinstance(urls, str):
            urls = [urls]
        else:
            urls = list(urls)
        # cdn.kernel.org occasionally times out on the CI worker
        # (ConanConnectionError: Read timed out).  Append official kernel.org
        # mirrors; get() enforces the same sha256 for every candidate.
        for mirror in (
            "https://mirrors.edge.kernel.org/pub/linux/utils/util-linux/v2.42/util-linux-2.42.2.tar.xz",
            "https://www.kernel.org/pub/linux/utils/util-linux/v2.42/util-linux-2.42.2.tar.xz",
        ):
            if mirror not in urls:
                urls.append(mirror)
        get(self, urls, sha256=data["sha256"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Disable ALL programs first, then re-enable liblastlog2 (the global
        # switch also disables it, so an explicit --enable-liblastlog2 is
        # mandatory).  Verify in the configure summary that
        # "lastlog2 support: yes"; sqlite3 probing failure would silently
        # disable the library otherwise.
        tc.configure_args.append("--disable-all-programs")
        tc.configure_args.append("--enable-liblastlog2")
        tc.configure_args.append("--disable-pam-lastlog2")
        # Static is required by the upstream check tests: BUILD_LIBLASTLOG2_TESTS
        # needs enable_static=yes and the test programs link with -static.
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
        else:
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        # Disable optional features that are not needed
        tc.configure_args.append("--without-systemd")
        tc.configure_args.append("--without-selinux")
        tc.configure_args.append("--without-audit")
        tc.configure_args.append("--disable-bash-completion")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-plymouth-support")
        tc.configure_args.append("--without-cap-ng")
        tc.configure_args.append("--without-utempter")
        tc.configure_args.append("--disable-makeinstall-chown")
        tc.configure_args.append("--disable-makeinstall-setuid")
        # PKG_CHECK_MODULES([SQLITE3], [sqlite3]) honours the SQLITE3_CFLAGS /
        # SQLITE3_LIBS environment variables before falling back to a
        # pkg-config lookup, so the sqlite3 detection succeeds even though the
        # Conan package does not ship a sqlite3.pc.  Must be defined on the
        # toolchain environment snapshot BEFORE tc.generate().
        sqlite3_dep = self.dependencies["sqlite3"]
        sqlite3_inc = os.path.join(
            sqlite3_dep.package_folder, sqlite3_dep.cpp_info.includedirs[0])
        sqlite3_lib = os.path.join(
            sqlite3_dep.package_folder, sqlite3_dep.cpp_info.libdirs[0])
        env = tc.environment()
        env.define("SQLITE3_CFLAGS", "-I%s" % sqlite3_inc)
        env.define("SQLITE3_LIBS", "-L%s -lsqlite3" % sqlite3_lib)
        tc.generate(env)
        # AutotoolsDeps exports the sqlite3 include/lib paths into
        # CPPFLAGS/LDFLAGS: liblastlog2/src/lastlog2.c includes <sqlite3.h>
        # directly and liblastlog2_la_CFLAGS never consumes $(SQLITE3_CFLAGS).
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # E011: autoconf configure/config.status create temp dirs (confXXXXXX)
        # with umask 077; on OHOS HMDFS such 0700 dirs get force-downgraded and
        # become unwritable -> replace with umask 022.
        for fname in ("configure",):
            fpath = os.path.join(self.source_folder, fname)
            if os.path.isfile(fpath):
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                if "umask 077" in text:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(text.replace("umask 077", "umask 022"))
        # Pre-create a writable TMPDIR and inject it so config.status child
        # processes inherit it.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Upstream test suite for this package: the 7 check_PROGRAMS
        # (test_lastlog2_*) compiled -static, plus the official tests/run.sh
        # harness over the liblastlog2 component (run.sh [<component> ...] is
        # the upstream TESTS_COMPONENTS mechanism).  Two OHOS-only adaptations
        # of the invocation, not of the tests:
        #  - the upstream `make check` target also builds every other
        #    component's check_PROGRAMS; lib/test_netlink.c does not compile
        #    against the musl/OHOS sysroot (linux/socket.h redefines
        #    sockaddr_storage), so the component programs are built by name;
        #  - the harness driver pipes scripts through `xargs -I ... -P ...`,
        #    but the toybox xargs first on the OHOS PATH lacks -I, so a shim
        #    directory mapping `xargs` to the busybox applet (which supports
        #    -I/-P and is already on the toolchain PATH) is prepended.
        test_progs = " ".join(
            "test_lastlog2_" + name
            for name in (
                "dlopen",
                "pam_lastlog2_output",
                "remove_entry",
                "rename_user",
                "write_read_user",
                "y2038_ll2_read_all",
                "y2038_sqlite3_time",
            )
        )
        self.run("make %s" % test_progs, env="conanbuild")
        path_prefix = ""
        busybox = shutil.which("busybox")
        if busybox:
            xargs_shim = os.path.join(self.build_folder, "ohos-xargs-shim")
            os.makedirs(xargs_shim, exist_ok=True)
            xargs_link = os.path.join(xargs_shim, "xargs")
            if not os.path.lexists(xargs_link):
                try:
                    os.symlink(busybox, xargs_link)
                except OSError:
                    pass
            if os.path.lexists(xargs_link):
                path_prefix = 'PATH="%s:$PATH" ' % xargs_shim
            else:
                self.output.warning("xargs shim unavailable for tests/run.sh")
        runsh = os.path.join(self.source_folder, "tests", "run.sh")
        self.run(
            '%sbash "%s" --srcdir="%s" --builddir="%s" '
            "--nonroot --show-diff --parallel liblastlog2"
            % (path_prefix, runsh, self.source_folder, self.build_folder),
            env="conanbuild",
        )

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove libtool archives (absolute build paths, no consumer value).
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            rm(self, "*.la", lib_dir)

    def package_info(self):
        # Upstream lastlog2.pc sets Cflags: -I${includedir}/liblastlog2, so
        # consumers do #include <lastlog2.h>.
        self.cpp_info.includedirs = ["include/liblastlog2"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["lastlog2"]
        # Match the official pkg-config/module names (lastlog2.pc,
        # meson.override_dependency("lastlog2")).
        self.cpp_info.set_property("pkg_config_name", "lastlog2")
        self.cpp_info.set_property("cmake_file_name", "lastlog2")
        self.cpp_info.set_property("cmake_target_name", "lastlog2::lastlog2")
