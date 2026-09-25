#!/usr/bin/env python3
"""Conan recipe for siril 1.2.3 — astronomy image processing GUI application.

siril (Siril) is a free astronomy image-processing software (GTK3 GUI +
siril-cli command line interface). Built with autotools from the official
GitLab tag-1.2.3 tarball.

Dependencies published on ohpcd are consumed as binaries (pure refs, no
user/channel). Trimmed from the upstream feature set (recorded in notes.md):
  - ffms2: AVI importer (not published on ohpcd)
  - json-glib: automatic-update check (published binary is pinned to
    glib/2.84.0 while gtk/3.24.38 needs glib/2.84.0.1 → cannot be part of a
    binary-only graph; feature is optional upstream anyway)
  - librtprocess: submodule is empty in the release tarball; made optional
    via HAVE_LIBRTPROCESS guards (patches 0003/0004/0005)
  - intltool: not available on OHOS; replaced with msgfmt-based po handling
    (patch 0001 + po/Makefile.am generated in source())

OHOS adaptations:
  - config.status umask 077 → 022 (HMDFS setgid permission issue)
  - OPENCV_LIBS resolved via pkg-config opencv4 instead of hardcoded libs
  - LIBHEIF/LIBRAW/EXIV2 CFLAGS added to AM_CPPFLAGS (upstream omission)
  - -lintl added for glib proxy gettext on OHOS
  - gio-unix-2.0.pc generated manually (conan glib doesn't declare it)
  - CI worker sandbox cannot EXECUTE host automake/aclocal (user-local
    install is not accessible to the sandbox user; SDK ships no automake)
    → the pre-generated autotools output (configure/aclocal.m4/config.h.in/
    every Makefile.in + aux scripts) ships inside the augmented release
    tarball (mirror/siril/1.2.3/siril-1.2.3-ohos-autotools.tar.bz2, see
    conandata.yml), downloaded and extracted in source(), so the recipe
    skips autoreconf on
    CI (the
    autoreconf fallback remains for dev hosts with a working automake)
"""
import json
import os
import shutil
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
    save, load, chmod, copy,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps, AutotoolsDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class SirilConan(ConanFile):
    name = "siril"
    version = "1.2.3"
    description = ("Siril is a free, open source astronomy image-processing "
                   "software for pre-processing and post-processing of "
                   "astronomical images (GUI + CLI)")
    license = "GPL-3.0-or-later"
    homepage = "https://free-astro.org/index.php/Siril"
    url = "https://gitlab.com/free-astro/siril"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # 上游单元测试运行器：build() 真实编译并运行 src/tests/ 的 11 个测试，
        # 输出 HMBS_UPSTREAM_TEST_RESULT 机器证据。
        copy(self, "tests/upstream_tests.sh", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def requirements(self):
        # siril configure.ac mandatory pkg-config deps:
        self.requires("gtk/3.24.38")      # gtk+-3.0 (brings glib/gio/cairo)
        self.requires("gsl/2.8")           # gsl
        self.requires("fftw3f/3.3.10")     # fftw3f
        self.requires("cfitsio/4.6.4")     # cfitsio
        self.requires("opencv/4.12.0")     # opencv4 >= 4.2
        # Optional published deps enabled for upstream feature parity:
        self.requires("exiv2/0.28.7")
        self.requires("libraw/0.22.1")
        self.requires("wcslib/8.4")
        self.requires("libheif/1.22.2")
        self.requires("libtiff/4.7.2")
        self.requires("libjpeg/10")
        self.requires("libpng/1.6.58")
        self.requires("libcurl/8.5.0")
        self.requires("lcms2/2.19")
        self.requires("libde265/1.0.18")

    def build_requirements(self):
        # 上游单元测试（src/tests/ 中 imoper/soper/photometry/rejection/sorting）
        # 依赖 Criterion。tool_requires 放入 build 上下文，不会进入 host 上下文
        # AutotoolsDeps 生成的链接参数，避免 -lcriterion 等污染主程序链接行。
        self.tool_requires("criterion/2.4.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # intltool absent on OHOS → provide a msgfmt-based po/Makefile.am.
        # Must be in place BEFORE autoreconf, else automake fails with
        # "required file 'po/Makefile.in' not found".
        po_makefile = (
            "localedir = $(datadir)/locale\n"
            "MSGFMT = msgfmt\n"
            ".po.gmo:\n"
            "\t$(MSGFMT) -o $@ $<\n"
            "all-local:\n"
            "\t@true\n"
            "install-data-local:\n"
            "\t@true\n"
            "clean-local:\n"
            "\t@true\n"
            "EXTRA_DIST = LINGUAS POTFILES.in\n"
        )
        save(self, os.path.join(self.source_folder, "po", "Makefile.am"),
             po_makefile)
        # The augmented release tarball already ships a pre-generated
        # po/Makefile.in built from the msgfmt-based Makefile.am above; CI has
        # no automake and skips autoreconf, so deleting it here would make
        # configure fail with "cannot find input file: 'po/Makefile.in'".
        # Only drop a genuinely intltool-generated po/Makefile.in (upstream
        # flavour) so a dev-host autoreconf can rebuild it cleanly from the
        # Makefile.am above.
        po_in = os.path.join(self.source_folder, "po", "Makefile.in")
        if os.path.exists(po_in):
            content = load(self, po_in)
            if "intltool" in content:
                os.remove(po_in)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # R26: this is an application; keep its configure consistent with the
        # published dep binaries (shared=False is the OHOS binary default).
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")

        # R29: conftest test programs cannot be EXECUTED on this OHOS host
        # (conan dep .so live under HMDFS paths that the runtime loader never
        # searches → "./conftest" aborts with "cannot run C compiled
        # programs").  Pass the GNU triplets explicitly with host != build so
        # autoconf enables cross mode and skips running every conftest; the
        # env's config.guess/config.sub (autoconf 2.72/automake 1.16, OHOS
        # aware) already accept *-linux-ohos.  Same pattern as the asterisk
        # family (asterisk-srtp, asterisk-speex) and the abiword plugins.
        tc.configure_args.append("--build=x86_64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")

        # Deps without pkg-config metadata (libjpeg, libde265) and those whose
        # configure probes need raw include/lib dirs must be reachable.  Also
        # make sure every dep package folder's lib/pkgconfig + bin are on the
        # search path (gdk-3.0.pc etc. ship inside gtk's own package).
        inc_flags, lib_flags = [], []
        env = Environment()
        for _, dep in self.dependencies.items():
            pf = getattr(dep, "package_folder", None)
            if not pf:
                continue
            cpp = dep.cpp_info
            for d in cpp.includedirs:
                p = d if os.path.isabs(d) else os.path.join(pf, d)
                if os.path.isdir(p):
                    inc_flags.append(f"-I{p}")
            for d in cpp.libdirs:
                p = d if os.path.isabs(d) else os.path.join(pf, d)
                if os.path.isdir(p):
                    lib_flags.append(f"-L{p}")
                    env.append_path("LD_LIBRARY_PATH", p)
                    env.append_path("PKG_CONFIG_PATH",
                                    os.path.join(p, "pkgconfig"))
            env.append_path("PATH", os.path.join(pf, "bin"))
        # AutotoolsToolchain.extra_cflags/extra_cxxflags/extra_ldflags are
        # lists of individual flags (Conan 2 API), NOT space-joined strings.
        if inc_flags:
            tc.extra_cflags = list(inc_flags)
            tc.extra_cxxflags = list(inc_flags)
        if lib_flags:
            tc.extra_ldflags = list(lib_flags)

        # R31: siril calls ngettext(), which glib's gi18n headers rename to
        # g_libintl_ngettext.  That symbol only exists in the glib package's
        # own built-in libintl (glib-2.0.pc emits `-lintl`, but which
        # libintl.so that resolves to depends on the -L search order: on the
        # CI worker it picks up the gettext package's libintl, which exports
        # plain `ngettext` without the g_libintl_* prefixed symbols → link
        # fails with "undefined symbol: g_libintl_ngettext").  Link the glib
        # package's libintl.so by full path so the g_libintl_* symbols are
        # always provided regardless of the environment's -L ordering.
        for _, dep in self.dependencies.items():
            if str(dep.ref).startswith("glib/"):
                pf = getattr(dep, "package_folder", None)
                if pf:
                    intl_so = os.path.join(pf, "lib", "libintl.so")
                    if os.path.isfile(intl_so):
                        tc.extra_ldflags.append(intl_so)
                break

        env.vars(self).save_script("conan_dep_paths")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # gio-unix-2.0.pc: siril configure.ac PKG_CHECK_MODULES(GIO, gio-2.0
        # gio-unix-2.0 ...). Conan glib exposes gio-2.0 but not a separate
        # gio-unix-2.0 component → generate it against the real glib package.
        glib_root = None
        glib_ver = "0.0"
        for _, dep in self.dependencies.items():
            if str(dep.ref).startswith("glib/"):
                glib_root = getattr(dep, "package_folder", None)
                glib_ver = str(dep.ref.version)
                break
        if glib_root:
            gio_unix_pc = (
                f"prefix={glib_root}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "includedir1=${prefix}/include/glib-2.0\n"
                "includedir2=${prefix}/lib/glib-2.0/include\n"
                "includedir3=${prefix}/include/gio-unix-2.0\n"
                "\n"
                f"Name: gio-unix-2.0\n"
                "Description: Conan component: gio-unix-2.0 (Unix GIO)\n"
                f"Version: {glib_ver}\n"
                'Libs: -L"${libdir}" -lgio-2.0 -lm -lpthread -ldl\n'
                'Cflags: -I"${includedir}" -I"${includedir1}" '
                '-I"${includedir2}" -I"${includedir3}"\n'
                "Requires: glib-2.0 gobject-2.0 gmodule-2.0\n"
            )
            save(self, os.path.join(self.generators_folder,
                                    "gio-unix-2.0.pc"), gio_unix_pc)

        # Pre-generated autotools output (configure/aclocal.m4/config.h.in/
        # every Makefile.in + aux scripts) ships inside the augmented release
        # tarball (siril-1.2.3-ohos-autotools.tar.bz2, see conandata.yml) and
        # is already extracted at the right relative paths in the source tree.
        # The CI worker
        # sandbox cannot EXECUTE the host automake/aclocal at all ("Can't exec
        # aclocal: No such file or directory" — the user-local automake install
        # is not readable by the sandbox user and the SDK ships no automake),
        # so autoreconf is impossible there.  Unify timestamps and skip autoreconf.
        # configure is executed from the build_folder copy (conan copies
        # source→build before build() and preserves mtimes), so the enhanced
        # tarball's configure mtime (packaging time, possibly in the future
        # relative to the CI worker clock) would trip configure's sanity
        # check unless the build copy is pinned too.  Unify timestamps on
        # BOTH trees.
        roots = tuple(r for r in (self.source_folder, self.build_folder)
                      if os.path.exists(os.path.join(r, "configure")))
        if roots:
            # automake's generated Makefile.in carry maintainer rules that
            # rebuild aclocal.m4/configure/Makefile.in whenever their deps
            # (configure.ac, Makefile.am) are newer.  The patches above bump
            # those deps, so make would otherwise re-run aclocal (broken here
            # and in CI).  Give every generated file the SAME explicit
            # timestamp and pin the patch-affected *source* files to the past,
            # so generated files are strictly newer than their sources no
            # matter how coarse the CI worker's 0.01s timestamp resolution is.
            # NOTE: a *future* timestamp also satisfies the maintainer rules
            # but trips configure's sanity check ("newly created file is older
            # than distributed files!") — configure compares $srcdir/configure
            # against a file created *during* the configure run, so generated
            # files must not be newer than that.
            now = time.time()
            past = now - 86400
            generated_files = (
                "configure", "aclocal.m4", "config.h.in", "Makefile.in",
                "compile", "config.guess", "config.sub", "depcomp",
                "install-sh", "missing",
                os.path.join("data", "Makefile.in"),
                os.path.join("pixmaps", "Makefile.in"),
                os.path.join("pixmaps", "icons", "Makefile.in"),
                os.path.join("platform-specific", "Makefile.in"),
                os.path.join("platform-specific", "linux", "Makefile.in"),
                os.path.join("po", "Makefile.in"),
                os.path.join("src", "Makefile.in"),
                os.path.join("subprojects", "Makefile.in"),
            )
            for root in roots:
                for rel in generated_files:
                    gen_file = os.path.join(root, rel)
                    if os.path.exists(gen_file):
                        os.utime(gen_file, (now, now))
                # Patch-affected sources (configure.ac, the Makefile.am that
                # patches 0002/0005 touch, and the generated po/Makefile.am)
                # must be strictly OLDER than the generated files, else the
                # automake (Makefile.in) or autoconf (configure) regeneration
                # rule fires and calls the missing automake-1.17.  Pin them
                # to the past so the ordering holds regardless of timestamp
                # granularity.
                for rel in ("configure.ac", "Makefile.am",
                            os.path.join("src", "Makefile.am"),
                            os.path.join("subprojects", "Makefile.am"),
                            os.path.join("po", "Makefile.am")):
                    src_file = os.path.join(root, rel)
                    if os.path.exists(src_file):
                        os.utime(src_file, (past, past))
        else:
            # Fallback for a dev host with a working automake/aclocal:
            # regenerate via autoreconf.  aclocal 1.17 shipped on this host is
            # broken (@am_AUTOM4TE@ literal); aclocal-1.16/automake-1.16
            # coexist and work. Create wrappers on PATH.
            def _find_autotools_116(tool):
                exe = shutil.which(f"{tool}-1.16")
                if exe:
                    return exe
                home = os.path.expanduser("~")
                for base in (os.path.join(home, "usr/local/bin"),
                             "/usr/local/bin", "/usr/bin", "/opt/local/bin"):
                    cand = os.path.join(base, f"{tool}-1.16")
                    if os.path.isfile(cand):
                        return cand
                return None

            wrapper_dir = os.path.join(self.build_folder, "tool_wrappers")
            os.makedirs(wrapper_dir, exist_ok=True)
            found16 = False
            for tool in ("aclocal", "automake"):
                exe = _find_autotools_116(tool)
                if exe:
                    found16 = True
                    save(self, os.path.join(wrapper_dir, tool),
                         f'#!/bin/sh\nexec "{exe}" "$@"\n')
                    # conan.tools.files.chmod takes booleans, not an octal mode.
                    # read/write/execute=True reproduces 0o755 on the wrapper.
                    chmod(self, os.path.join(wrapper_dir, tool),
                          read=True, write=True, execute=True)

            # PKG_CHECK_MODULES lives in pkg.m4 (pkg-config).  On this
            # toolchain pkg.m4 is not in aclocal's default dir, so
            # PKG_CHECK_MODULES would be "possibly undefined" at autoconf
            # time.  Locate pkg.m4 and make it available through the source
            # m4/ dir (AC_CONFIG_MACRO_DIR) and ACLOCAL_PATH.
            aclocal_dirs = []
            for cand in ("/usr/share/aclocal", "/usr/local/share/aclocal",
                         "/storage/Users/currentUser/usr/local/share/aclocal"):
                if os.path.isfile(os.path.join(cand, "pkg.m4")):
                    aclocal_dirs.append(cand)
            # Toolchain pkg-config lives under /data/service/hnp/pkg-config.org/
            pkgconf_dir = "/data/service/hnp/pkg-config.org"
            if os.path.isdir(pkgconf_dir):
                for sub in os.listdir(pkgconf_dir):
                    d = os.path.join(pkgconf_dir, sub, "share", "aclocal")
                    if os.path.isfile(os.path.join(d, "pkg.m4")):
                        aclocal_dirs.append(d)
            if not aclocal_dirs:
                # fall back: try parent of pkg-config executable
                pc = shutil.which("pkg-config") or shutil.which("pkgconf")
                if pc:
                    d = os.path.join(os.path.dirname(os.path.dirname(
                        os.path.realpath(pc))), "share", "aclocal")
                    if os.path.isfile(os.path.join(d, "pkg.m4")):
                        aclocal_dirs.append(d)
            src_m4 = os.path.join(self.source_folder, "m4")
            os.makedirs(src_m4, exist_ok=True)
            have_local = os.path.isfile(os.path.join(src_m4, "pkg.m4"))
            if not have_local and aclocal_dirs:
                shutil.copy2(os.path.join(aclocal_dirs[0], "pkg.m4"),
                             os.path.join(src_m4, "pkg.m4"))

            path_env = os.environ.get("PATH", "")
            if found16:
                path_env = wrapper_dir + os.pathsep + path_env
            aclocal_env = " ".join(
                f'"{d}"' for d in aclocal_dirs) if aclocal_dirs else '""'
            # Run autoreconf manually; siril's git-archive tarball ships no
            # generated configure/aclocal.m4.
            self.run(
                f'cd "{self.source_folder}" && '
                f'PATH="{path_env}" ACLOCAL_PATH="{aclocal_env}" '
                f'autoreconf --install --force',
                env="conanbuild")

        # umask 077 in generated config.status template breaks on HMDFS
        # (setgid dir is not owner-writable) → force 022.  configure runs from
        # the build_folder copy, so patch the umask on BOTH trees.
        for root in (self.source_folder, self.build_folder):
            configure_script = os.path.join(root, "configure")
            if os.path.exists(configure_script):
                # Keep configure executable even if export/checkout lost the +x
                # bit on the committed patches/autotools/ files.
                chmod(self, configure_script, read=True, write=True,
                      execute=True)
                cfg = load(self, configure_script)
                if "(umask 077" in cfg:
                    cfg = cfg.replace("(umask 077", "(umask 022")
                    save(self, configure_script, cfg)
                # The umask rewrite (save) bumps configure to "now"; keep it
                # that way — NOT in the future, or configure's sanity check
                # ("newly created file is older than distributed files!")
                # fails because it compares $srcdir/configure with a file
                # created during configure.

        autotools = Autotools(self)
        autotools.configure()
        # -j2: parallel make on HMDFS is unreliable (jobserver fifo issues)
        autotools.make(args=["-j2"])

        # 真实编译并运行上游单元测试（HMBS 硬门禁要求的机器证据）。
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """编译并运行 siril 上游单元测试（src/tests/ 共 11 项：compare_fits、
        stacking_blocks_test、ser_test、siril_date_test、siril_world_cs_test、
        measure_sorting、imoper_test、soper_test、photometry_test、
        rejection_test、sorting），输出 HMBS_UPSTREAM_TEST_RESULT 标记并
        将结果写入 $build_folder/upstream-tests/upstream_test_result.json。
        任一测试失败即中断构建（与 criterion 配方同等的硬门禁行为）。"""
        script = os.path.join(self.export_sources_folder,
                              "tests", "upstream_tests.sh")
        if not os.path.isfile(script):
            raise ConanException("tests/upstream_tests.sh 未随配方导出")
        cr = self.dependencies.build["criterion"]
        cr_inc = cr.cpp_info.includedirs[0] if cr.cpp_info.includedirs else ""
        cr_lib = cr.cpp_info.libdirs[0] if cr.cpp_info.libdirs else ""
        out = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(out, exist_ok=True)
        self.run(
            f'SIRIL_SOURCE="{self.source_folder}" '
            f'SIRIL_BUILD="{self.build_folder}" '
            f'CRITERION_INCLUDE="{cr_inc}" CRITERION_LIB="{cr_lib}" '
            f'SIRIL_TESTS_OUT="{out}" bash "{script}"',
            env="conanbuild")
        result_path = os.path.join(out, "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException("上游测试未产出 upstream_test_result.json")
        result = load(self, result_path).strip()
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + result)
        try:
            data = json.loads(result)
        except Exception as exc:  # noqa: BLE001
            raise ConanException(
                f"上游测试结果解析失败: {exc}") from exc
        if data.get("status") != "passed":
            raise ConanException(
                f"上游测试未全部通过: passed={data.get('passed')} "
                f"failed={data.get('failed')} "
                f"executed={data.get('executed')}")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 携带上游测试结果到制品，供 test_package 重发 HMBS 标记
        # （缓存命中时 build() 不会重跑，标记必须能再次输出）。
        result_path = os.path.join(self.build_folder, "upstream-tests",
                                   "upstream_test_result.json")
        if os.path.isfile(result_path):
            copy(self, "upstream_test_result.json",
                 src=os.path.dirname(result_path),
                 dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        # Application package: consumers link nothing against it.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.requires = []
        self.cpp_info.system_libs = []
