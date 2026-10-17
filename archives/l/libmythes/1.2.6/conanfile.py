#!/usr/bin/env python3
"""Conan recipe — libmythes 1.2.6 (Autotools).

MyThes is a simple thesaurus library using structured text data
(.idx index + .dat data, e.g. th_en_US_new), used by LibreOffice
and Hunspell for synonym lookup (MyThes::Lookup).

Upstream: https://github.com/hunspell/mythes

OHOS adaptation notes (see notes.md for the full log):
  - Autotools build with a mandatory hunspell pkg-config probe
    (PKG_CHECK_MODULES in configure.ac); the library itself
    (mythes.cxx) does not include hunspell, only the example
    check program (example.cxx) does.
  - configure is run with --disable-werror (MSYS2 precedent):
    upstream -Werror breaks on clang 15 warnings for legacy C++.
  - make uses -j1: OHOS sandbox has no mkfifo jobserver support.
  - Upstream `make check` builds check_PROGRAMS=example but defines
    no TESTS, so it runs zero automated assertions (same pattern as
    libXext 6.4.0.1: build() runs make, MANIFEST records empty).
  - package() removes libtool .la archives, dereferences .so alias
    symlinks into real copies (HMDFS linker cannot resolve links),
    and installs COPYING into licenses/.
"""

import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibmythesConan(ConanFile):
    name = "libmythes"
    version = "1.2.6"
    description = "Simple thesaurus library using structured text data (.idx/.dat)"
    license = "BSD-Mark-Modifications"
    homepage = "https://github.com/hunspell/mythes"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/l/libmythes/1.2.6"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libmythes supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # configure.ac PKG_CHECK_MODULES([HUNSPELL],[hunspell]) is
        # mandatory; example.cxx includes <hunspell.hxx> for stemming.
        self.requires("hunspell/1.7.3", transitive_headers=True)

    def build_requirements(self):
        # configure performs PKG_PROG_PKG_CONFIG / PKG_CHECK_MODULES;
        # the HMBS preflight worker has no system pkg-config
        # (configure aborts: "pkg-config not found"). Provide it as a
        # build tool (cassbeam 1.1 / libesmtp 1.1.0 precedent).
        # 3.0.4 is the published OHOS revision (see
        # archives/p/pkgconf/manifest.yaml); the pkgconf package ships
        # bin/pkgconf WITHOUT a bin/pkg-config alias
        # (pkg_config_alias: false), so generate() additionally defines
        # PKG_CONFIG plus a pkg-config -> pkgconf shim on PATH.
        self.tool_requires("pkgconf/3.0.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            shell = self._ohos_shell()
            environment = tc.environment()
            environment.define_path("SHELL", shell)
            environment.define_path("CONFIG_SHELL", shell)
            environment.define_path("CC", self._compiler_executable("c", "clang"))
            environment.define_path("CXX", self._compiler_executable("cpp", "clang++"))
            environment.define_path("LD", self._tool_executable("ld.lld", "lld", "ld"))
            environment.define_path("AR", self._tool_executable("llvm-ar", "ar"))
            environment.define_path(
                "RANLIB", self._tool_executable("llvm-ranlib", "ranlib")
            )
            environment.define_path(
                "STRIP", self._tool_executable("llvm-strip", "strip")
            )
            environment.define_path("NM", self._tool_executable("llvm-nm", "nm"))
            gnu_triplet = self._gnu_triplet()
            # The compiler target still comes from the Conan profile; this
            # pair is only for Autotools canonicalization when the bundled
            # config.guess/config.sub predate OHOS (libXext precedent).
            tc.update_configure_args(
                {
                    "--build": gnu_triplet,
                    "--host": gnu_triplet,
                }
            )
        # --disable-werror: upstream appends -Werror unless disabled
        # (MSYS2 builds with --disable-werror); clang 15 promotes legacy
        # warnings to errors otherwise.
        tc.configure_args.extend(
            [
                "--disable-werror",
                "--disable-dependency-tracking",
            ]
        )
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
            if self.options.get_safe("fPIC"):
                tc.configure_args.append("--with-pic")
        # PkgConfigDeps writes hunspell.pc into the generators folder, but
        # the conanbuild env does not put it on PKG_CONFIG_PATH, so
        # PKG_CHECK_MODULES([HUNSPELL]) would report "No package
        # 'hunspell' found" (abiword-plugin-sdw 3.0.8 precedent).
        tc.configure_args.append(
            "PKG_CONFIG_PATH={}".format(self.generators_folder)
        )
        # Conan's PkgConfigDeps emits hunspell.pc with Cflags=-I<package>/include
        # (no /hunspell suffix), while upstream hunspell.pc uses
        # -I${includedir}/hunspell and example.cxx does #include <hunspell.hxx>
        # (flat). With only the generated .pc, `make check` fails with
        # "fatal error: 'hunspell.hxx' file not found". Bypass pkg-config by
        # passing explicit HUNSPELL_CFLAGS/HUNSPELL_LIBS (autoconf honours
        # pre-set pkg-config variables and skips the probe), covering both
        # include styles: -I<include> and -I<include>/hunspell.
        hun_cflags, hun_libs = self._hunspell_pkg_config_override()
        if hun_cflags:
            tc.configure_args.append("HUNSPELL_CFLAGS={}".format(hun_cflags))
        if hun_libs:
            tc.configure_args.append("HUNSPELL_LIBS={}".format(hun_libs))
        # pkgconf binary + pkg-config shim (cassbeam 1.1 precedent).
        # PKG_PROG_PKG_CONFIG honours $PKG_CONFIG, while literal
        # `AC_CHECK_PROG(pkg-config)` probes need the shim name on PATH.
        # Both are published via a saved conanbuild script so the
        # Autotools helper picks them up (os.environ edits in build()
        # would not reach its conanbuild env).
        self._expose_pkg_config()
        if str(self.settings.os) == "OHOS":
            # configure probes write under ${TMPDIR:-$HOME/tmp} on HMDFS;
            # feed the HMBS-injected task-private TMPDIR through.
            tmpdir = self._writable_tmpdir()
            environment.define_path("TMPDIR", tmpdir)
            environment.define_path("TMP", tmpdir)
            environment.define_path("TEMP", tmpdir)
            tc.generate(env=environment)
        else:
            tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._patch_configure_runtime_shell()
        autotools = Autotools(self)
        autotools.configure()
        # -j1: OHOS sandbox has no mkfifo jobserver support.
        autotools.make(args=["-j1"])
        # Upstream `make check` builds check_PROGRAMS (example) but
        # defines no TESTS: zero automated assertions. Run it so the
        # example link (libmythes + hunspell) is verified at build time.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        self._ensure_header_installed()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._normalize_installed_libs()
        self._remove_libtool_archives()

    def package_info(self):
        # lib_LTLIBRARIES = libmythes-1.2.la -> libmythes-1.2.so
        self.cpp_info.libs = ["mythes-1.2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["hunspell::hunspell"]
        self.cpp_info.set_property("cmake_file_name", "libmythes")
        self.cpp_info.set_property("cmake_target_name", "libmythes::libmythes")
        self.cpp_info.set_property("pkg_config_name", "mythes")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )

    def _hunspell_pkg_config_override(self):
        """Build explicit HUNSPELL_CFLAGS/HUNSPELL_LIBS for configure.

        Upstream hunspell.pc declares Cflags=-I${includedir}/hunspell so that
        `#include <hunspell.hxx>` resolves; Conan PkgConfigDeps generates
        -I<package>/include only, which breaks mythes example.cxx. Return
        (cflags, libs) covering both -I styles, or ("", "") when the dep is
        unavailable (fall back to pkg-config probe).
        """
        try:
            dep = self.dependencies["hunspell"]
        except Exception:
            return "", ""
        try:
            pkg_folder = getattr(dep, "package_folder", "") or ""
            if not pkg_folder:
                return "", ""
            # Include dirs from cpp_info (usually ["include"]) plus the
            # upstream-style /hunspell suffix for flat #include <hunspell.hxx>.
            inc_dirs = []
            try:
                for rel in (dep.cpp_info.includedirs or ["include"]):
                    abs_inc = rel if os.path.isabs(rel) else os.path.join(pkg_folder, rel)
                    if abs_inc not in inc_dirs:
                        inc_dirs.append(abs_inc)
            except Exception:
                inc_dirs = [os.path.join(pkg_folder, "include")]
            hun_sub = os.path.join(pkg_folder, "include", "hunspell")
            if os.path.isdir(hun_sub) and hun_sub not in inc_dirs:
                inc_dirs.append(hun_sub)
            cflags = " ".join("-I{}".format(d) for d in inc_dirs if d)
            # Lib dir + lib name from cpp_info (usually ["hunspell-1.7"]).
            lib_dir = os.path.join(pkg_folder, "lib")
            try:
                libdirs = dep.cpp_info.libdirs or ["lib"]
                first = libdirs[0]
                lib_dir = first if os.path.isabs(first) else os.path.join(pkg_folder, first)
            except Exception:
                pass
            try:
                libs_list = list(dep.cpp_info.libs or ["hunspell-1.7"])
            except Exception:
                libs_list = ["hunspell-1.7"]
            libs = "-L{} {}".format(lib_dir, " ".join("-l{}".format(l) for l in libs_list))
            self.output.info("HUNSPELL_CFLAGS override: {}".format(cflags))
            self.output.info("HUNSPELL_LIBS override: {}".format(libs))
            return cflags, libs
        except Exception as exc:
            self.output.warning("hunspell override failed: {}".format(exc))
            return "", ""

    def _pkgconf_binary(self):
        """Return an existing pkgconf binary path, or empty string."""
        try:
            build_deps = getattr(self.dependencies, "build", {})
            pkgconf_dep = build_deps.get("pkgconf") if build_deps else None
            if pkgconf_dep is not None:
                pkg_folder = getattr(pkgconf_dep, "package_folder", "") or ""
                if pkg_folder:
                    for name in ("pkgconf", "pkg-config"):
                        candidate = os.path.join(pkg_folder, "bin", name)
                        if os.path.isfile(candidate):
                            return candidate
        except Exception:
            pass
        for name in ("pkgconf", "pkg-config"):
            found = shutil.which(name)
            if found:
                return found
        return ""

    def _expose_pkg_config(self):
        """Define PKG_CONFIG and a pkg-config shim for configure."""
        pkgconf_bin = self._pkgconf_binary()
        if not pkgconf_bin:
            self.output.warning(
                "pkgconf binary not found; configure may fail with "
                "'pkg-config not found'"
            )
            return
        env = Environment()
        env.define("PKG_CONFIG", pkgconf_bin)
        # The pkgconf package ships bin/pkgconf WITHOUT a bin/pkg-config
        # alias by design; provide the literal name configure probes for.
        shim_dir = os.path.join(self.build_folder, "hmbs-shims")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            shim_dir = ""
        if shim_dir:
            link = os.path.join(shim_dir, "pkg-config")
            try:
                if os.path.islink(link) or os.path.isfile(link):
                    try:
                        os.remove(link)
                    except OSError:
                        pass
                try:
                    os.symlink(pkgconf_bin, link)
                except (OSError, NotImplementedError):
                    shutil.copyfile(pkgconf_bin, link)
                env.prepend_path("PATH", shim_dir)
                self.output.info(
                    "pkg-config shim: {} -> {}".format(link, pkgconf_bin)
                )
            except Exception as exc:
                self.output.warning("pkg-config shim failed: {}".format(exc))
        env.vars(self).save_script("hmbs_pkg_config")
        self.output.info("PKG_CONFIG={}".format(pkgconf_bin))

    def _gnu_triplet(self):
        arch = str(self.settings.arch)
        machine = {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "x86_64": "x86_64",
            "armv7": "arm",
        }.get(arch, arch)
        return f"{machine}-unknown-linux-gnu"

    def _ohos_shell(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
            "/usr/bin/sh",
            "/data/service/hnp/bin/bash",
        ):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "/system/bin/sh"

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _tool_executable(self, *names):
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return names[0]

    def _writable_tmpdir(self):
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                return candidate
        fallback = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _patch_configure_runtime_shell(self):
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        shell = self._ohos_shell()
        replace_in_file(
            self,
            configure_path,
            "umask 077",
            "umask 022",
            strict=False,
        )
        for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
            replace_in_file(
                self,
                configure_path,
                pattern,
                f"#!{shell}",
                strict=False,
            )

    def _ensure_header_installed(self):
        """Fallback: guarantee mythes.hxx lands flat in include/.

        Upstream installs mythes.hxx flat to $(includedir) via
        libmythes_1_2_include_HEADERS (see Makefile.am + mythes.pc
        Cflags=-I${includedir}). The preflight test_package died with
        "fatal error: 'mythes.hxx' file not found" despite
        -I<package>/include being passed, i.e. `make install` did not
        leave the header where consumers expect on OHOS. Copy it from
        the source tree when missing; no-op when install already did.
        """
        dst_dir = os.path.join(self.package_folder, "include")
        dst = os.path.join(dst_dir, "mythes.hxx")
        if os.path.isfile(dst):
            return
        src = os.path.join(self.source_folder, "mythes.hxx")
        if not os.path.isfile(src):
            self.output.warning(
                "mythes.hxx missing in both package and source; "
                "consumers will fail to include <mythes.hxx>"
            )
            return
        copy(self, "mythes.hxx", src=self.source_folder, dst=dst_dir,
             keep_path=False)
        self.output.info("fallback-installed mythes.hxx into include/")

    def _normalize_installed_libs(self):
        """Repair dangling .so aliases from the build tree (pure Python).

        Third-attempt strategy (differs from both previous alias-only
        fixes): preflight evidence now shows package lib/ contains ONLY
        the two aliases ['libmythes-1.2.so', 'libmythes-1.2.so.0'] with
        no versioned real file, i.e. both are dangling links, so
        `ld.lld: unable to find library -lmythes-1.2`. The previous
        logic skipped dangling links when gathering candidates
        (isfile()==False follows the broken target), found zero
        candidates and returned without repairing. The real library
        was still built (make+make check succeeded and linked the
        example), so source it from the build tree's .libs/ and copy
        it into package lib/ as real files. No shell `cp -a` (needs
        chmod/hardlink, unsupported: chmod=0 hardlink=0) and no
        symlinks left behind (HMDFS/ld.lld cannot resolve them, E050).
        """
        pkg = self.package_folder
        libdir = os.path.join(pkg, "lib")
        try:
            os.makedirs(libdir, exist_ok=True)
        except OSError:
            pass
        try:
            raw = sorted(os.listdir(libdir))
        except OSError:
            raw = []
        self.output.info("package lib/ raw: {}".format(raw or "<empty>"))
        for entry in raw:
            if not entry.startswith("libmythes-1.2."):
                continue
            path = os.path.join(libdir, entry)
            try:
                is_link = os.path.islink(path)
            except OSError:
                is_link = False
            try:
                is_file = os.path.isfile(path)
            except OSError:
                is_file = False
            try:
                exists = os.path.lexists(path)
            except OSError:
                exists = is_file or is_link
            self.output.info(
                "lib/{}: islink={} isfile={} lexists={}".format(
                    entry, is_link, is_file, exists))
        # Find a real (non-dangling) library image: first anywhere under
        # package lib/lib64, then the build tree (.libs/).
        real_src = ""
        for sub in ("lib", "lib64"):
            d = os.path.join(pkg, sub)
            try:
                entries = sorted(os.listdir(d), key=len, reverse=True)
            except OSError:
                continue
            for entry in entries:
                if not entry.startswith("libmythes-1.2."):
                    continue
                path = os.path.join(d, entry)
                try:
                    if os.path.islink(path):
                        real = os.path.realpath(path)
                        if real and os.path.isfile(real):
                            real_src = real
                            break
                    elif os.path.isfile(path):
                        real_src = path
                        break
                except OSError:
                    continue
            if real_src:
                break
        if not real_src:
            # Fall back to the build tree: libtool keeps the real image
            # under .libs/ (out-of-tree build dir or source dir).
            search_roots = []
            for attr in ("build_folder", "source_folder"):
                try:
                    root = getattr(self, attr, "") or ""
                except Exception:
                    root = ""
                if root and os.path.isdir(root) and root not in search_roots:
                    search_roots.append(root)
            for root in search_roots:
                for dirpath, _, filenames in os.walk(root):
                    if os.path.basename(dirpath) != ".libs":
                        continue
                    for name in sorted(filenames, key=len, reverse=True):
                        if not name.startswith("libmythes-1.2."):
                            continue
                        cand = os.path.join(dirpath, name)
                        try:
                            if os.path.isfile(cand) and not os.path.islink(cand):
                                real_src = cand
                                break
                        except OSError:
                            continue
                    if real_src:
                        break
                if real_src:
                    break
        if not real_src:
            self.output.warning(
                "no real libmythes-1.2 image in package or build tree; "
                "linker will fail with unable to find library -lmythes-1.2")
            return
        self.output.info("lib source image: {}".format(real_src))
        # Replace every alias/dangling link in lib/ with a real copy of
        # the image, and ensure all three names exist as real files.
        # CI #48305 guard: when the real image already lives inside
        # package lib/ (islink=False isfile=True), dst == real_src for
        # the versioned name; removing it first deletes the source and
        # all three copyfile() then fail with ENOENT, leaving lib/ with
        # only pkgconfig/ and `ld.lld: unable to find library
        # -lmythes-1.2`. Skip the self-copy so the source survives for
        # the remaining aliases.
        real_src_norm = os.path.abspath(real_src)
        base = os.path.basename(real_src)
        names = ["libmythes-1.2.so.0.0.0", "libmythes-1.2.so.0", "libmythes-1.2.so"]
        # Keep the exact versioned basename when it looks versioned.
        if base.startswith("libmythes-1.2.so.") and base not in names:
            names.insert(0, base)
        for name in names:
            dst = os.path.join(libdir, name)
            if os.path.abspath(dst) == real_src_norm:
                self.output.info(
                    "lib/{} already a real file, keep".format(name))
                continue
            try:
                if os.path.islink(dst) or os.path.lexists(dst):
                    os.remove(dst)
            except OSError:
                pass
            try:
                shutil.copyfile(real_src, dst)
                self.output.info("installed lib/{} from build image".format(name))
            except Exception as exc:
                self.output.warning("install {} failed: {}".format(name, exc))

    def _dereference_shared_aliases(self):
        """Kept for compatibility; delegates to _normalize_installed_libs."""
        self._normalize_installed_libs()

    def _remove_libtool_archives(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for entry in os.listdir(lib_dir):
            if not entry.endswith(".la"):
                continue
            os.remove(os.path.join(lib_dir, entry))
        for pc_file in self._pkg_config_files(lib_dir):
            self._make_pc_relocatable(pc_file)

    def _pkg_config_files(self, lib_dir):
        pc_dir = os.path.join(lib_dir, "pkgconfig")
        if not os.path.isdir(pc_dir):
            return []
        return [
            os.path.join(pc_dir, entry)
            for entry in os.listdir(pc_dir)
            if entry.endswith(".pc")
        ]

    def _make_pc_relocatable(self, pc_file):
        with open(pc_file, "r", encoding="utf-8") as handle:
            content = handle.read()
        content = re.sub(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r"^exec_prefix=.*$",
            "exec_prefix=${prefix}",
            content,
            flags=re.MULTILINE,
        )
        with open(pc_file, "w", encoding="utf-8") as handle:
            handle.write(content)
