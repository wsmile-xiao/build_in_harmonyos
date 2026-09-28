#!/usr/bin/env python3
"""Conan recipe — nedit 5.8 (Nirvana Editor)

NEdit is a Motif/LessTif text editor for the X Window System. Upstream ships
two executables — ``nedit`` (the GUI editor) and ``nc`` (the X client used to
talk to a running server) — plus a hand-written, non-autotools build system.

Build system (makefiles + raw Makefiles, no configure):

  * ``Makefile`` at the top level is only a *dispatcher*.  Its ``.DEFAULT``
    rule symlinks ``makefiles/Makefile.<platform>`` into ``util/``, ``Xlt/``,
    ``Microline/XmL/`` and ``source/``, then runs four sub-makes and finally
    **executes the freshly linked binary** (``@source/nedit -V``).
  * Each of the four sub-directories carries ``Makefile.common`` (platform
    independent object list + the ``.c.o`` rule) plus ``Makefile.dependencies``.

The recipe therefore drives the four sub-makes directly, which keeps the
per-directory layout identical to upstream while dropping the trailing
``source/nedit -V`` — see notes.md for why that trailing exec must not run
during ``conan create``.

OHOS adaptation points
----------------------
1. ``USE_DIRENT`` is mandatory here. Without it ``util/printUtils.c`` includes
   ``<sys/dir.h>``, which musl (and therefore OHOS) does not ship. Debian's
   ``debian/rules`` can drop the define because glibc still carries
   ``<sys/dir.h>`` as a compatibility shim — copying a distribution's CFLAGS
   verbatim onto musl does not work.
2. ``source/parse.c`` is normally produced by bison/yacc. Upstream documents
   the fallback (``cp parse_noyacc.c parse.c``); the recipe performs that copy
   up front so the build never depends on a yacc being installed.
3. No patches. ``nedit -V`` and ``nc -V`` are handled *before* ``XtOpenDisplay``
   on both binaries, so the smoke test runs headless — see test_package/.
4. The two executables are signed with ``binary-sign-tool`` like every other
   OHOS application package; an unsigned ELF cannot be executed from the Conan
   package cache on device.
5. Man pages come from ``doc/*.pod`` via ``pod2man``, which is a Perl script
   rather than a compiled tool. That step is best-effort: it is skipped when
   the worker has no pod2man, exactly as upstream skips it in its own default
   build.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout

# (sub-directory, make target) — mirrors the four sub-makes of the top Makefile.
_SUBDIRS = (
    ("util", "libNUtil.a"),
    ("Xlt", "libXlt.a"),
    ("Microline/XmL", "libXmL.a"),
    ("source", "nedit nc"),
)


def _unique(items):
    """Order-preserving de-duplication (link order of -l flags matters)."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


class NeditConan(ConanFile):
    name = "nedit"
    version = "5.8"
    description = ("NEdit - a Motif-based multi-purpose text editor for the "
                   "X Window System (GUI editor plus the nc X client)")
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/nedit/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # motif/2.3.8 already requires libx11/libxt/libxext/libsm/libice with
        # transitive_headers/transitive_libs, so the whole X11 stack reaches the
        # consumer. Everything nedit links against lives behind this one edge.
        self.requires("motif/2.3.8", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    # ------------------------------------------------------------------
    # Toolchain / dependency plumbing
    # ------------------------------------------------------------------

    def _compiler(self):
        # R33: take the compiler from Conan conf, never from a bare ${CC}.
        execs = self.conf.get("tools.build:compiler_executables",
                              default={}, check_type=dict)
        return execs.get("c") or "clang"

    def _archiver(self):
        """llvm-ar sitting next to the configured clang (upstream uses `ar`)."""
        cc = os.path.realpath(self._compiler())
        candidate = os.path.join(os.path.dirname(cc), "llvm-ar")
        if os.path.isfile(candidate):
            return candidate
        return shutil.which("llvm-ar") or "ar"

    def _sdk_llvm_libdir(self):
        """LLVM lib dir of the compiler toolchain (holds the SDK's libxml2.so.16).

        The OHOS clang driver spawns ``lld`` for linking, and lld's RUNPATH
        (``$ORIGIN/../lib``) points into the SDK llvm/lib. An ambient
        LD_LIBRARY_PATH (e.g. a leftover ``~/usr/local/lib`` on a CI worker) can
        shadow that directory with an incompatible libxml2.so.16 and make lld
        die with "Error loading shared library libxml2.so.16 ... symbol not
        found". Prepending the SDK llvm/lib makes the correct one win.
        """
        cc = os.path.realpath(self._compiler())
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(cc)), "lib")
        return llvm_lib if os.path.isdir(llvm_lib) else ""

    def _dependency_flags(self):
        """Collect -I / -L / -l inputs from the whole host dependency graph."""
        includedirs, libdirs, libs = [], [], []
        for dep in self.dependencies.host.values():
            info = dep.cpp_info.aggregated_components()
            includedirs.extend(info.includedirs)
            libdirs.extend(info.libdirs)
            libs.extend(info.libs)
        return _unique(includedirs), _unique(libdirs), _unique(libs)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder
        tc = GnuToolchain(self)

        incdirs, libdirs, libs = self._dependency_flags()

        # tc.cflags already carries the build type's optimisation (-O3 for
        # Release, -g for Debug) plus -DNDEBUG from tc.defines, so upstream's
        # own `-O` in Makefile.linux is left overridden rather than repeated.
        cflags = list(tc.cflags)
        cflags += [f"-D{d}" for d in tc.defines]
        cflags += [f"-I{d}" for d in incdirs]
        # Upstream makefiles/Makefile.linux carries both defines. USE_DIRENT is
        # the one that is genuinely required on OHOS (musl has no <sys/dir.h>);
        # USE_LPR_PRINT_CMD keeps upstream's Linux default print command.
        cflags += ["-DUSE_DIRENT", "-DUSE_LPR_PRINT_CMD"]

        ldflags = list(tc.ldflags)
        ldflags += [f"-L{d}" for d in libdirs]
        ldflags += [f"-l{lib}" for lib in libs]
        ldflags += ["-lm"]

        # source/parse.c is generated from parse.y by bison/yacc, with an
        # official fallback to the checked-in parse_noyacc.c. Do the fallback up
        # front: deterministic, and no yacc needed on the worker.
        shutil.copyfile(os.path.join(src, "source", "parse_noyacc.c"),
                        os.path.join(src, "source", "parse.c"))

        # Upstream's top Makefile symlinks the platform makefile into each
        # sub-directory; do the same (a copy, so no symlink permissions are
        # needed) and then run the four sub-makes directly.
        platform_makefile = os.path.join(src, "makefiles", "Makefile.linux")
        for sub, _ in _SUBDIRS:
            shutil.copyfile(platform_makefile,
                            os.path.join(src, sub, "Makefile.linux"))

        mk = ("make -f Makefile.linux "
              f"CC='{self._compiler()}' AR='{self._archiver()}' "
              f"ARFLAGS='-urs' CFLAGS='{str.join(' ', cflags)}' "
              f"LIBS='{str.join(' ', ldflags)}' -j1")

        sdk_ld = self._sdk_llvm_libdir()
        ld_env = f'LD_LIBRARY_PATH="{sdk_ld}:$LD_LIBRARY_PATH" ' if sdk_ld else ""

        for sub, target in _SUBDIRS:
            self.run(f'cd "{os.path.join(src, sub)}" && {ld_env}{mk} {target}')

        # Manual pages: doc/Makefile turns doc/*.pod into nedit.man / nc.man
        # with pod2man, a Perl script that clean OHOS images do not carry.
        # Upstream's own top-level Makefile keeps `docs` out of the default
        # build for the very same reason ("users may not have Perl
        # installed").  The editors are the deliverable, so a missing pod2man
        # must not fail the build; package() ships the pages only when this
        # produced them.
        self.run(f'cd "{src}" && make -C doc man VERSION="NEdit 5.8"',
                 ignore_errors=True)

    # ------------------------------------------------------------------
    # Package
    # ------------------------------------------------------------------

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        copy(self, "nedit", src=os.path.join(src, "source"),
             dst=os.path.join(pkg, "bin"), keep_path=False)
        # Upstream builds `nc`; Debian installs it under a less collision-prone
        # name so it cannot be confused with netcat. Keep that rename.
        copy(self, "nc", src=os.path.join(src, "source"),
             dst=os.path.join(pkg, "bin"), keep_path=False)
        os.replace(os.path.join(pkg, "bin", "nc"),
                   os.path.join(pkg, "bin", "nedit-nc"))

        # X resource defaults (application class NEdit).
        copy(self, "NEdit.ad", src=os.path.join(src, "doc"),
             dst=os.path.join(pkg, "share", "X11", "app-defaults"),
             keep_path=False)
        os.replace(os.path.join(pkg, "share", "X11", "app-defaults", "NEdit.ad"),
                   os.path.join(pkg, "share", "X11", "app-defaults", "NEdit"))

        # Manual pages, when the best-effort pod2man step in build() produced
        # them. `nc` is renamed to nedit-nc here for the same reason as bin/.
        for pod, man in (("nedit.man", "nedit.1"), ("nc.man", "nedit-nc.1")):
            if not os.path.isfile(os.path.join(src, "doc", pod)):
                continue
            copy(self, pod, src=os.path.join(src, "doc"),
                 dst=os.path.join(pkg, "share", "man", "man1"), keep_path=False)
            os.replace(os.path.join(pkg, "share", "man", "man1", pod),
                       os.path.join(pkg, "share", "man", "man1", man))

        for doc in ("README", "ReleaseNotes", "faq.txt"):
            copy(self, doc, src=os.path.join(src, "doc") if doc == "faq.txt" else src,
                 dst=os.path.join(pkg, "share", "doc", "nedit"), keep_path=False)

        copy(self, "COPYRIGHT", src=src,
             dst=os.path.join(pkg, "licenses"), keep_path=False)

        for name in ("nedit", "nedit-nc"):
            path = os.path.join(pkg, "bin", name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
                self._sign_ohos_binary(path)

    def _sign_ohos_binary(self, path):
        if str(self.settings.os) != "OHOS":
            return

        signer = self.conf.get("user.ohos:sign_tool", default="", check_type=str)
        signer = (
            signer
            or os.environ.get("OHOS_SIGN_TOOL", "")
            or shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool is unavailable; skipping OHOS ELF signing"
            )
            return

        objcopy = self.conf.get("user.ohos:objcopy", default="", check_type=str)
        objcopy = (
            objcopy
            or os.environ.get("OHOS_OBJCOPY", "")
            or shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        if os.path.isfile(objcopy):
            self.run(f'"{objcopy}" --remove-section .codesign "{path}"',
                     ignore_errors=True)

        signed = f"{path}.signed"
        self.run(f'"{signer}" sign -inFile "{path}" '
                 f'-outFile "{signed}" -selfSign 1')
        if not os.path.isfile(signed):
            raise ConanException(f"binary-sign-tool produced no output for {path}")
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        # X applications look their resource defaults up through XAPPLRESDIR.
        self.runenv_info.prepend_path(
            "XAPPLRESDIR",
            os.path.join(self.package_folder, "share", "X11", "app-defaults"))
