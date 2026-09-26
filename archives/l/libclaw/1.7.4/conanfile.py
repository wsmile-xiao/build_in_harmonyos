#!/usr/bin/env python3
"""Conan recipe — libclaw 1.7.4 (CMake).

Claw ("C++ Library Absolutely Wonderful"): generalist C++ library with
containers, tweeners, 2D geometry, image I/O (bmp/jpeg/png/pcx/targa/xbm),
sockets, config files and logging.
Upstream: https://libclaw.sourceforge.net/ (SourceForge tarball).

OHOS adaptations:
  - CMAKE_POLICY_VERSION_MINIMUM=3.5 (toolchain + env): upstream
    cmake_minimum_required(2.6) is rejected by device CMake >= 4
    (same approach as devil/1.8.0, leptonica/1.87.0; knowledge E103).
  - 0001 bumps cmake_minimum_required(2.6) to 3.5 in the top-level and
    examples/tween CMakeLists.
  - 0002 (patches/0002-cxx11-cxx17-compat.patch) ports C++03-era code to
    the C++17 toolchain (ohos-aarch64 profile, compiler.cppstd=17):
    configuration_file.cpp uses static_cast<bool> on text::getline()
    (C++11 made istream's operator bool explicit, so copy-init fails),
    and functional.hpp drops the C++17-removed std::unary_function /
    std::binary_function bases while keeping argument_type/result_type
    typedefs (dawg/1.2 precedent).
  - 0003 (patches/0003-dependent-template-keyword.patch) adds the
    required 'template' keyword on dependent
    cast_value_type_to<U>() calls in claw/impl/rectangle.tpp and
    claw/impl/box_2d.tpp (two-phase lookup; old GCC accepted it,
    modern clang rejects without the keyword).
  - 0005 (NLS disable: OHOS musl provides no libintl at link time, so the
    .so files would carry undefined libintl_* symbols rejected by
    --no-allow-shlib-undefined (knowledge E027; dos2unix/diction
    precedent)) is implemented as a tolerant in-build() string
    replacement (_disable_nls, not a context patch): claw_gettext.hpp
    drops <libintl.h>, claw_gettext(s)->(s) and
    claw_ngettext(s,p,n)->((n)==1?(s):(p)); application.cpp drops the
    setlocale/bindtextdomain/bind_textdomain_codeset/textdomain calls
    by line-prefix filtering (the former strict patch claimed @@ -38
    while the constructor sits later after the CLAW_MK_STR macros, so
    apply_conandata_patches aborted with "source file is different").
    English fallback, no new dependency.
  - 0004 (patches/0004-boost-bind-rvalue-compat.patch) fixes
    tween/single_tweener.cpp for Boost 1.91: new Boost.Bind forwards
    the _1 placeholder as an rvalue, so local_swap's second parameter
    becomes by-value (the old swap-back only wrote the discarded
    temporary; plain assignment preserves behavior).
  - tween/easing/easing_elastic.cpp drops the
    <boost/math/constants/constants.hpp> include (subset boost/1.91.0
    ships no boost/math headers): pi comes from a hardcoded double
    literal, matching upstream master's own later fix. Implemented as a
    tolerant in-build() string replacement (not a context patch) so it
    never fails on whitespace drift or when already absent.
  - 0002 drops the global "-std=c++03" flag so the Conan toolchain
    C++ standard (C++17 from ohos-aarch64 profile) applies; required
    because Boost >= 1.84 headers need C++14 or newer. Implemented as a
    tolerant in-build() string replacement (not a context patch) because
    strict patch hunks fail on trivial context drift (this round:
    apply_conandata_patches reported "source file is different" with
    actual 'set( CLAW_APPLICATION_SOURCES').
  - JPEG/PNG are wired by absolute path (JPEG_INCLUDE_DIR/JPEG_LIBRARY,
    PNG_INCLUDE_DIR/PNG_LIBRARY) from the Conan packages instead of host
    probing; BOOST_ROOT points at the boost package so FindBoost resolves
    thread/system from Conan (stiff/opencv precedent).
  - CMAKE_INSTALL_LIBDIR=lib (upstream defaults to empty without
    GNUInstallDirs, which would install to "/").
  - Conan shared option is honoured in build(): upstream declares BOTH
    flavours unconditionally (add_library(claw_X SHARED ...) plus
    add_library(claw_X-static STATIC ...)) and installs both, ignoring
    BUILD_SHARED_LIBS. With shared=False (CI default) the unwanted SHARED
    targets still link against the static-only non-PIC zlib/1.3.1
    (./configure --static, no fPIC) and die on aarch64 with
    "relocation R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC"
    (knowledge E005). _respect_conan_shared_option() therefore rewrites
    the explicit SHARED keyword to STATIC when shared=False, so only
    static archives are produced (static creation never links, hence
    needs no PIC; the sibling claw_X-static target builds the same
    content). Tolerant regex, never fails when already absent.
  - CLAW_INSTALL_CMAKE_MODULES=OFF: skip upstream's legacy
    libclaw-config.cmake so consumers use the Conan-generated config.
  - ELF signing: the OHOS loader rejects unsigned .so at dlopen time;
    installed shared objects are self-signed with binary-sign-tool
    (libjpeg-turbo/3.0.4 precedent).
  - Upstream 1.7.4 ships no test suite (no enable_testing/add_test, no
    test/ dir; examples/ are demos). build() runs no upstream tests;
    the no_tests evidence marker is emitted by test_package every run
    (bwm/0.6.3 precedent) so cache hits still produce evidence.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibclawConan(ConanFile):
    name = "libclaw"
    version = "1.7.4"
    description = "Claw: generalist C++ library (containers, tweeners, 2D geometry, image I/O, sockets, config files)"
    license = "LGPL-2.1-or-later"
    homepage = "https://libclaw.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # Conan 2 requires 'shared' for package_type=library (graph validation).
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Public headers (claw/tween/base_tweener.hpp etc.) include
        # <boost/function.hpp> directly, so consumers need Boost headers
        # and libs transitively (yomm2/c10t precedent). Without
        # transitive_headers, test_package compiling against the installed
        # claw headers fails with 'boost/function.hpp file not found'.
        self.requires("boost/1.91.0", transitive_headers=True, transitive_libs=True)
        self.requires("libpng/1.6.39", transitive_headers=True, transitive_libs=True)
        self.requires("libjpeg-turbo/3.0.4", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libclaw is only supported on Linux/OHOS, not %s" % self.settings.os
            )

    def layout(self):
        cmake_layout(self)

    def _writable_tmpdir(self):
        """HMBS readonly_tmp: reuse injected writable tmpdir (minimal).

        Priority: HMBS_TMPDIR > HMBS_PLATFORM_CAPABILITIES.tmpdir >
        already-exported TMPDIR/TMP/TEMP (bare /tmp is read-only erofs,
        must be skipped) > HMBS_AUTOCONF_MKTEMP_FALLBACK >
        build_folder/tmp. Probe-writes; only replaces the temp-file root.
        """
        candidates = []
        for key in ("HMBS_TMPDIR",):
            value = os.environ.get(key)
            if value:
                candidates.append(value)
        capabilities = os.environ.get("HMBS_PLATFORM_CAPABILITIES")
        if capabilities:
            try:
                obj = json.loads(capabilities)
                if isinstance(obj, dict) and obj.get("tmpdir"):
                    candidates.append(str(obj["tmpdir"]))
            except Exception:
                pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(key)
            if value and value != "/tmp" and value not in candidates:
                candidates.append(value)
        fallback = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if fallback and fallback not in candidates:
            candidates.append(fallback)
        for base in (getattr(self, "build_folder", None),
                     getattr(self, "source_folder", None)):
            if base:
                candidates.append(os.path.join(str(base), "tmp"))
        for candidate in candidates:
            if not candidate:
                continue
            try:
                os.makedirs(candidate, exist_ok=True)
            except OSError:
                continue
            if not os.path.isdir(candidate):
                continue
            try:
                fd, probe = tempfile.mkstemp(dir=candidate)
                os.close(fd)
                os.unlink(probe)
                return candidate
            except OSError:
                continue
            except Exception:
                continue
        fallback_dir = os.path.join(str(self.build_folder), "tmp")
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir

    def _ensure_tmp_env(self):
        """Redirect temp files off read-only /tmp; pin shell to /bin/sh."""
        tmp = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        os.environ["SHELL"] = "/bin/sh"
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        try:
            os.umask(0o022)
        except Exception:
            pass
        return tmp

    def source(self):
        self._ensure_tmp_env()
        get(self, **self.conan_data["sources"], strip_root=True)

    def _runs_compiler(self, path):
        try:
            if not path or not os.path.isfile(path):
                return False
            r = subprocess.run([path, "--version"], capture_output=True,
                               text=True, timeout=20,
                               env=os.environ.copy())
            return r.returncode == 0
        except Exception:
            return False

    def _discover_ohos_compilers(self):
        """Pin a runnable C/CXX pair via toolchain variables (no file rewrite).

        Preflight worker drift: profile /data/service/hnp/bin/clang may be
        absent/unrunnable in sandbox (cmake identification unknown). Probe
        conf path with --version, else PATH names, else absolute fallbacks.
        Returns (c, cpp) or ("", "") when nothing usable is found.
        """
        try:
            cm = self.conf.get("tools.build:compiler_executables",
                               default={}, check_type=dict) or {}
        except Exception:
            cm = {}
        pc = cm.get("c", "") if isinstance(cm, dict) else ""
        pcpp = cm.get("cpp", "") if isinstance(cm, dict) else ""
        if pc and pcpp and self._runs_compiler(pc) and self._runs_compiler(pcpp):
            return pc, pcpp
        if pc or pcpp:
            self.output.warning("profile compiler not runnable: c=%s cpp=%s" % (pc, pcpp))
        for name_c, name_cpp in (("clang", "clang++"), ("cc", "c++"),
                                 ("gcc", "g++")):
            wc = shutil.which(name_c) or ""
            wcpp = shutil.which(name_cpp) or ""
            if wc and wcpp and self._runs_compiler(wc) and self._runs_compiler(wcpp):
                self.output.info("using PATH compilers: %s / %s" % (wc, wcpp))
                return wc, wcpp
        cc_env = os.environ.get("CC", "")
        cxx_env = os.environ.get("CXX", "")
        if cc_env and cxx_env and self._runs_compiler(cc_env) and self._runs_compiler(cxx_env):
            return cc_env, cxx_env
        for d in ("/storage/Users/currentUser/usr/local/bin",
                  "/data/service/hnp/bin",
                  "/usr/local/bin", "/usr/bin"):
            for pair in (("clang", "clang++"), ("cc", "c++")):
                c = os.path.join(d, pair[0])
                cpp = os.path.join(d, pair[1])
                if self._runs_compiler(c) and self._runs_compiler(cpp):
                    self.output.info("using absolute compilers: %s / %s" % (c, cpp))
                    return c, cpp
        return "", ""

    def _dep_artifacts(self, dep_name):
        dep = self.dependencies[dep_name]
        include_dir = ""
        for inc in dep.cpp_info.includedirs:
            if os.path.isdir(inc):
                include_dir = inc
                break
        if not include_dir:
            raise ConanException("could not resolve include dir of %s" % dep_name)
        lib_path = ""
        for lib in dep.cpp_info.libs:
            for libdir in dep.cpp_info.libdirs:
                for ext in (".so", ".a"):
                    candidate = os.path.join(libdir, "lib%s%s" % (lib, ext))
                    if os.path.isfile(candidate):
                        lib_path = candidate
                        break
                if lib_path:
                    break
            if lib_path:
                break
        if not lib_path:
            raise ConanException("could not resolve library file of %s" % dep_name)
        return include_dir, lib_path

    def generate(self):
        # Ensure --version probes run with writable TMPDIR (else a good
        # compiler can false-negative on read-only /tmp).
        self._ensure_tmp_env()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CLAW_INSTALL_CMAKE_MODULES"] = False
        tc.variables["CLAW_NO_JPEG"] = False
        tc.variables["CLAW_NO_PNG"] = False
        boost = self.dependencies["boost"]
        tc.variables["BOOST_ROOT"] = boost.package_folder
        png_inc, png_lib = self._dep_artifacts("libpng")
        jpg_inc, jpg_lib = self._dep_artifacts("libjpeg-turbo")
        tc.variables["JPEG_INCLUDE_DIR"] = jpg_inc
        tc.variables["JPEG_LIBRARY"] = jpg_lib
        tc.variables["PNG_INCLUDE_DIR"] = png_inc
        tc.variables["PNG_LIBRARY"] = png_lib
        tc.variables["PNG_PNG_INCLUDE_DIR"] = png_inc
        # Preflight drift: profile clang may be unrunnable in sandbox
        # (identification unknown). Discover a runnable pair and pin via
        # toolchain variables (no conan_toolchain.cmake rewrite).
        _disc_c, _disc_cpp = self._discover_ohos_compilers()
        if _disc_c and _disc_cpp:
            tc.variables["CMAKE_C_COMPILER"] = _disc_c
            tc.variables["CMAKE_CXX_COMPILER"] = _disc_cpp
            self.output.info("pinning discovered compilers: %s / %s" % (_disc_c, _disc_cpp))
        tc.generate()
        # HMBS readonly_tmp: propagate writable tmp root + /bin/sh so
        # compiler temp files never fall back to read-only /tmp. Only
        # replaces the temp-file root; no toolchain compiler rewrite.
        tmp = self._writable_tmpdir()
        hmbs_env = Environment()
        hmbs_env.define("TMPDIR", tmp)
        hmbs_env.define("TMP", tmp)
        hmbs_env.define("TEMP", tmp)
        hmbs_env.define("SHELL", "/bin/sh")
        hmbs_env.define("CONFIG_SHELL", "/bin/sh")
        for key in ("HMBS_AUTOCONF_MKTEMP_FALLBACK", "HMBS_CAP_LOCAL_MKTEMP",
                    "HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD", "HMBS_CAP_SYMLINK",
                    "HMBS_TMPDIR", "HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA",
                    "HMBS_PYTHON3"):
            value = os.environ.get(key)
            if value:
                hmbs_env.define(key, value)
        hmbs_env.vars(self, scope="build").save_script("hmbs_env")

    def _drop_cxx03_flag(self):
        # Tolerant removal of the upstream global "-std=c++03" flag
        # (top-level CMakeLists.txt). Exact whitespace/line-number drift
        # breaks strict context patches, so do plain substring replaces
        # and never fail when the flag is already absent.
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        if not os.path.isfile(cmake_lists):
            self.output.info("libclaw: top CMakeLists.txt not found, skip c++03 cleanup")
            return
        with open(cmake_lists, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        orig = content
        content = content.replace(
            'set (CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++03")',
            '# -std=c++03 removed: Conan toolchain selects C++ standard (C++17)')
        content = content.replace(
            'set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++03")',
            '# -std=c++03 removed: Conan toolchain selects C++ standard (C++17)')
        if content == orig and "-std=c++03" in content:
            content = content.replace("-std=c++03", "")
        if content != orig:
            with open(cmake_lists, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            self.output.info("libclaw: dropped hardcoded -std=c++03 flag")
        else:
            self.output.info("libclaw: no hardcoded -std=c++03 flag found, skipping")

    def _drop_boost_math_dep(self):
        # Tolerant removal of the boost/math/constants dependency in
        # claw/code/tween/easing/easing_elastic.cpp. The required
        # boost/1.91.0 package is a subset build (BOOST_INCLUDE_LIBRARIES
        # = filesystem;iostreams;program_options;regex;thread) whose
        # install tree contains no boost/math/ headers, so the upstream
        # #include fails with 'boost/math/constants/constants.hpp file
        # not found'. Upstream master itself later replaced the call with
        # a hardcoded pi literal; do the same via plain substring
        # replaces and never fail when already absent. Scans the whole
        # source tree for the same include so sibling easing files are
        # covered too; only the temp-file root is touched otherwise.
        pi_literal = ("3.14159265358979323846264338327950288"
                      "419716939937510582097494459230781640628620899L")
        fixed = []
        for root, _dirs, files in os.walk(self.source_folder):
            for name in files:
                if not name.endswith((".cpp", ".hpp", ".h", ".tpp", ".ipp")):
                    continue
                path = os.path.join(root, name)
                try:
                    with open(path, "r", encoding="utf-8",
                              errors="replace") as f:
                        content = f.read()
                except OSError:
                    continue
                if ("boost/math/constants/constants.hpp" not in content
                        and "boost::math::constants::pi" not in content):
                    continue
                orig = content
                content = content.replace(
                    "#include <boost/math/constants/constants.hpp>",
                    "// boost/math removed: subset Boost has no boost/math "
                    "headers; pi is a literal below")
                content = content.replace(
                    "boost::math::constants::pi<double>()", pi_literal)
                content = content.replace(
                    "boost::math::constants::pi<double> ()", pi_literal)
                if "boost/math/constants/constants.hpp" in content:
                    lines = content.splitlines(keepends=True)
                    lines = [ln for ln in lines
                             if "boost/math/constants/constants.hpp" not in ln]
                    content = "".join(lines)
                    if not content.endswith("\n"):
                        content += "\n"
                if content != orig:
                    with open(path, "w", encoding="utf-8",
                              newline="\n") as f:
                        f.write(content)
                    fixed.append(os.path.relpath(path, self.source_folder))
        if fixed:
            self.output.info("libclaw: dropped boost/math dep in %s"
                             % ", ".join(sorted(fixed)))
        else:
            self.output.info("libclaw: no boost/math/constants usage found, "
                             "skipping")

    def _disable_nls(self):
        # Tolerant NLS disable (replaces the former strict 0005 context
        # patch, whose application.cpp hunk claimed @@ -38 while the
        # constructor actually sits later, after the CLAW_MK_STR macros,
        # so apply_conandata_patches aborted with "source file is
        # different"). Plain substring/line-prefix replaces never fail on
        # line-number drift or when already absent. OHOS musl provides no
        # libintl at link time, so the .so files would carry undefined
        # libintl_* symbols rejected by --no-allow-shlib-undefined
        # (knowledge E027). English fallback, no new dependency.
        header = os.path.join(self.source_folder, "claw", "claw_gettext.hpp")
        if os.path.isfile(header):
            with open(header, "r", encoding="utf-8",
                      errors="replace") as f:
                content = f.read()
            orig = content
            content = content.replace(
                "#include <libintl.h>",
                "// NLS disabled: OHOS musl provides no libintl at link\n"
                "// time (E027); return original strings instead.")
            content = content.replace(
                '#define claw_gettext(s) dgettext( "libclaw", (s) )',
                "#define claw_gettext(s) (s)")
            content = content.replace(
                '#define claw_ngettext(s, p, n) '
                'dngettext( "libclaw", (s), (p), (n) )',
                "#define claw_ngettext(s, p, n) ((n) == 1 ? (s) : (p))")
            if content != orig:
                with open(header, "w", encoding="utf-8",
                          newline="\n") as f:
                    f.write(content)
                self.output.info("libclaw: NLS disabled in claw_gettext.hpp")
            else:
                self.output.info("libclaw: claw_gettext.hpp already NLS-free,"
                                 " skipping")
        else:
            self.output.info("libclaw: claw_gettext.hpp not found, skipping")
        app = os.path.join(self.source_folder, "claw", "code",
                           "application.cpp")
        if os.path.isfile(app):
            with open(app, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            kept = []
            removed = 0
            for ln in lines:
                stripped = ln.strip()
                if (stripped.startswith("setlocale(")
                        or stripped.startswith("bindtextdomain(")
                        or stripped.startswith("bind_textdomain_codeset(")
                        or stripped.startswith("textdomain(")):
                    removed += 1
                    continue
                kept.append(ln)
            content = "".join(kept)
            if "// NLS disabled" not in content:
                content = content.replace(
                    "  : m_arguments( argc, argv )\n{\n",
                    "  : m_arguments( argc, argv )\n{\n"
                    "  // NLS disabled: OHOS musl provides no libintl at "
                    "link time (E027).\n",
                    1)
            with open(app, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            self.output.info("libclaw: dropped %d NLS calls"
                             " in application.cpp" % removed)
        else:
            self.output.info("libclaw: application.cpp not found, skipping")

    def _strip_versioned_soname(self):
        # OHOS/HMDFS: upstream sets VERSION 1.7.4 / SOVERSION 1 on every
        # claw_* shared lib, producing libclaw_X.so -> .so.1 -> .so.1.7.4
        # symlink chains. The preflight rootfs (HMDFS/erofs, read-only /tmp
        # precedent) does not preserve those symlinks, so the musl loader
        # fails with "Error loading shared library libclaw_*.so.1" even
        # though the package installed fine (boost/1.91.0 avoids the same
        # via BOOST_INSTALL_NO_VERSIONED_LIBS). Drop the VERSION/SOVERSION
        # block tolerantly so only unversioned .so files (real files, no
        # symlinks) are built; DT_NEEDED then references the unversioned
        # name which is always present. Never fails when already absent.
        if str(self.settings.os) != "OHOS":
            return
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        if not os.path.isfile(cmake_lists):
            return
        with open(cmake_lists, "r", encoding="utf-8",
                  errors="replace") as f:
            content = f.read()
        orig = content
        # Remove the VERSION/SOVERSION set_target_properties block.
        lines = content.splitlines(keepends=True)
        out = []
        skip = 0
        for i, ln in enumerate(lines):
            s = ln.strip()
            if (s.startswith("set_target_properties(")
                    and i + 4 < len(lines)
                    and "VERSION ${CLAW_VERSION}" in "".join(lines[i:i+5])):
                skip = 5
                # Replace with a comment preserving line count roughly.
                out.append("# OHOS: versioned SONAME stripped; "
                           "unversioned .so only (no .so.1 symlinks)\n")
                continue
            if skip > 0:
                skip -= 1
                continue
            out.append(ln)
        content = "".join(out)
        # Fallback: plain substring removal if the block shape drifted.
        if content == orig and "SOVERSION ${CLAW_VERSION_MAJOR}" in content:
            content = content.replace(
                "    VERSION ${CLAW_VERSION}\n"
                "    SOVERSION ${CLAW_VERSION_MAJOR}\n", "")
            content = content.replace(
                "    VERSION ${CLAW_VERSION}\r\n"
                "    SOVERSION ${CLAW_VERSION_MAJOR}\r\n", "")
        if content != orig:
            with open(cmake_lists, "w", encoding="utf-8",
                      newline="\n") as f:
                f.write(content)
            self.output.info("libclaw: stripped versioned SONAME "
                             "(OHOS, no .so.1 symlinks)")
        else:
            self.output.info("libclaw: no VERSION/SOVERSION block found, "
                             "skipping")

    def _respect_conan_shared_option(self):
        # Upstream ignores BUILD_SHARED_LIBS: every claw_* lib is declared
        # twice (add_library(claw_X SHARED ...) + add_library(claw_X-static
        # STATIC ...)) and both flavours are installed. With Conan
        # shared=False (CI default) the unwanted SHARED link still runs and
        # pulls the static-only non-PIC zlib/1.3.1 (that recipe builds via
        # ./configure --static with no fPIC option, R26 system same-name
        # library, so its libz.a objects are not position-independent),
        # which lld on aarch64 rejects with:
        #   relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against
        #   symbol 'z_errmsg'; recompile with -fPIC (knowledge E005).
        # Fix: when shared=False, rewrite the explicit SHARED keyword of
        # the 7 non-suffixed targets to STATIC via a tolerant regex (never
        # fails when already absent or drifted). Static archive creation
        # performs no link, so no PIC is needed.
        # CI #54046 follow-up: the converted STATIC targets must NOT keep
        # the canonical OUTPUT_NAME. Upstream maps the sibling -static
        # target to the same OUTPUT_NAME (OUTPUT_NAME ${lib} +
        # CLEAN_DIRECT_OUTPUT 1), which is only safe for mixed flavours
        # (.so vs .a). Two STATIC targets with one OUTPUT_NAME race on
        # the same .a under parallel make (`make -j`, CI default):
        # duplicate `Linking CXX static library libclaw_X.a` then
        # `llvm-ranlib: unable to load 'libclaw_X.a': No such file`.
        # So the converted targets get a distinct OUTPUT_NAME
        # (<lib>_shared_compat); the -static siblings keep the canonical
        # libclaw_X.a that consumers link. Both install() rules stay valid
        # (extra _shared_compat.a files are harmless). shared=True keeps
        # upstream behaviour untouched.
        # stay valid because every target still exists. shared=True keeps
        # upstream behaviour untouched.
        try:
            shared = bool(self.options.shared)
        except Exception:
            self.output.info("libclaw: shared option unreadable, "
                             "skipping flavour gating")
            return
        if shared:
            self.output.info("libclaw: shared=True, keeping upstream "
                             "dual-flavour build")
            return
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        if not os.path.isfile(cmake_lists):
            self.output.info("libclaw: top CMakeLists.txt not found, "
                             "skip flavour gating")
            return
        with open(cmake_lists, "r", encoding="utf-8",
                  errors="replace") as f:
            content = f.read()
        orig = content
        libs = ("claw_application|claw_configuration_file|"
                "claw_dynamic_library|claw_graphic|claw_logger|"
                "claw_net|claw_tween")
        pattern = re.compile(
            r"add_library\s*\(\s*(%s)\s+SHARED\b" % libs)
        content, count = pattern.subn(r"add_library( \1 STATIC", content)
        if content != orig:
            # Disambiguate archive names so the converted STATIC targets do
            # not race the -static siblings on the same .a file. Appended
            # footer wins over the in-loop OUTPUT_NAME mapping; guarded by
            # marker for idempotence across re-runs on a dirty source tree.
            marker = "HMBS shared=False static OUTPUT_NAME disambiguation"
            if marker not in content:
                lib_names = libs.split("|")
                footer_lines = [
                    "",
                    "# %s: converted SHARED->STATIC targets need a distinct" % marker,
                    "# archive name; otherwise both flavours emit lib<name>.a",
                    "# in one dir and parallel make corrupts/renames it",
                    "# (CI #54046 llvm-ranlib No such file).",
                    "if(NOT BUILD_SHARED_LIBS)",
                ]
                for lib_name in lib_names:
                    footer_lines.append(
                        '  set_target_properties(%s PROPERTIES OUTPUT_NAME %s_shared_compat)'
                        % (lib_name, lib_name))
                footer_lines.append("endif()")
                footer_lines.append("")
                if not content.endswith("\n"):
                    content += "\n"
                content += "\n".join(footer_lines)
            with open(cmake_lists, "w", encoding="utf-8",
                      newline="\n") as f:
                f.write(content)
            self.output.info("libclaw: flavour-gated %d SHARED -> STATIC "
                             "targets (Conan shared=False, avoids non-PIC "
                             "static zlib link, E005)" % count)
        else:
            self.output.info("libclaw: no explicit SHARED targets found, "
                             "skipping flavour gating")

    def build(self):
        tmp = self._ensure_tmp_env()
        # Sync CC/CXX to the runnable pair so cmake probe and any direct
        # compiler calls avoid a dead profile absolute path.
        _bc, _bcpp = self._discover_ohos_compilers()
        if _bc and _bcpp:
            os.environ["CC"] = _bc
            os.environ["CXX"] = _bcpp
        apply_conandata_patches(self)
        self._disable_nls()
        self._drop_cxx03_flag()
        self._drop_boost_math_dep()
        self._strip_versioned_soname()
        self._respect_conan_shared_option()
        env = Environment()
        env.define("CMAKE_POLICY_VERSION_MINIMUM", "3.5")
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        env.define("SHELL", "/bin/sh")
        env.define("CONFIG_SHELL", "/bin/sh")
        if os.environ.get("CC"):
            env.define("CC", os.environ["CC"])
        if os.environ.get("CXX"):
            env.define("CXX", os.environ["CXX"])
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._materialize_versioned_libs(
            os.path.join(self.package_folder, "lib"))
        self._sign_shared_libs(os.path.join(self.package_folder, "lib"))

    def _tool_in_compiler_dir(self, tool):
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        for key in ("cpp", "c"):
            compiler = (executables or {}).get(key)
            if not compiler:
                continue
            compiler_dir = os.path.dirname(compiler)
            for candidate in (os.path.join(compiler_dir, tool), os.path.join(compiler_dir, "llvm-" + tool)):
                if os.path.isfile(candidate):
                    return candidate
        return shutil.which(tool)

    def _materialize_versioned_libs(self, lib_dir):
        # Safety net for caches built before _strip_versioned_soname: if a
        # versioned real file exists (e.g. libclaw_tween.so.1.7.4) but the
        # .so.1 symlink was lost on HMDFS, copy it to the expected SONAME
        # paths so the musl loader (which ignores RPATH and relies on
        # LD_LIBRARY_PATH) can resolve DT_NEEDED. Never fails.
        if not os.path.isdir(lib_dir):
            return
        try:
            names = os.listdir(lib_dir)
        except OSError:
            return
        for name in sorted(names):
            if ".so." not in name:
                continue
            src = os.path.join(lib_dir, name)
            if os.path.islink(src) or not os.path.isfile(src):
                continue
            # e.g. libclaw_tween.so.1.7.4 -> libclaw_tween.so.1, .so
            base = name.split(".so")[0] + ".so"
            cands = [base + ".1", base]
            for dst_name in cands:
                dst = os.path.join(lib_dir, dst_name)
                if os.path.lexists(dst):
                    continue
                try:
                    shutil.copy2(src, dst)
                    self.output.info("libclaw: materialized %s from %s"
                                     % (dst_name, name))
                except OSError as exc:
                    self.output.warning("libclaw: copy %s -> %s failed: %s"
                                        % (name, dst_name, exc))

    def _sign_shared_libs(self, lib_dir):
        if str(self.settings.os) != "OHOS":
            return
        if not os.path.isdir(lib_dir):
            return
        sos = []
        sos += glob.glob(os.path.join(lib_dir, "*.so"))
        sos += glob.glob(os.path.join(lib_dir, "*.so.*"))
        sos = [p for p in sos if not os.path.islink(p)]
        if not sos:
            return
        objcopy = self._tool_in_compiler_dir("objcopy")
        if not objcopy:
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = self._tool_in_compiler_dir("binary-sign-tool")
        if not signer:
            signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sorted(sos):
            self.run('%s --remove-section .codesign "%s" 2>/dev/null || true' % (objcopy, so), ignore_errors=True)
            self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (signer, so, so))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libclaw")
        self.cpp_info.set_property("cmake_target_name", "libclaw::libclaw")
        self.cpp_info.libs = [
            "claw_application",
            "claw_configuration_file",
            "claw_dynamic_library",
            "claw_graphic",
            "claw_logger",
            "claw_net",
            "claw_tween",
        ]
        self.cpp_info.requires = [
            "boost::thread",
            "boost::headers",
            "libpng::libpng",
            "libjpeg-turbo::libjpeg-turbo",
            "zlib::zlib",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread"]
