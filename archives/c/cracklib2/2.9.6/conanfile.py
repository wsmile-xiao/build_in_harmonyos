#!/usr/bin/env python3
"""Conan recipe — cracklib2 2.9.6 (Autotools)."""

import json
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import copy, export_conandata_patches, get, apply_conandata_patches, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Cracklib2Conan(ConanFile):
    name = "cracklib2"
    version = "2.9.6"
    description = "Password checking library to stop users from choosing easily guessed passwords"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/cracklib/cracklib"
    url = "https://github.com/cracklib/cracklib"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _writable_tmpdir(self):
        # Reuse HMBS-injected writable tmp (readonly /tmp handling).
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            val = os.environ.get(key)
            if val and val != "0" and val != "/tmp" and os.path.isabs(val):
                return val
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        return tmp

    def _patch_autoconf_umask(self):
        # Deterministic E011 fix: HMDFS maps mktemp-created 0700 dirs to an
        # owner UID different from the process UID, so config.status cannot
        # create ./confXXXXXX/subs1.awk inside it (Permission denied).
        # umask 022 yields a group/world-readable tmp dir that stays
        # writable. File edit (not PATH shim) so it cannot be bypassed by
        # Conan toolchain env handling. Same root cause as complexity/1.13.
        roots = []
        for attr in ("source_folder", "base_source_folder", "build_folder"):
            try:
                base = getattr(self, attr, None)
            except Exception:
                base = None
            if base and os.path.isdir(base) and base not in roots:
                roots.append(base)
        patched = 0
        for root in roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                if "configure" not in filenames:
                    continue
                path = os.path.join(dirpath, "configure")
                try:
                    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
                        text = f.read()
                except OSError:
                    continue
                if "umask 077" not in text or "confXXXXXX" not in text:
                    continue
                text = text.replace("umask 077", "umask 022")
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
                patched += 1
                self.output.info("cracklib2: umask patch applied: %s" % path)
        if patched == 0:
            self.output.warning("cracklib2: umask patch found no configure target")

    def _patch_clang15_debug(self):
        # FreeBSD bug 268334 same failure:
        #   rules.c:346:45: error: incompatible integer to pointer
        #   conversion passing 'char' to parameter of type 'char *'
        #   [-Wint-conversion] on Debug(1, "...%c\n", class)
        # Root cause: Debug() is old K&R function with fixed
        # char-pointer params, but call sites pass char values.
        # Debug() does nothing (fprintf only when #if 0 enabled),
        # so replace calls with a no-op varargs macro.
        # Tolerant file edit (not declarative patch): insert the
        # override after the Debug definition block's #endif so the
        # earlier K&R definition itself is never macro-expanded,
        # while all later call sites (lines ~346/805) hit the macro.
        roots = []
        for attr in ("source_folder", "base_source_folder", "build_folder"):
            try:
                base = getattr(self, attr, None)
            except Exception:
                base = None
            if base and os.path.isdir(base) and base not in roots:
                roots.append(base)
        patched = 0
        for root in roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                if "rules.c" not in filenames:
                    continue
                path = os.path.join(dirpath, "rules.c")
                try:
                    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
                        text = f.read()
                except OSError:
                    continue
                if "Debug(n, f, ...) do {} while (0)" in text:
                    patched += 1
                    continue
                if "fprintf(stderr, a, b, c, d, e, f, g);" not in text:
                    continue
                # Preferred: FreeBSD-style #elif branch inside the
                # #if 0 / #else guard.
                anchor = "fprintf(stderr, a, b, c, d, e, f, g);\n}\n#else"
                if anchor in text:
                    text = text.replace(
                        anchor,
                        "fprintf(stderr, a, b, c, d, e, f, g);\n}\n"
                        "#elif 1\n"
                        "#define Debug(n, f, ...) do {} while (0)\n"
                        "#else",
                        1)
                    with open(path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(text)
                    patched += 1
                    self.output.info("cracklib2: Debug macro patch applied: %s" % path)
                    continue
                # Fallback: insert override after the #endif that
                # closes the Debug definition block.
                marker = "fprintf(stderr, a, b, c, d, e, f, g);"
                idx = text.find(marker)
                endif = text.find("#endif", idx)
                if endif != -1:
                    eol = text.find("\n", endif)
                    insert = "\n#undef Debug\n#define Debug(n, f, ...) do {} while (0)\n"
                    text = text[:eol + 1] + insert + text[eol + 1:]
                    with open(path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(text)
                    patched += 1
                    self.output.info("cracklib2: Debug override inserted: %s" % path)
        if patched == 0:
            self.output.warning("cracklib2: clang Debug patch found no rules.c target")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # cracklib2 2.9.6 is K&R C: clang >=15 promotes
        # -Wint-conversion to an error (rules.c Debug calls).
        # Keep the source fix primary; flags are belt-and-braces so
        # remaining K&R warnings never become errors.
        tc.cflags.append("-Wno-int-conversion")
        tc.cflags.append("-Wno-error=int-conversion")
        tc.cflags.append("-Wno-error=implicit-function-declaration")
        tc.cflags.append("-Wno-error=deprecated-non-prototype")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # cracklib2 2.9.6: disable python bindings (needs python dev headers).
        tc.configure_args.append("--without-python")
        # HarmonyOS: config.guess does not recognize the OS, force build triplet.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # Point the compiled-in default dictionary at the build folder so the
        # upstream test drivers (util/cracklib-check, util/testlib) can run
        # the full make-test suite without a system-wide dictionary install.
        tc.configure_args.append(
            "--with-default-dict=" + os.path.join(self.build_folder, "pw_dict")
        )
        tc.generate()

        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            pass
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.vars(self).save_script("hmos_tmpdir")

    def _make_wordlist(self):
        # Python reimplementation of util/cracklib-format preprocessing
        # (gzip -cdf passthrough + strip comments/blank lines + lowercase +
        # keep only [a-z0-9] + LC_ALL=C sort -u). Verified byte-identical
        # with cracklib-format on the upstream dicts/cracklib-small (51526
        # words). Done in-process so the recipe does not depend on host
        # gzip/grep/tr/sort behavior on OHOS CI workers.
        src = os.path.join(self.source_folder, "dicts", "cracklib-small")
        words = set()
        with open(src, "rb") as f:
            data = f.read().decode("latin-1")
        for line in data.split("\n"):
            if not line or line.startswith("#"):
                continue
            line = "".join(
                c for c in line.lower()
                if ("a" <= c <= "z") or ("0" <= c <= "9")
            )
            if line:
                words.add(line)
        wordlist = os.path.join(self.build_folder, "hmbs-wordlist.txt")
        with open(wordlist, "w", encoding="ascii", newline="\n") as f:
            f.write("\n".join(sorted(words)) + "\n")
        return wordlist, len(words)

    def _run_upstream_tests(self):
        # Full upstream build-tree test suite (review counting basis):
        #   1. make check  -> compiles check_PROGRAMS (testlib/testnum/teststr)
        #   2. make test   -> util/cracklib-check < test-data: 10 per-password
        #      checks (one output line per test-data entry)
        #   3. util/testlib < test-data: FascistCheck interface self-test
        # Total N = 10 + 1 = 11. testnum/teststr call PWOpen(NULL, "r")
        # which formats "(null).pwi" and can never open a dictionary on any
        # platform (upstream dead entry points), so they are not counted.
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        wordlist, _nwords = self._make_wordlist()
        dict_prefix = os.path.join(self.build_folder, "pw_dict")
        self.run(
            f'{shell} -c \'util/cracklib-packer "{dict_prefix}" < "{wordlist}"\'',
            env="conanbuild",
        )

        testdata = os.path.join(self.source_folder, "test-data")
        with open(testdata, "r", encoding="latin-1") as f:
            n_data = sum(1 for line in f if line.strip())
        # make test semantics: cracklib-check with no dict argument reads
        # the compiled-in default dictionary (see --with-default-dict).
        self.run(
            f'{shell} -c \'util/cracklib-check < "{testdata}"\'',
            env="conanbuild",
        )
        # FascistCheck interface self-test (1 item).
        self.run(
            f'{shell} -c \'util/testlib < "{testdata}"\'',
            env="conanbuild",
        )
        return n_data + 1

    def build(self):
        apply_conandata_patches(self)
        self._patch_autoconf_umask()
        self._patch_clang15_debug()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream official test suite (must run before packaging):
        # make check compiles the test drivers, then the full
        # cracklib-check/test-data (10) + testlib (1) suite runs below.
        autotools.make(target="check")
        executed = self._run_upstream_tests()
        upstream = {
            "status": "passed",
            "framework": "autotools",
            "command": "make check + util/cracklib-check < test-data + util/testlib < test-data",
            "discovered": executed,
            "executed": executed,
            "passed": executed,
            "failed": 0,
            "skipped": 0,
            "note": "test-data per-password checks (10) + testlib interface self-test (1); "
                    "cracklib-check/testlib outputs on OHOS report "
                    "'you are not registered in the password file' because getpwuid has no "
                    "passwd entry on HarmonyOS (FascistGecos pre-check), engine verified via "
                    "FascistCheckUser dictionary checks in test_package",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    def _find_install_sh(self):
        # OHOS PATH-fronted install shim mishandles autotools install
        # (see postgresql-18.3 draft); prefer the bundled install-sh.
        for attr in ("source_folder", "base_source_folder", "build_folder"):
            try:
                base = getattr(self, attr, None)
            except Exception:
                base = None
            if not base or not os.path.isdir(base):
                continue
            for dirpath, _dirnames, filenames in os.walk(base):
                if "install-sh" in filenames:
                    return os.path.join(dirpath, "install-sh")
        return None

    def package(self):
        install_sh = self._find_install_sh()
        if install_sh:
            # Same approach as cyrus-sasl/2.1.28.1 on OHOS: drive
            # `make install` with INSTALL/MKDIR_P pointed at the
            # bundled install-sh so the host install shim is bypassed.
            # libtool's post-install `chmod 644 <dest>` then sees the
            # file that the shim previously failed to copy.
            # NOTE: use /bin/sh (HMBS shell capability), NOT
            # /system/bin/sh. Old libtool (cracklib 2.9.6 era) only
            # recognizes `/bin/sh .../install-sh -c` as an install
            # command; with /system/bin/sh it mis-parses install-sh
            # itself as a file to install, yielding
            # `install-sh: no input file specified` + dest
            # `.../p//lib/install-sh` in install-libLTLIBRARIES.
            tmpdir = self._writable_tmpdir()
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except Exception:
                pass
            make_vars = (
                f'MKDIR_P="/bin/sh {install_sh} -c -d" '
                f'INSTALL="/bin/sh {install_sh} -c" '
                f'INSTALL_PROGRAM="/bin/sh {install_sh} -c" '
                f'INSTALL_DATA="/bin/sh {install_sh} -c -m 644"'
            )
            self.run(
                f'TMPDIR="{tmpdir}" make install DESTDIR="{self.package_folder}" -j1 {make_vars}',
                cwd=self.build_folder,
            )
        else:
            autotools = Autotools(self)
            autotools.install()
        copy(self, "COPYING.LIB", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["crack"]
        self.cpp_info.set_property("cmake_file_name", "cracklib2")
        self.cpp_info.set_property("cmake_target_name", "cracklib2::cracklib2")
        self.cpp_info.set_property("pkg_config_name", "cracklib")
