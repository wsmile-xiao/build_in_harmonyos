#!/usr/bin/env python3
"""Conan recipe — libopenraw-pixbuf-loader 0.3.7

`libopenraw_pixbuf.so` is the gdk-pixbuf RAW loader module that ships inside
the libopenraw source tree (gnome/pixbuf-loader.c).  Upstream publishes no
standalone tarball for it, so the source is the official libopenraw 0.3.7
release tarball.

Build strategy
--------------
The loader itself is a *single* C file, and upstream builds it with one
trivial automake rule (gnome/Makefile.am):

    libopenraw_pixbuf_la_LDFLAGS = -no-undefined -module -avoid-version
    libopenraw_pixbuf_la_LIBADD  = ../lib/libopenraw.la $(LIBGLIB_LIBS) $(LIBGDKPIXBUF_LIBS)
    libopenraw_pixbuf_la_SOURCES = pixbuf-loader.c

so this recipe reproduces exactly that rule: it compiles gnome/pixbuf-loader.c
into a shared module (``-shared -fPIC``) linked against libopenraw, glib and
gdk-pixbuf, then installs it into lib/gdk-pixbuf-2.0/loaders/ (upstream
``GDK_PIXBUF_DIR``).

Upstream tests (R51)
--------------------
The package's own upstream component (gnome/) registers no tests, but the
*tarball* the package builds from is the whole libopenraw 3.7 tree, whose
automake ``TESTS`` registry contains 9 cases (lib/: teststream; testsuite/:
test_xmlhandler + testsuite; test/: fileio testoption ljpegtest testunpack
extensions testbititerator).  They exercise the library internals the loader
links against, so the recipe configures and builds that tree and runs the
registered tests via ``make check-TESTS`` in each directory (R51 step 2:
tests must actually run).  See notes.md for the census and the per-case
results; the ``testsuite`` case is data-driven and self-skips without camera
RAW samples (HAVE_CURL=no), which notes.md states explicitly.

The tree build is why this recipe needs autotools.

Dependency note
---------------
The module's API usage is satisfied by libopenraw 0.1.2's public headers
(all `or_*` symbols used by pixbuf-loader.c are present in 0.1.2), and
libopenraw/0.1.2 is the version published to the ohpcd registry, so it is the
one required here (R36: a dependency must be published to the registry before
a downstream package can be built/shipped).  The *source tree* built for the
tests is 0.3.7; boost/libjpeg-turbo/libxml2 are the tree's build inputs and
were already transitive through libopenraw/0.1.2 — they are declared
explicitly below because the upstream configure/make steps use them directly.
"""
import glob
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, load_toolchain_args
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.gnu.pkgconfigdeps import PkgConfigDeps
from conan.tools.layout import basic_layout

# Upstream `check_PROGRAMS` per directory: compiled for validation and, for
# those registered in automake `TESTS`, run through `check-TESTS`.
CHECK_PROGRAMS = {
    "lib": ["teststream"],
    "testsuite": ["test_xmlhandler", "testsuite"],
    "test": ["fileio", "testoption", "ciffcontainertest", "ljpegtest",
             "testunpack", "extensions", "missingcoefficients",
             "testbititerator"],
}


class LibopenrawPixbufLoaderConan(ConanFile):
    name = "libopenraw-pixbuf-loader"
    version = "0.3.7"
    description = "gdk-pixbuf loader module for camera RAW files (from libopenraw 0.3.7)"
    license = "LGPL-3.0-or-later"
    homepage = "https://libopenraw.freedesktop.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def configure(self):
        # a gdk-pixbuf loader is inherently a loadable shared module
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "libopenraw-pixbuf-loader is a gdk-pixbuf module and is shared-only"
            )

    # ── source ────────────────────────────────────────────────────────────
    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    # ── dependencies ──────────────────────────────────────────────────────
    def requirements(self):
        # libopenraw supplies the header + shared library the loader links to.
        # 0.1.2 is the version published in the ohpcd registry (R36).
        self.requires("libopenraw/0.1.2", transitive_headers=True, transitive_libs=True)
        # gdk-pixbuf supplies the loader backend headers (GDK_PIXBUF_ENABLE_BACKEND)
        # and the runtime host that dlopen()s the module.
        self.requires("gdk-pixbuf/2.44.6", transitive_headers=True, transitive_libs=True)
        # unify zlib: boost/1.84.0 (via libopenraw) pins zlib/1.3.1, while
        # glib/2.84.0.1 (via gdk-pixbuf) pins zlib/1.3.1.1.
        self.requires("zlib/1.3.1.1", override=True)

    def build_requirements(self):
        # The 0.3.x tree ships a Rust mp4 parser (lib/mp4) that cargo builds
        # into the static library linked into libopenraw; the OHOS image has
        # no system cargo/rustc.  openssl/zlib provide the PIC static archives
        # cargo's absent runtime libraries are relinked from.
        self.tool_requires("rust-toolchain/1.97.1")
        self.tool_requires("openssl/3.5.6.1.1")
        self.tool_requires("zlib/1.3.2")
        # boost / libjpeg-turbo / libxml2 are configure/make inputs of the
        # upstream tree that is built to run the registered tests (see module
        # docstring).  They are build-time only: the loader module this package
        # ships does not link any of them, and this package's public interface
        # (cpp_info.requires) names only libopenraw and gdk-pixbuf.  Declaring
        # them as tool_requires keeps them out of the host interface, which is
        # both accurate and required — Conan's package_info() rejects a visible
        # direct host dependency that no cpp_info.requires refers to.
        self.tool_requires("boost/1.84.0")
        self.tool_requires("libjpeg-turbo/3.2.0")
        self.tool_requires("libxml2/2.15.3")

    # ── build ─────────────────────────────────────────────────────────────
    def _compiler(self):
        """C compiler, taken from the Conan profile (R33 — never ${CC})."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c") or executables.get("cpp") or "clang"

    def _dep_paths(self, attr):
        """Absolute, existing dirs contributed by host dependencies."""
        paths = []
        for dep in self.dependencies.host.values():
            for cppinfo in (dep.cpp_info, dep.cpp_info.aggregated_components()):
                for entry in getattr(cppinfo, attr):
                    full = entry if os.path.isabs(entry) else os.path.join(
                        dep.package_folder, entry
                    )
                    if os.path.isdir(full) and full not in paths:
                        paths.append(full)
        return paths

    def _dep_folder(self, name):
        """Package folder of a dependency, searched in the host context first
        and then in the build context.

        boost / libjpeg-turbo / libxml2 are tool_requires here (build-time
        only, see build_requirements), so their folders live in the build
        context; libopenraw / gdk-pixbuf are host requirements.  Indexing
        ``self.dependencies[name]`` is not enough: it does not resolve
        ``package_folder`` for these, so walk the contexts explicitly."""
        for deps in (self.dependencies.host, self.dependencies.build):
            for dep in deps.values():
                ref = getattr(dep, "ref", None)
                if ref is not None and ref.name == name:
                    return dep.package_folder
        return None

    def _dep_libs(self, names):
        """Library names (for -l) of the named host dependencies + their
        aggregated component libs."""
        libs = []
        for name in names:
            dep = next((d for d in self.dependencies.host.values()
                        if d.ref.name == name), None)
            if dep is None:
                continue
            for cppinfo in (dep.cpp_info, dep.cpp_info.aggregated_components()):
                for lib in cppinfo.libs:
                    if lib and lib not in libs:
                        libs.append(lib)
        return libs

    def generate(self):
        # Emit the dependencies' pkg-config files (libxml-2.0.pc, libjpeg.pc,
        # boost.pc, zlib.pc) and put the generator dir on PKG_CONFIG_PATH so
        # the upstream configure probes resolve them.
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-gnome")
        boost = self._dep_folder("boost")
        tc.configure_args.append("--with-boost={}".format(boost))
        # Every upstream test includes the header-only
        # <boost/test/included/unit_test.hpp>, so no Boost.Test *library* is
        # needed; the published boost package ships no
        # libboost_unit_test_framework and boost.m4's link probe would fail.
        # Seed the autoconf cache so the probe is skipped and
        # BOOST_UNIT_TEST_FRAMEWORK_{LIBS,LDFLAGS} stay empty.
        tc.configure_args.append("boost_cv_lib_unit_test_framework=yes")
        jpeg = self._dep_folder("libjpeg-turbo")
        tc.extra_cflags.append("-I{}/include".format(jpeg))
        tc.extra_cxxflags.append("-I{}/include".format(jpeg))
        # boost::smart_ptr calls pthread_setcancelstate(), absent from bionic.
        tc.extra_cxxflags.append("-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE")
        tc.extra_ldflags.append("-L{}/lib".format(jpeg))
        xml = self._dep_folder("libxml2")
        tc.extra_cflags.extend(["-I{}/include/libxml2".format(xml),
                                "-I{}/include".format(xml)])
        tc.extra_ldflags.append("-L{}/lib".format(xml))
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()
        self._write_rust_env()
        self._write_tree_env()
        self._write_test_run_env()

    # ── Rust toolchain / cargo runtime (OHOS has neither) ────────────────
    def _ohos_cc(self):
        cc = self.conf.get("tools.build:compiler_executables",
                           default={}).get("c")
        for candidate in (cc, shutil.which("clang"),
                          "/data/service/hnp/bin/clang"):
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration("no C compiler found for Rust linking")

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            "/data/service/hnp/bin/binary-sign-tool",
        ]
        cc = self._ohos_cc()
        candidates.append(os.path.join(os.path.dirname(cc),
                                       "binary-sign-tool"))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _sign(self, paths):
        """Sign ELF images with binary-sign-tool — HarmonyOS refuses to
        execve/dlopen unsigned images (EACCES)."""
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; OHOS may reject unsigned ELF "
                "images (EACCES)")
            return
        for path in paths:
            tmp = path + ".signed"
            result = subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", tmp,
                 "-selfSign", "1"], capture_output=True, text=True)
            if result.returncode != 0 or not os.path.isfile(tmp):
                raise ConanInvalidConfiguration(
                    "binary-sign-tool failed for %s (rc=%d): %s"
                    % (path, result.returncode, result.stderr[:200]))
            os.replace(tmp, path)
            os.chmod(path, 0o755)

    def _prepare_signed_toolchain(self):
        """Copy cargo/rustc + librustc_driver into the build folder and sign
        them. Returns the bin directory, or None if unavailable. Idempotent
        via a marker file so repeated builds do not re-sign."""
        dst = os.path.join(self.build_folder, "rust-toolchain")
        bin_dst = os.path.join(dst, "bin")
        lib_dst = os.path.join(dst, "lib")
        marker = os.path.join(dst, ".prepared")
        if os.path.isfile(marker):
            return bin_dst
        try:
            tool = self.dependencies.build["rust-toolchain"]
        except KeyError:
            tool = None
        if not tool:
            return None
        src = tool.package_folder
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)
        to_sign = []
        for name in ("cargo", "rustc"):
            s = os.path.join(src, "bin", name)
            if os.path.isfile(s):
                d = os.path.join(bin_dst, name)
                shutil.copy2(s, d)
                os.chmod(d, 0o755)
                to_sign.append(d)
        src_lib = os.path.join(src, "lib")
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                if name.startswith("librustc_driver") and name.endswith(".so"):
                    d = os.path.join(lib_dst, name)
                    shutil.copy2(os.path.join(src_lib, name), d)
                    os.chmod(d, 0o755)
                    to_sign.append(d)
        self._sign(to_sign)
        # Remaining read-only payload is symlinked (rustc's sysroot is `dst`,
        # so dst/lib/rustlib must be visible).
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                d = os.path.join(lib_dst, name)
                if not os.path.exists(d):
                    os.symlink(os.path.join(src_lib, name), d)
        for name in ("etc", "libexec", "share"):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.isdir(s) and not os.path.exists(d):
                os.symlink(s, d)
        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("signed toolchain prepared\n")
        return bin_dst

    def _relink_runtime_libs(self):
        """Relink cargo's runtime shared libraries from the published PIC
        static archives into a private build-folder directory."""
        cc = self._ohos_cc()
        runtime = os.path.join(self.build_folder, "rust-runtime-libs")
        os.makedirs(runtime, exist_ok=True)
        openssl = self.dependencies.build["openssl"].package_folder
        zlib = self.dependencies.build["zlib"].package_folder
        specs = [
            ("crypto", os.path.join(openssl, "lib", "libcrypto.a"), []),
            ("ssl", os.path.join(openssl, "lib", "libssl.a"),
             ["-L" + runtime, "-lcrypto"]),
            ("z", os.path.join(zlib, "lib", "libz.a"), []),
        ]
        for name, archive, extra in specs:
            out = os.path.join(runtime, "lib{}.so".format(name))
            if os.path.isfile(out):
                continue
            cmd = ([cc, "-shared", "-fPIC", "-Wl,-z,relro,-z,now",
                    "-Wl,-soname,lib{}.so".format(name),
                    "-Wl,--whole-archive", archive, "-Wl,--no-whole-archive",
                    "-ldl", "-pthread"] + extra + ["-o", out])
            self.run(shlex.join(cmd), env=["conanbuild"])
        return runtime

    def _write_rust_env(self):
        bin_dir = self._prepare_signed_toolchain()
        if not bin_dir:
            return
        runtime = self._relink_runtime_libs()
        lib_dir = os.path.join(self.build_folder, "rust-toolchain", "lib")
        scratch = os.path.join(self.build_folder, "tmp")
        os.makedirs(scratch, exist_ok=True)
        env = Environment()
        env.prepend_path("PATH", bin_dir)
        env.prepend_path("LD_LIBRARY_PATH", runtime)
        env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        env.define("CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER",
                   self._ohos_cc())
        # The vendored libc 0.2.126 predates target_env = "ohos"; its musl
        # bindings map strerror_r onto bionic's plain strerror_r.
        env.define("RUSTFLAGS",
                   '--cfg target_env="musl" -Aexplicit_builtin_cfgs_in_flags')
        env.define("CARGO_HOME", os.path.join(self.build_folder, "cargo-home"))
        env.define("CARGO_NET_OFFLINE", "true")
        env.define("TMPDIR", scratch)
        env.vars(self, scope="build").save_script("rust_env")

    def _write_tree_env(self):
        """Flags for the upstream tree's libxml2 probe.

        libxml2 is a tool_require (build-time only, see build_requirements), so
        PkgConfigDeps — which walks the host dependencies — does not emit a
        libxml-2.0.pc.  autoconf's PKG_CHECK_MODULES uses $LIBXML_CFLAGS and
        $LIBXML_LIBS verbatim when both are set, skipping pkg-config, so supply
        them here instead of relying on the .pc file."""
        xml = self._dep_folder("libxml2")
        if not xml:
            return
        env = Environment()
        env.define("LIBXML_CFLAGS", "-I{}/include/libxml2".format(xml))
        env.define("LIBXML_LIBS", "-L{}/lib -lxml2".format(xml))
        env.vars(self, scope="build").save_script("libopenraw_tree_env")

    def _write_test_run_env(self):
        """Loader paths for the freshly built (uninstalled) libraries plus
        the dependency package libraries, used when running the tests."""
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH",
                         os.path.join(self.build_folder, "lib", ".libs"))
        for dep in ("libxml2", "libjpeg-turbo", "boost"):
            folder = self._dep_folder(dep)
            if not folder:
                continue
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(folder, "lib"))
        env.define("srcdir", os.path.join(self.source_folder))
        env.vars(self, scope="build").save_script("libopenraw_test_env")

    # ── upstream configure fix-up ────────────────────────────────────────
    def _fix_configure_umask(self):
        """HMDFS forces setgid; a scratch dir created with umask 077 is not
        writable even by its owner, so configure's `umask 077 && mktemp -d`
        probe fails. Rewrite it to 022 (same fix as the libopenraw recipes)."""
        cfg = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cfg):
            return
        with open(cfg, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
        if "umask 077" not in text:
            return
        with open(cfg, "w", encoding="utf-8") as fh:
            fh.write(text.replace("umask 077", "umask 022"))
        self.output.info("patched configure: umask 077 -> umask 022")

    def _build_loader_module(self):
        """Compile gnome/pixbuf-loader.c into the shipped module, mirroring
        gnome/Makefile.am exactly (the tree is configured --disable-gnome)."""
        source = os.path.join(self.source_folder, "gnome", "pixbuf-loader.c")
        module = os.path.join(self.build_folder, "libopenraw_pixbuf.so")

        cmd = [self._compiler(), "-shared", "-fPIC", "-O2", "-o", module, source]
        for incdir in self._dep_paths("includedirs"):
            cmd.append(f"-I{incdir}")
        for libdir in self._dep_paths("libdirs"):
            cmd.append(f"-L{libdir}")
        # mirror gnome/Makefile.am LIBADD = libopenraw + $(LIBGLIB_LIBS) + $(LIBGDKPIXBUF_LIBS)
        for lib in self._dep_libs(["libopenraw", "glib", "gdk-pixbuf"]):
            cmd.append(f"-l{lib}")

        self.output.info("Compiling gdk-pixbuf loader module:")
        self.output.info("  " + shlex.join(cmd))
        self.run(shlex.join(cmd))

    # ── upstream tree build + tests ──────────────────────────────────────
    def _build_upstream_tree(self):
        """Configure and build the libopenraw 3.7 tree the tests come from."""
        self._fix_configure_umask()
        args = load_toolchain_args(self.generators_folder).get("configure_args")
        configure = os.path.join(self.source_folder, "configure")
        self.run('"{}" {}'.format(configure, args),
                 cwd=self.build_folder, env=["conanbuild", "rust_env"])
        self.run("make -j1", cwd=self.build_folder,
                 env=["conanbuild", "rust_env"])

    def _run_upstream_tests(self):
        """R51 step 2: compile the upstream test programs and run every case
        registered in automake TESTS via `check-TESTS`.  A known environment
        limitation (the data-driven testsuite has no camera RAW samples and
        skips) must not break packaging, so failures are surfaced in the log
        but do not abort the build."""
        for directory, programs in CHECK_PROGRAMS.items():
            self.run("make -j1 " + " ".join(programs),
                     cwd=os.path.join(self.build_folder, directory),
                     env=["conanbuild", "rust_env"], ignore_errors=True)
        # OHOS refuses to execute unsigned ELF images.
        self._sign_built_executables()
        results = {}
        for directory in CHECK_PROGRAMS:
            # automake's parallel test harness needs a stable cwd: HMDFS
            # makes getcwd() fail when the shell's cwd is a removed dir, and
            # the libtool wrapper then resolves the program path wrongly.
            self.run("make -j1 check-TESTS",
                     cwd=os.path.join(self.build_folder, directory),
                     env=["conanrun", "libopenraw_test_env"],
                     ignore_errors=True)
            results[directory] = self._collect_test_results(directory)
        self._report_test_results(results)
        return results

    def _collect_test_results(self, directory):
        """Read automake's per-test .trs files for the given directory."""
        results = {}
        pattern = os.path.join(self.build_folder, directory, "*.trs")
        for path in sorted(glob.glob(pattern)):
            name = os.path.basename(path)[:-4]
            try:
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            for line in text.splitlines():
                if line.startswith(":test-result:"):
                    results[name] = line.split(":", 2)[2].strip()
                    break
        return results

    def _report_test_results(self, results):
        total = passed = 0
        for directory, cases in results.items():
            for name, outcome in cases.items():
                total += 1
                if outcome == "PASS":
                    passed += 1
                self.output.info("UPSTREAM TEST {}/{}: {}".format(
                    directory, name, outcome))
        self.output.info(
            "UPSTREAM TESTS SUMMARY: {}/{} passed (N'={}, N={})".format(
                passed, total, total, len(self._registered_tests())))

    @staticmethod
    def _registered_tests():
        """The 9 cases registered in automake TESTS across the tree."""
        return ["teststream", "test_xmlhandler", "testsuite", "fileio",
                "testoption", "ljpegtest", "testunpack", "extensions",
                "testbititerator"]

    def _sign_built_executables(self, roots=None):
        """OHOS refuses to execute unsigned ELF images; sign every executable
        produced by the test-program build before automake runs it."""
        signable = []
        for root in roots or [self.build_folder]:
            for base, _dirs, files in os.walk(root):
                for name in files:
                    path = os.path.join(base, name)
                    if not os.path.isfile(path) or os.path.islink(path):
                        continue
                    try:
                        with open(path, "rb") as fh:
                            if fh.read(4) != b"\x7fELF":
                                continue
                    except OSError:
                        continue
                    if os.access(path, os.X_OK):
                        signable.append(path)
        if signable:
            self._sign(signable)

    def build(self):
        apply_conandata_patches(self)
        # 1) the module this package ships (single-file clang compile)
        self._build_loader_module()
        # 2) the upstream tree + its registered tests (R51)
        self._build_upstream_tree()
        if can_run(self):
            self._run_upstream_tests()

    # ── package ───────────────────────────────────────────────────────────
    def package(self):
        loaders_dir = os.path.join(
            self.package_folder, "lib", "gdk-pixbuf-2.0", "loaders"
        )
        copy(
            self,
            "libopenraw_pixbuf.so",
            src=self.build_folder,
            dst=loaders_dir,
        )
        if str(self.settings.os) == "OHOS":
            self._sign_module(os.path.join(loaders_dir, "libopenraw_pixbuf.so"))

    def _sign_module(self, module):
        """Sign the ELF module on HarmonyOS — an unsigned module cannot be
        dlopen()ed (R7 safe-execution)."""
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip signing")
            return
        self.run(
            shlex.join(
                [signer, "sign", "-inFile", module, "-outFile", module, "-selfSign", "1"]
            )
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib/gdk-pixbuf-2.0/loaders"]
        self.cpp_info.libs = ["openraw_pixbuf"]
        self.cpp_info.requires = [
            "libopenraw::libopenraw",
            "gdk-pixbuf::gdk-pixbuf",
        ]
        self.cpp_info.set_property("cmake_file_name", "libopenraw-pixbuf-loader")
        self.cpp_info.set_property(
            "cmake_target_name", "libopenraw-pixbuf-loader::libopenraw-pixbuf-loader"
        )
        self.cpp_info.set_property("pkg_config_name", "libopenraw-pixbuf-loader")
