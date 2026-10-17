#!/usr/bin/env python3
"""Conan recipe for tabbed 0.9 - suckless tabbed container.

`tabbed` is a minimal X11 window manager helper: it decorates *any* program with
its own tab bar by becoming the container window and re-parenting each top-level
window the spawned client maps.  One build produces two programs:

  * ``tabbed``  - the container itself (Xlib + Xft + fontconfig).
  * ``xembed``  - an XEmbed wrapper that is exec'd by tabbed.  Upstream's
                  single ``.o`` rule links the same ``-lX11 -lfontconfig
                  -lXft`` closure into it, so it is *not* dependency-free
                  (proven by the link line in ``reports`` notes and by the
                  fact that running it needs the same runtime closure).

OHOS notes
----------
* Upstream is a bare POSIX makefile: no configure, no CMake, and (unlike
  dmenu/st/slock) no ``config.mk`` either -- every setting is inlined in
  ``Makefile``.
* The first line is ``.POSIX:``, which makes GNU make fall back to ``CC=c99``.
  ``c99`` does not exist on this platform, so the cross clang must be passed on
  the make command line (R33: taken from the Conan profile, never from a bare
  shell ``${CC}``), and its usability is proven by running ``--version``.
* ``TABBED_CFLAGS`` / ``TABBED_LDFLAGS`` end with ``${CFLAGS}`` / ``${LDFLAGS}``
  but ``TABBED_CPPFLAGS`` never references ``${CPPFLAGS}``: a ``-I`` delivered
  through CPPFLAGS is dropped silently, so all dependency search paths go
  through CFLAGS/LDFLAGS.
* ``PREFIX`` is a plain ``=`` assignment and the install rule expects a host
  ``install``/``chmod``/``sed`` tool chain that HMDFS does not fully provide,
  so packaging stages the files itself (farbfeld/4.0 shape) instead of running
  ``make install``.
* Both ELFs are signed for OHOS: first the freshly linked copies in ``build()``
  (so an exploratory run works) and again the packaged copies in ``package()``,
  which is the artifact consumers actually get.  On OHOS a missing
  ``binary-sign-tool`` is a hard error, not a warning: an unsigned ELF is
  unloadable on this platform (this recipe's own rc=127 investigation proved
  that a rejected ``.codesign`` yields exit 127), so warning and continuing
  would publish an artifact that is dead on arrival.
* Upstream ships no tests at all; see ``test_package/`` for the consumer test.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class TabbedConan(ConanFile):
    name = "tabbed"
    version = "0.9"
    description = ("X11 tab container: gives any application its own tab bar "
                   "by re-parenting the client windows (suckless)")
    license = "MIT"
    homepage = "https://tools.suckless.org/tabbed/"
    url = ""

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tabbed is adapted for Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        # Upstream links -lX11 -lfontconfig -lXft and tabbed.c includes
        # X11/Xft/Xft.h, so Xft + fontconfig are mandatory, not optional.
        # libxft/2.3.9 pins libx11/1.8.13; the alternative libx11/6.4.0 recipe
        # is a SONAME-style alias that would fork the graph, so it is not used.
        self.requires("libxft/2.3.9", transitive_headers=True,
                      transitive_libs=True)
        self.requires("libx11/1.8.13", transitive_headers=True,
                      transitive_libs=True)
        self.requires("fontconfig/2.18.3", transitive_headers=True,
                      transitive_libs=True)
        # X11/Xatom.h & friends come from xorgproto; libx11 does not re-export
        # them, so it is declared (same treatment as the published aliki).
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def export_sources(self):
        # patches: [] today; kept so a future upstream fix ships as a real
        # patch instead of an in-recipe string replace (G1/W2 shape).
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate(scope="build")

    def build(self):
        apply_conandata_patches(self)
        cc = self._resolve_compiler()
        cflags, ldflags = self._dependency_flags()
        # A make-command-line assignment beats the Makefile's plain "=", and
        # ${CFLAGS}/${LDFLAGS} are referenced by TABBED_CFLAGS/TABBED_LDFLAGS.
        # CPPFLAGS is deliberately not passed: upstream never forwards it.
        # LD_LIBRARY_PATH must not reach the *toolchain*: lld is a host binary with
        # NEEDED libxml2.so.16 and RUNPATH $ORIGIN/../lib, and the conanbuild env
        # generated by VirtualRunEnv(scope="build") puts the *target* libxml2 (a
        # transitive dependency of fontconfig) on LD_LIBRARY_PATH first.  The loader
        # then hands lld a library that does not export the symbols it was linked
        # against, and the link dies (CI build #60222 on worker CI-005:
        # "Error loading shared library libxml2.so.16: (needed by .../llvm/bin/lld)"
        # + "Error relocating .../lld: xmlFreeDoc: symbol not found" x17 ->
        # "clang-15: error: unable to execute command" -> "Makefile:37: tabbed] Error 1").
        # Dependency discovery at link time is already explicit through -L/-l in
        # LDFLAGS, so unsetting it costs nothing.  Same hazard this recipe already
        # guards for the signing tools below; merged precedent: archives/b/burp2/2.1.0
        # unsets LD_LIBRARY_PATH around its make step.
        self.run("unset LD_LIBRARY_PATH && make -j1 CC={} CFLAGS={} LDFLAGS={}".format(
            shlex.quote(cc), shlex.quote(cflags), shlex.quote(ldflags)),
            cwd=self.source_folder)

        for binary in ("tabbed", "xembed"):
            path = os.path.join(self.source_folder, binary)
            if os.path.isfile(path):
                self._sign_ohos_binary(path)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        for binary in ("tabbed", "xembed"):
            src = os.path.join(self.source_folder, binary)
            if not os.path.isfile(src):
                raise ConanInvalidConfiguration(
                    "expected program is missing after build: " + binary)
            copy(self, binary, src=self.source_folder, dst=bin_dir,
                 keep_path=False)
            installed = os.path.join(bin_dir, binary)
            os.chmod(installed, 0o755)
            self._sign_ohos_binary(installed)

        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        for page in ("tabbed.1", "xembed.1"):
            copy(self, page, src=self.source_folder, dst=man_dir,
                 keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "tabbed"),
             keep_path=False)

    def package_info(self):
        # tabbed is a standalone tool; it exports no library for consumers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

    # ── helpers ──────────────────────────────────────────────────────────

    def _dependency_flags(self):
        """Collect -I / -L of the whole dependency closure.

        Everything goes into CFLAGS/LDFLAGS because the upstream Makefile drops
        CPPFLAGS.  The hard-coded host paths stay in TABBED_CFLAGS unused.
        """
        cflags = ["-O2", "-Wall"]
        ldflags = []
        for _, dep in self.dependencies.items():
            if not dep.package_folder:
                continue
            for inc in dep.cpp_info.includedirs:
                path = inc if os.path.isabs(inc) else os.path.join(
                    dep.package_folder, inc)
                if os.path.isdir(path):
                    cflags.append("-I" + path)
            for lib in dep.cpp_info.libdirs:
                path = lib if os.path.isabs(lib) else os.path.join(
                    dep.package_folder, lib)
                if os.path.isdir(path):
                    ldflags.append("-L" + path)
        return " ".join(cflags), " ".join(ldflags)

    def _resolve_compiler(self):
        """R33: the compiler comes from the Conan profile, never from ${CC}.

        Usability is proven by executing ``--version``: on HMDFS a path can look
        fine to ``os.path.isfile`` and still be unusable (libdogleg/0.18 note,
        xmlsec/1.3.12 precedent).
        """
        executables = self.conf.get(
            "tools.build:compiler_executables", default={},
            check_type=dict) or {}
        cc = executables.get("c") or shutil.which("clang")
        if not cc:
            raise ConanInvalidConfiguration(
                "tabbed needs an explicit C compiler: set "
                "tools.build:compiler_executables in the profile")
        try:
            self.run(shlex.quote(cc) + " --version", quiet=True,
                     env="conanbuild")
        except Exception as error:  # noqa: BLE001 - re-raised with context
            raise ConanInvalidConfiguration(
                "configured C compiler is not usable: " + str(cc)
                + " (" + str(error) + ")")
        return cc

    def _find_tool(self, name):
        configured = os.environ.get("OHOS_" + name.upper().replace("-", "_"))
        for candidate in (configured,
                          shutil.which(name),
                          os.path.join("/data/service/hnp/bin", name),
                          os.path.join(os.path.expanduser("~"),
                                       "usr", "local", "bin", name)):
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _sign_ohos_binary(self, path):
        """Self-sign an OHOS ELF; a stale .codesign section is stripped first
        so re-signing stays idempotent.

        Missing signer is a hard failure on OHOS, not a warning: an unsigned
        (or badly signed) ELF cannot be loaded by this platform's loader at
        all -- this recipe's own root-cause work on fontconfig/2.18.3 ended
        with rc=127 for exactly that condition, so shipping it silently would
        hand out an artifact that is dead on arrival.  334 archived recipes
        already fail loudly vs 271 that only warn.
        """
        if str(self.settings.os) != "OHOS" or not os.path.isfile(path):
            return
        signer = self._find_tool("binary-sign-tool")
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found: OHOS ELFs must be signed, "
                "refusing to package an unloadable binary")
        objcopy = self._find_tool("llvm-objcopy")
        if objcopy:
            self.run("env -u LD_LIBRARY_PATH {} --remove-section .codesign {} "
                     "2>/dev/null || true".format(shlex.quote(objcopy),
                                                  shlex.quote(path)),
                     quiet=True, env=None)
        signed = path + ".signed"
        # LD_LIBRARY_PATH must not leak into the signing tools, otherwise the
        # packaged dependency libraries shadow the SDK's own ones.
        self.run("env -u LD_LIBRARY_PATH {} sign -inFile {} -outFile {} "
                 "-selfSign 1".format(shlex.quote(signer), shlex.quote(path),
                                      shlex.quote(signed)),
                 quiet=True, env=None)
        if os.path.isfile(signed):
            os.replace(signed, path)
            os.chmod(path, 0o755)
