#!/usr/bin/env python3
"""Conan recipe for lowdown 3.1.1.

lowdown is a Markdown processing library (liblowdown) and CLI tool written in
C.  It converts Markdown to HTML, LaTeX, roff (man/mdoc/ms), Gemini,
OpenDocument (fodt), terminal, and a syntax tree.

Upstream uses a BSD Makefile (.ifdef/.for conditionals) driven by a POSIX
``configure`` shell script.  GNU make cannot parse it, so the recipe
``tool_requires`` bmake.

Official upstream: https://kristaps.bsd.lv/lowdown/
License: ISC
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

required_conan_version = ">=2.0"


class LowdownConan(ConanFile):
    name = "lowdown"
    version = "3.1.1"
    description = "Markdown processing library and CLI (liblowdown + lowdown)"
    license = "ISC"
    homepage = "https://kristaps.bsd.lv/lowdown/"
    url = ""

    # library + CLI: ship both the static/shared lib and the lowdown binary
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_cli": [True, False],
    }
    default_options = {
        "shared": False,
        "with_cli": True,
    }

    # VirtualBuildEnv puts tool_requires (bmake) on PATH in the conanbuild env.
    generators = "VirtualBuildEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # zero external runtime deps

    def build_requirements(self):
        # lowdown's Makefile is BSD make (.ifdef/.for); GNU make cannot parse it.
        self.tool_requires("bmake/20200710")

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def configure(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "lowdown conanfile targets OHOS; os={} not supported"
                .format(self.settings.os)
            )

    def generate(self):
        # OHOS SDK lld dynamically links libxml2.so.16 from <sdk>/llvm/lib.
        # If that dir is absent from LD_LIBRARY_PATH, lld fails to start during
        # bmake's compile/link steps and regress, so link-dependent probes
        # silently degrade.  Prepend it to the *conanbuild* scope so every
        # self.run(env="conanbuild") below (bmake liblowdown.a/.so, lowdown,
        # lowdown.pc, and `bmake regress`) inherits it.  (configure runs via
        # subprocess, not self.run — it is handled separately in
        # _clean_env_for_configure.)  _usable_sdk_llvm_libdir also runs the
        # `lld --version` probe here; if lld cannot even start, fail loudly
        # instead of letting configure mis-detect HAVE_*.
        sdk_lib = self._usable_sdk_llvm_libdir()
        if sdk_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path: {sdk_lib}"
            )
            env = Environment()
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
            env.vars(self, scope="build").save_script("conanbuild_lld_rpath")

    def _sdk_llvm_libdir(self):
        """Locate the OHOS SDK llvm/lib dir that ships libxml2.so.16.

        lld (the SDK linker) dynamically links libxml2.so.16; if that lib is
        not on LD_LIBRARY_PATH, lld fails to start and every configure link
        probe silently degrades to "feature unavailable" — which is exactly
        what mis-detects HAVE_GETPROGNAME / HAVE_PROGRAM_INVOCATION_SHORT_NAME
        / HAVE___PROGNAME as 0, ultimately tripping compats.c's
        "#error No getprogname available."
        """
        if str(self.settings.os) != "OHOS":
            return ""

        compilers = self._ce()
        cc = compilers.get("c") or compilers.get("cpp")
        candidates = []
        if cc:
            compiler = os.path.realpath(cc)
            # clang -print-resource-dir → <sdk>/llvm/lib/clang/<ver>;
            # two levels up is <sdk>/llvm/lib, which holds libxml2.so.16.
            try:
                resource_dir = subprocess.check_output(
                    [cc, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass
            # Fallback: compiler lives in <sdk>/llvm/bin → lib is a sibling.
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )

        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def _usable_sdk_llvm_libdir(self):
        """Return a verified SDK llvm/lib dir, or raise.

        Probes ``lld --version`` with that dir on LD_LIBRARY_PATH; if lld
        cannot even start (missing libxml2.so.16), fail loudly instead of
        letting configure silently mis-detect capabilities.
        """
        if str(self.settings.os) != "OHOS":
            return ""

        cached = getattr(self, "_checked_sdk_llvm_libdir", None)
        if cached is not None:
            return cached

        sdk_llvm_lib = self._sdk_llvm_libdir()
        if not sdk_llvm_lib:
            raise ConanInvalidConfiguration(
                "Cannot locate the OHOS SDK llvm/lib containing "
                "libxml2.so.16 from the configured CC; set "
                "tools.build:compiler_executables:c to the SDK clang."
            )

        lld = os.path.join(os.path.dirname(sdk_llvm_lib), "bin", "lld")
        probe_env = os.environ.copy()
        old_ld = probe_env.get("LD_LIBRARY_PATH", "")
        probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (sdk_llvm_lib, old_ld) if part
        )
        try:
            probe = subprocess.run(
                [lld, "-flavor", "gnu", "--version"],
                env=probe_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(
                f"Cannot execute the OHOS SDK linker {lld}: {error}"
            ) from error
        if probe is not None and probe.returncode == 0:
            self._checked_sdk_llvm_libdir = sdk_llvm_lib
            return sdk_llvm_lib
        raise ConanInvalidConfiguration(
            f"The active OHOS SDK linker failed its GNU-flavor probe: {lld}; "
            f"stderr={probe.stderr.strip()!r}"
        )

    def _ce(self):
        return self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )

    def _cc(self):
        cc = self._ce().get("c", "clang")
        return cc if shutil.which(cc) else shutil.which("clang") or "clang"

    def _ar(self):
        ar = self._ce().get("ar", "llvm-ar")
        return ar if shutil.which(ar) else shutil.which("llvm-ar") or "ar"

    def _ranlib(self):
        rl = self._ce().get("ranlib", "llvm-ranlib")
        return rl if shutil.which(rl) else shutil.which("ranlib") or "ranlib"

    def _bmake_bin(self):
        # bmake is a tool_requires; in Conan 2 the VirtualBuildEnv puts it on
        # PATH in the conanbuild environment.  Return bare "bmake" —
        # self.run(env="conanbuild") resolves it at execution time.
        return "bmake"

    def _makesyspath(self):
        msp = os.environ.get("MAKESYSPATH", "")
        if msp and os.path.isdir(msp):
            return msp
        bmake = shutil.which("bmake")
        if bmake:
            base = os.path.dirname(os.path.dirname(bmake))
            for sub in ("share/mk", "share"):
                cand = os.path.join(base, sub)
                if os.path.isdir(cand):
                    return cand
        return None

    def _clean_env_for_configure(self):
        """Build a clean env for the configure subprocess call.

        Conan 2's self.run() injects the profile's [env] section, which sets
        CONFIG_SHELL=/data/service/hnp/bin/bash (non-existent on this machine)
        and overrides PATH.  That breaks bash fd-3 redirects in ./configure
        ("Bad file descriptor" at line 561).  By using subprocess directly
        with the full host env (only overriding CONFIG_SHELL), we bypass
        Conan's env injection entirely.  CC/AR/RANLIB are passed as CLI args
        to configure (written to Makefile.configure).
        """
        env = os.environ.copy()
        env["CONFIG_SHELL"] = shutil.which("bash") or "/bin/bash"
        env["LC_ALL"] = "C.UTF-8"
        msp = self._makesyspath()
        if msp:
            env["MAKESYSPATH"] = msp
        # configure runs via subprocess (NOT self.run), so the conanbuild
        # scope script written by generate() is NOT inherited here.  Inject
        # the SDK llvm/lib dir manually so lld can resolve libxml2.so.16
        # during configure's link probes — otherwise HAVE_GETPROGNAME /
        # HAVE_PROGRAM_INVOCATION_SHORT_NAME / HAVE___PROGNAME all collapse
        # to 0 and compats.c later trips "#error No getprogname available."
        sdk_lib = self._usable_sdk_llvm_libdir()
        if sdk_lib:
            old_ld = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (sdk_lib, old_ld) if part
            )
        return env

    def _run_subprocess(self, cmd, cwd=None, env=None):
        """Run a command via subprocess with a controlled env, streaming output."""
        self.output.info(f"RUN: {cmd}")
        result = subprocess.run(
            cmd,
            cwd=cwd or self.source_folder,
            env=env,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.stdout:
            self.output.write(result.stdout)
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                f"Command failed (exit {result.returncode}): {cmd}"
            )

    def build(self):
        apply_conandata_patches(self)

        cc = self._cc()
        ar = self._ar()
        ranlib = self._ranlib()
        bmake = self._bmake_bin()
        msp = self._makesyspath()
        prefix = self.package_folder
        sf = self.source_folder

        # Resolve bash — configure needs real bash for fd-3 redirects.
        bash_bin = shutil.which("bash") or "/bin/bash"

        makesys_prefix = f"MAKESYSPATH={msp} " if msp else ""

        # 1) configure — BSD configure script (not autotools).
        #    Runs via subprocess with clean env (NOT self.run) because Conan's
        #    self.run injects profile env that breaks bash fd-3 redirects.
        #    CC/AR/RANLIB passed as CLI args → written to Makefile.configure.
        self._run_subprocess(
            f"{bash_bin} ./configure PREFIX={prefix} CC={cc} AR={ar} RANLIB={ranlib}",
            cwd=sf,
            env=self._clean_env_for_configure(),
        )

        # 2) bmake — build lib + cli.
        #    Uses self.run(env="conanbuild") so bmake (tool_requires) is on PATH.
        #    CC/AR/RANLIB already written to Makefile.configure by step 1.
        self.run(
            f"{bmake} {makesys_prefix}liblowdown.a -j1",
            env="conanbuild",
            cwd=sf,
        )
        if self.options.shared:
            self.run(
                f"{bmake} {makesys_prefix}liblowdown.so -j1",
                env="conanbuild",
                cwd=sf,
            )
        if self.options.with_cli:
            self.run(
                f"{bmake} {makesys_prefix}lowdown lowdown.pc -j1",
                env="conanbuild",
                cwd=sf,
            )
            # lowdown-diff: upstream uses 'ln -f lowdown lowdown-diff' (hard link).
            # Overlay/CI filesystems reject hard links — copy instead.
            lowdown_bin = os.path.join(sf, "lowdown")
            lowdown_diff = os.path.join(sf, "lowdown-diff")
            if os.path.exists(lowdown_bin):
                shutil.copy2(lowdown_bin, lowdown_diff)

        # Copy lowdown.h from src/ to source root so package() can find it.
        # (Upstream Makefile has a 'lowdown.h' target that does this, but it's
        # not a dependency of liblowdown.a, so we copy manually.)
        hdr_src = os.path.join(sf, "src", "lowdown.h")
        hdr_dst = os.path.join(sf, "lowdown.h")
        if os.path.exists(hdr_src) and not os.path.exists(hdr_dst):
            shutil.copy2(hdr_src, hdr_dst)

        # 3) regress — upstream test suite (executed in build() per CI L2 step).
        #    Runs lowdown over regress/ inputs and diffs against expected output
        #    for 7 output formats.  Builds nothing; safe inside build().
        self.run(
            f"{bmake} {makesys_prefix}regress",
            env="conanbuild",
            cwd=sf,
        )

    def package(self):
        # Header
        copy(
            self,
            "lowdown.h",
            self.source_folder,
            os.path.join(self.package_folder, "include"),
        )
        # Static lib
        copy(
            self,
            "liblowdown.a",
            self.source_folder,
            os.path.join(self.package_folder, "lib"),
        )
        # Shared lib (if built)
        if self.options.shared:
            for pat in ("liblowdown.so*", "liblowdown.so"):
                copy(
                    self,
                    pat,
                    self.source_folder,
                    os.path.join(self.package_folder, "lib"),
                )
        # CLI binaries (lowdown + lowdown-diff) when with_cli
        if self.options.with_cli:
            for binname in ("lowdown", "lowdown-diff"):
                src = os.path.join(self.source_folder, binname)
                if os.path.exists(src):
                    copy(
                        self,
                        binname,
                        self.source_folder,
                        os.path.join(self.package_folder, "bin"),
                    )
        # pkg-config
        copy(
            self,
            "lowdown.pc",
            self.source_folder,
            os.path.join(self.package_folder, "lib", "pkgconfig"),
        )

    def package_info(self):
        # Library component
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_target_name", "lowdown::lowdown")
        self.cpp_info.set_property("pkg_config_name", "lowdown")
        self.cpp_info.libs = ["lowdown"]

        # CLI component (type=tool) — registered as a separate component
        # so consumers can depend on it explicitly; also collected by commands.json.
        if self.options.with_cli:
            self.cpp_info.components["lowdown_cli"].set_property(
                "cmake_target_name", "lowdown::lowdown_cli"
            )
            self.cpp_info.components["lowdown_cli"].bindirs = ["bin"]
