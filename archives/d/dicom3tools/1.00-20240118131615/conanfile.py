#!/usr/bin/env python3
"""Conan recipe for dicom3tools 1.00-20240118131615 -- DICOM file toolkit (imake).

dicom3tools is David A. Clunie's command line toolkit for creating, modifying,
dumping and validating DICOM files.  It ships ~115 programs built from six
internal static libraries, plus an X11 image display program (dcdisp).

Build system: this snapshot is built with imake, the X11 makefile generator,
in three steps -- ./Configure writes config/generic.cf, imake turns every
Imakefile into a Makefile, and make builds the libraries and programs.  imake,
makedepend and mkdirhier are not part of dicom3tools and are not published for
OHOS, so the two small X11R5 tools from the official archive named in INSTALL
are compiled from source here and used as build tools only; nothing from them
is packaged.

OHOS notes (see notes.md and the patches for the evidence):
  * the hnp clang emits a signed (.codesign) binary and stripping it makes the
    result non-executable (exit code 126), so StripCmd is set to true and the
    install step does not strip;
  * /tmp is a read-only mount and /dev/tty cannot be opened without a
    controlling terminal, so both the Configure temporary root and the awk
    diagnostics had to be redirected;
  * musl has no sys_errlist, no gethostid and no infinity()/quiet_nan().
"""

import os
import shutil
import stat
import textwrap

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

required_conan_version = ">=2.0"


def _quote_defines(defines):
    """Quote the imake defines for use inside IMAKE_DEFINES.

    imake expands IMAKE_DEFINES unquoted in the sub-directory rules, so a define
    whose value contains spaces (-DX11IncludePath=...) has to arrive as one
    shell word; without the quotes only the first path survives.
    """
    return " ".join("'%s'" % d.replace("'", "'\\''") for d in defines)


class Dicom3ToolsConan(ConanFile):
    name = "dicom3tools"
    version = "1.00-20240118131615"
    description = (
        "Command line tools for creating, modifying, dumping and validating "
        "DICOM medical image files"
    )
    license = "BSD-3-Clause"
    homepage = "https://www.dclunie.com/dicom3tools.html"
    url = "https://www.dclunie.com/dicom3tools.html"
    topics = ("dicom", "medical", "imaging", "validation")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    # ----------------------------------------------------------------- export
    def export_sources(self):
        export_conandata_patches(self)

    # ------------------------------------------------------------ requirements
    def requirements(self):
        # dcdisp (the X11 image display program) and the two display libraries it
        # is linked with need X11; both packages are published for OHOS.
        self.requires("libx11/6.4.0")
        self.requires("libxext/6.4.0")

    # ------------------------------------------------------------------ source
    def source(self):
        # Both trees are unpacked into the source folder: dicom3tools/ and imake/.
        get(
            self,
            **self.conan_data["sources"]["dicom3tools"],
            strip_root=True,
            destination="dicom3tools",
        )
        get(
            self,
            **self.conan_data["sources"]["imake"],
            strip_root=True,
            destination="imake",
        )
        # imake.tar.gz ships stale *.orig copies of two Imakefiles.  They are
        # unused, and patch_ng refuses to patch a file when the name it wants
        # for its own backup already exists.
        self._remove_upstream_backups()

    def _remove_upstream_backups(self):
        for root, _dirs, files in os.walk(os.path.join(self.source_folder, "imake")):
            for name in files:
                if name.endswith((".orig", ".bak")):
                    os.remove(os.path.join(root, name))

    # ------------------------------------------------------------------- build
    # layout() and generate() are deliberately not overridden: the build is
    # driven by hand (Configure + imake + make) and needs no toolchain file, so
    # Conan's default build folder and the plain VirtualBuildEnv generator are
    # enough.
    def build(self):
        apply_conandata_patches(self)

        src = os.path.join(self.source_folder, "dicom3tools")
        imake_src = os.path.join(self.source_folder, "imake")
        tools = os.path.join(self.build_folder, "hosttools")
        work = os.path.join(self.build_folder, "work")
        os.makedirs(tools, exist_ok=True)

        self._build_imake_tools(imake_src, tools)

        # Configure and make run in a copy of the source tree so that the
        # unpacked sources in the cache stay pristine.
        if os.path.exists(work):
            shutil.rmtree(work)
        shutil.copytree(src, work, symlinks=True)

        env = self._tool_env(tools)
        defines = self._imake_defines()

        self.output.info("Configure: writing config/generic.cf")
        self.run("./Configure", cwd=work, env=env)

        imake = os.path.join(tools, "imake")
        define_args = " ".join("'%s'" % d for d in defines)
        self.run(f'{imake} -I./config {define_args}', cwd=work, env=env)

        # The sub-directory Makefiles take their imake flags from IMAKE_DEFINES,
        # and the build tools are named by absolute path because make starts a
        # fresh shell for every recipe.
        make_defs = " ".join(
            [
                'IMAKE_DEFINES="%s"' % _quote_defines(defines),
                'IMAKE="%s"' % os.path.join(tools, "imake"),
                'DEPEND="%s"' % os.path.join(tools, "makedepend"),
                'MKDIRHIER="%s"' % os.path.join(tools, "mkdirhier"),
            ]
        )
        self.run(f"make {make_defs} Makefiles", cwd=work, env=env)
        self.run(f"make {make_defs} depend", cwd=work, env=env)

        jobs = str(max(1, self._cpu_count()))
        self.run(
            f"make -j{jobs} {make_defs} {self._install_command_env()}",
            cwd=work,
            env=env,
        )

        # imake's sub-directory rules discard the exit status of every sub-make
        # except the last one, so the return code alone does not prove that all
        # 67 sub-directories built.  Check the log the same way a reader would.
        self._check_build_completed(work)
        self._work_dir = work

    # ----------------------------------------------------------------- helpers
    def _cpu_count(self):
        try:
            return len(os.sched_getaffinity(0))
        except (AttributeError, OSError):
            return os.cpu_count() or 1

    def _compiler(self, key, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = executables.get(key)
        if configured:
            return configured
        return shutil.which(fallback) or fallback

    def _build_imake_tools(self, imake_src, tools):
        """Compile imake, makedepend and mkdirhier from the X11R5 archive.

        These are host build tools: they run while the package is built and are
        never packaged.
        """
        cc = self._compiler("c", "clang")

        # imake feeds its Imakefile to the preprocessor on stdin, which is how
        # the historic /lib/cpp behaved.  clang-cpp does the same; -P suppresses
        # the line markers and the blank filler lines clang emits to preserve
        # source line numbers, which imake would otherwise mistake for makefile
        # content.
        cpp = shutil.which("clang-cpp") or shutil.which("cpp")
        if not cpp:
            raise ConanException(
                "dicom3tools needs a preprocessor that reads stdin (clang-cpp or cpp)"
            )
        cpp_wrapper = os.path.join(tools, "cpp")
        self._write_script(
            cpp_wrapper,
            f'#! /bin/sh\nexec "{cpp}" -P "$@"\n',
        )

        self.run(
            f'"{cc}" -std=gnu89 -w -DFIXUP_CPP_WHITESPACE -o "{os.path.join(tools, "imake")}"'
            f' -I"{os.path.join(imake_src, "config")}"'
            f' -I"{os.path.join(imake_src, "include")}"'
            f' -DCPP_PROGRAM=\'"{cpp_wrapper}"\''
            f' "{os.path.join(imake_src, "config", "imake.c")}"'
        )

        md_src = os.path.join(imake_src, "util", "makedepend")
        md_obj = os.path.join(self.build_folder, "makedepend-obj")
        os.makedirs(md_obj, exist_ok=True)
        objects = []
        for name in ("include", "main", "parse", "pr", "cppsetup"):
            obj = os.path.join(md_obj, name + ".o")
            self.run(
                f'"{cc}" -w -c -I"{md_src}"'
                f' -I"{os.path.join(imake_src, "include")}"'
                f' -I"{os.path.join(imake_src, "config")}"'
                f" -DINCLUDEDIR='\"/usr/include\"'"
                f' -o "{obj}" "{os.path.join(md_src, name + ".c")}"'
            )
            objects.append(obj)
        self.run(
            f'"{cc}" -w -o "{os.path.join(tools, "makedepend")}" '
            + " ".join(f'"{o}"' for o in objects)
        )

        mkdirhier = os.path.join(tools, "mkdirhier")
        shutil.copyfile(
            os.path.join(imake_src, "util", "scripts", "mkdirhier.sh"), mkdirhier
        )
        os.chmod(
            mkdirhier,
            os.stat(mkdirhier).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
        )

    def _write_script(self, path, content):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(
            path,
            os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
        )

    def _tool_env(self, tools):
        """Environment for the build tools, as the list ConanFile.run wants."""
        # Configure writes its probe files under TMPDIR; /tmp is a read-only
        # mount on OHOS.
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        return [
            "PATH=%s%s%s" % (tools, os.pathsep, os.environ.get("PATH", "")),
            "TMPDIR=%s" % tmp,
            "CC=%s" % self._compiler("c", "clang"),
            "CXX=%s" % self._compiler("cpp", "clang++"),
        ]

    def _dep_dirs(self, subdir):
        found = []
        for dep in self.dependencies.host.values():
            path = os.path.join(dep.package_folder, subdir)
            if os.path.isdir(path) and path not in found:
                found.append(path)
        return found

    def _imake_defines(self):
        """The imake command line for this build.

        X11INCLUDEPATH is interpolated as -I<value>, so only the second and
        later include directories carry their own -I.
        """
        include_dirs = self._dep_dirs("include")
        if not include_dirs:
            raise ConanException("libx11/xorgproto include directories not found")

        x11_include = include_dirs[0] + "".join(
            " -I" + d for d in include_dirs[1:]
        )
        x11_library = "".join("-L%s " % d for d in self._dep_dirs("lib")).strip()
        x11_library = (x11_library + " -lX11 -lXext").strip()

        return [
            # OHOS: stripping the hnp signed binary makes it non-executable.
            "-DStripCmd=true",
            "-DAnsiCCmd=%s" % self._compiler("c", "clang"),
            "-DCPlusPlusCmd=%s" % self._compiler("cpp", "clang++"),
            "-DX11IncludePath=%s" % x11_include,
            "-DDisplayLoadFlags=%s" % x11_library,
        ]

    def _install_command_env(self):
        # `install` is not part of the OHOS base system; busybox provides one.
        install = shutil.which("install")
        if not install:
            busybox = shutil.which("busybox")
            if busybox:
                install = busybox + " install"
        if not install:
            raise ConanException("no install implementation available")
        # INSTPGMFLAGS defaults to -s; never strip on OHOS.
        return "INSTALL='%s' INSTPGMFLAGS=" % install

    def _check_build_completed(self, work):
        """Fail unless every sub-directory really compiled.

        make's exit status only reflects the last sub-make because of the way
        imake writes the sub-directory rules.  Re-derive the count of programs
        that were linked instead of trusting the return code.
        """
        linked = 0
        for root, _dirs, files in os.walk(os.path.join(work, "appsrc")):
            for name in files:
                path = os.path.join(root, name)
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    with open(path, "rb") as handle:
                        if handle.read(4) == b"\x7fELF":
                            linked += 1
        if linked < 100:
            raise ConanException(
                "only %d programs were linked; the imake build did not complete"
                % linked
            )
        self.output.info("linked %d programs" % linked)

    # ----------------------------------------------------------------- package
    def package(self):
        work = getattr(self, "_work_dir", None)
        if work is None:
            # conan package may run in a fresh process for the package step
            work = os.path.join(self.build_folder, "work")

        stage = os.path.join(self.build_folder, "stage")
        if os.path.exists(stage):
            shutil.rmtree(stage)
        os.makedirs(stage)

        env = self._tool_env(os.path.join(self.build_folder, "hosttools"))
        tools = os.path.join(self.build_folder, "hosttools")
        make_defs = " ".join(
            [
                'IMAKE_DEFINES="%s"' % _quote_defines(self._imake_defines()),
                'IMAKE="%s"' % os.path.join(tools, "imake"),
                'DEPEND="%s"' % os.path.join(tools, "makedepend"),
                'MKDIRHIER="%s"' % os.path.join(tools, "mkdirhier"),
            ]
        )
        self.run(
            f'make {make_defs} {self._install_command_env()} DESTDIR="{stage}" install',
            cwd=work,
            env=env,
        )
        self.run(
            f'make {make_defs} {self._install_command_env()} DESTDIR="{stage}" install.man',
            cwd=work,
            env=env,
        )

        prefix = os.path.join(stage, "usr", "local")
        copy(
            self,
            "*",
            src=os.path.join(prefix, "bin"),
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "*",
            src=os.path.join(prefix, "man"),
            dst=os.path.join(self.package_folder, "share", "man"),
        )
        copy(
            self,
            "COPYRIGHT",
            src=os.path.join(self.source_folder, "dicom3tools"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Tool-only package: ships executables and their manual pages.  The
        # static libraries the programs are linked from are internal build
        # artefacts and are deliberately not packaged, so the default lib/ and
        # include/ search paths have to be cleared as well -- otherwise a
        # consumer would be pointed at directories that do not exist.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
