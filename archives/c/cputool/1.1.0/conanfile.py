#!/usr/bin/env python3
"""Conan recipe — cputool 1.1.0 (Meson).

CPUTool is a utility which manages CPU usage and system load using
SIGSTOP/SIGCONT signals. Single C program (cputool.c), no external
dependencies. Upstream ships no test suite (no meson test() targets,
CI only builds); functional coverage is provided by test_package.
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class CputoolConan(ConanFile):
    name = "cputool"
    version = "1.1.0"
    description = "CPUTool - utility which manages CPU usage and system load"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.linux.community/cputool/cputool/"
    url = "https://gitlab.linux.community/cputool/cputool/"
    topics = ("cpu", "system", "cli")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cputool 1.1.0 is adapted for Linux/OHOS, got %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: executable-only package, keep the static default (upstream
        # defines no library targets, so this only guards future ones).
        tc.project_options["default_library"] = "static"
        # Upstream man pages need rst2man (python3-docutils), which is not
        # available on OHOS; skip the docs subdir. The companion patch also
        # makes the rst2man lookup non-fatal when docs are disabled.
        tc.project_options["docs"] = "disabled"
        tc.generate()
        self._fix_meson_compilers()

    def _resolve_real_clang(self, path):
        # OHOS SDK 'clang' may be a /bin/sh wrapper script which conan's
        # subprocess domain cannot execute (SELinux). Prefer the real
        # clang-<N> ELF sibling when the candidate is a script.
        try:
            if not path or not os.path.isfile(path):
                return path
            with open(path, "rb") as f:
                head = f.read(2)
            if head != b"#!":
                return path
        except OSError:
            return path
        bindir = os.path.dirname(os.path.realpath(path))
        try:
            cands = []
            for name in os.listdir(bindir):
                if name.startswith("clang-") and name[6:].isdigit():
                    cand = os.path.join(bindir, name)
                    try:
                        with open(cand, "rb") as f:
                            if f.read(4) == b"\x7fELF":
                                cands.append(cand)
                    except OSError:
                        continue
            if cands:
                return sorted(cands)[-1]
        except OSError:
            pass
        return path

    def _find_tool(self, kind):
        # kind: "c" or "cpp". Return an existing executable path or None.
        # Order: profile conf -> CC/CXX env -> PATH -> versioned hnp
        # binaries -> OHOS SDK llvm dir (fixed + glob). No invention of
        # new toolchains: only well-known OHOS layouts already used in
        # this repo (ci profile / ohos-sdk.org).
        conf = {}
        try:
            conf = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            conf = {}
        base = "clang" if kind == "c" else "clang++"
        candidates = []
        if conf.get(kind):
            candidates.append(conf.get(kind))
        env_key = "CC" if kind == "c" else "CXX"
        if os.environ.get(env_key):
            candidates.append(os.environ.get(env_key))
        w = shutil.which(base)
        if w:
            candidates.append(w)
        candidates.append("/data/service/hnp/bin/" + base)
        candidates.extend(sorted(
            glob.glob("/data/service/hnp/bin/" + base + "-[0-9]*")))
        candidates.append(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/"
            "native/llvm/bin/" + base)
        candidates.extend(sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/"
            + base)))
        candidates.extend(sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/"
            + base + "-[0-9]*")))
        for cand in candidates:
            if cand and os.path.isfile(cand):
                real = self._resolve_real_clang(cand)
                if os.path.isfile(real):
                    return real
        return None

    def _fix_meson_compilers(self):
        # Preflight evidence: MesonToolchain wrote
        # c = '/data/service/hnp/bin/clang' but that file was absent on
        # the device, so meson configure failed with
        # "Unknown compiler(s): [['/data/service/hnp/bin/clang']]".
        # When the profile path is missing, fall back to the discoverable
        # clang in well-known OHOS layouts and rewrite both machine files.
        # No-op when the profile compilers already exist (CI path).
        conf = {}
        try:
            conf = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            conf = {}
        conf_c = conf.get("c", "")
        conf_cpp = conf.get("cpp", "")

        def _usable(p):
            p = self._resolve_real_clang(p) if p else p
            return p if p and os.path.isfile(p) else None

        real_c = _usable(conf_c) or self._find_tool("c")
        real_cpp = _usable(conf_cpp) or self._find_tool("cpp")
        # Single-C project: cpp fallback may reuse the C driver sibling.
        if not real_cpp and real_c:
            sib = os.path.join(os.path.dirname(real_c), "clang++")
            if os.path.isfile(sib):
                real_cpp = self._resolve_real_clang(sib)
        if not real_c:
            self.output.warning(
                "cputool: no usable C compiler found; leaving Meson "
                "machine files untouched")
            return
        if _usable(conf_c) and _usable(conf_cpp):
            self.output.info(
                "cputool: profile compilers exist, no Meson fix needed")
            # Still ensure ar is present for future library targets.
        else:
            self.output.info(
                "cputool: patching Meson machine files to usable "
                "compilers: c=%s cpp=%s (profile was c=%s cpp=%s)"
                % (real_c, real_cpp or conf_cpp, conf_c, conf_cpp))
        replacements = {}
        if real_c and real_c != conf_c:
            replacements["c"] = real_c
        if real_cpp and real_cpp != conf_cpp:
            replacements["cpp"] = real_cpp
        # Derive llvm-ar/llvm-ranlib from the real compiler dir (same
        # approach as cairo/cexception: Meson does not get ar from conf).
        ar = None
        ranlib = None
        try:
            ar_conf = conf.get("ar")
            if ar_conf and os.path.isfile(ar_conf):
                ar = ar_conf
        except Exception:
            pass
        if not ar and real_c:
            cand = os.path.join(os.path.dirname(real_c), "llvm-ar")
            if os.path.isfile(cand):
                ar = cand
                rcand = os.path.join(os.path.dirname(real_c), "llvm-ranlib")
                if os.path.isfile(rcand):
                    ranlib = rcand
        if not ar:
            for cand in ("/data/service/hnp/bin/llvm-ar",
                         "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                         "ohos/native/llvm/bin/llvm-ar"):
                if os.path.isfile(cand):
                    ar = cand
                    break
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as f:
                content = f.read()
            orig = content
            for key, val in replacements.items():
                v = val.replace("\\", "/")
                content, n = re.subn(
                    r"(?m)^\s*" + key + r"\s*=\s*'[^']*'",
                    "%s = '%s'" % (key, v), content, count=1)
                if n == 0:
                    # Some generators emit double quotes.
                    content, _ = re.subn(
                        r'(?m)^\s*' + key + r'\s*=\s*"[^"]*"',
                        '%s = "%s"' % (key, v), content, count=1)
            if ar and "\nar =" not in content and "\nar=" not in content \
                    and "[binaries]" in content:
                ins = "[binaries]\nar = '%s'\n" % ar.replace("\\", "/")
                if ranlib:
                    ins += "ranlib = '%s'\n" % ranlib.replace("\\", "/")
                content = content.replace("[binaries]\n", ins, 1)
            if content != orig:
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
        # Export for any subprocess that honours env (defensive only;
        # Meson itself reads the machine files above).
        os.environ["CC"] = real_c
        if real_cpp:
            os.environ["CXX"] = real_cpp

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # No upstream test suite: meson.build defines only executable(cputool)
        # plus docs, with no test() targets, so there is no `meson test` to
        # run here. Functional coverage is provided by
        # test_package/test_cputool.sh.

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
