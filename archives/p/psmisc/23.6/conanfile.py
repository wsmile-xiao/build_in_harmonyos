#!/usr/bin/env python3
"""Conan recipe — psmisc 23.6 (command-line utilities).

psmisc provides process-management tools: pstree, killall, fuser,
peekfd, prtstat, pslog.  The source from GitLab tag archives does NOT
include a pre-generated configure script, and the OHOS CI environment
lacks automake.  This recipe builds the six binaries directly with
the compiler, bypassing the autotools bootstrap.  A pre-generated
config.h is included as a patch so the source compiles without
running configure.
"""

import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.env import Environment


class PsmiscConan(ConanFile):
    name = "psmisc"
    version = "23.6"
    description = "Process management utilities (pstree, killall, fuser, etc.)"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/psmisc/psmisc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"psmisc supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("ncurses/6.6")

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "src"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        src = Path(self.source_folder)
        os.umask(0o022)

        env = self._build_environment()
        with env.vars(self).apply():
            self._generate_signames_h(src)

            ncurses = Path(self.dependencies["ncurses"].package_folder)
            ncurses_lib = ncurses / "lib"
            ncurses_inc = ncurses / "include"

            cc = self._get_compiler()
            cflags = self._get_cflags()
            ldflags = self._get_ldflags()

            # (source_files, extra_compile_flags, extra_link_flags)
            binaries = {
                "killall": (["src/killall.c", "src/signals.c"], [], []),
                "fuser":   (["src/fuser.c", "src/signals.c", "src/statx.c"], [], []),
                "pstree":  (["src/pstree.c"], [], [f"-lncursesw", f"-L{ncurses_lib}"]),
                "pslog":   (["src/pslog.c"], [], []),
                "prtstat": (["src/prtstat.c"], [], []),
                "peekfd":  (["src/peekfd.c"], ["-DARM64"], []),
            }

            for name, (sources, extra_cflags, extra_ldflags) in binaries.items():
                objs = []
                for src_file in sources:
                    obj = str(src / (Path(src_file).stem + ".o"))
                    cmd = " ".join([
                        cc, *cflags, *extra_cflags,
                        f"-I{src}", f"-I{ncurses_inc}",
                        "-DHAVE_CONFIG_H", "-include", "config.h",
                        "-c", str(src / src_file),
                        "-o", obj,
                    ])
                    self.run(cmd)
                    objs.append(obj)

                bin_path = str(src / name)
                link_cmd = " ".join([
                    cc, *ldflags, *extra_ldflags,
                    *objs,
                    "-o", bin_path,
                ])
                self.run(link_cmd)
                self.output.info(f"Built {name}")

    def package(self):
        src = Path(self.source_folder)
        bindir = Path(self.package_folder) / "bin"
        bindir.mkdir(parents=True, exist_ok=True)

        for name in ("killall", "fuser", "pstree", "pslog", "prtstat", "peekfd"):
            binary = src / name
            if binary.is_file():
                shutil.copy2(binary, bindir / name)
                (bindir / name).chmod(0o755)

        pstree_x11 = bindir / "pstree.x11"
        if not pstree_x11.exists() and (bindir / "pstree").exists():
            try:
                pstree_x11.symlink_to("pstree")
            except OSError:
                shutil.copy2(bindir / "pstree", pstree_x11)

        man_src = src / "doc"
        mandir = Path(self.package_folder) / "share" / "man" / "man1"
        mandir.mkdir(parents=True, exist_ok=True)
        for manpage in ("killall.1", "pslog.1", "prtstat.1",
                        "pstree.1", "peekfd.1", "fuser.1"):
            man_file = man_src / manpage
            if man_file.is_file():
                shutil.copy2(man_file, mandir / manpage)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []

    def _get_compiler(self):
        """Get C compiler from conan conf (R33: no shell env vars)."""
        conf = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(conf, dict) and "c" in conf:
            return conf["c"]
        return "clang"

    def _get_cflags(self):
        flags = ["-Wall", "-fPIC", "-O2"]
        if self.settings.build_type == "Release":
            flags.extend(["-g", "-fstack-protector-strong",
                          "-Wformat", "-Werror=format-security"])
        return flags

    def _get_ldflags(self):
        return ["-Wl,-z,relro"]

    def _get_bash(self):
        """Get bash path — OHOS uses HNP bash, Linux uses system bash."""
        if self.settings.os == "OHOS":
            return "/data/service/hnp/bin/bash"
        return shutil.which("bash") or "/bin/bash"

    def _ohos_path(self):
        """Get PATH for OHOS builds — uses HNP and local bin."""
        return (
            "/data/service/hnp/bin:"
            "/storage/Users/currentUser/usr/local/bin:"
            f"{os.environ.get('PATH', '')}"
        )

    def _build_environment(self):
        env = Environment()
        if self.settings.os == "OHOS":
            env.define("CONFIG_SHELL", self._get_bash())
            env.define("SHELL", self._get_bash())
            env.define("TMPDIR", os.environ.get("TMPDIR",
                         "/storage/Users/currentUser/tmp"))
            env.define("PATH", self._ohos_path())
        return env

    def _generate_signames_h(self, src):
        """Generate src/signames.h from src/signames.c using CPP."""
        signames_c = src / "src" / "signames.c"
        signames_h = src / "src" / "signames.h"
        if signames_h.exists():
            return

        cc = self._get_compiler()
        cmd = (
            f"{cc} -E -dM {signames_c} | "
            "tr -s '\\t ' ' ' | sort -n -k 3 | sed "
            "'s:#define SIG\\([A-Z][A-Z]*[0-9]*\\) \\([0-9][0-9]*\\).*$"
            ":{ \\2,\"\\1\" },:p;d' | "
            "grep -v '[0-9][0-9][0-9]'"
        )
        bash_path = self._get_bash()
        run_env = {**os.environ}
        if self.settings.os == "OHOS":
            run_env["PATH"] = self._ohos_path()
        result = subprocess.run(
            [bash_path, "-c", cmd],
            capture_output=True, text=True,
            env=run_env
        )
        if result.returncode != 0:
            raise RuntimeError(f"signames.h generation failed: {result.stderr}")
        signames_h.write_text(result.stdout)
        self.output.info("Generated signames.h")
