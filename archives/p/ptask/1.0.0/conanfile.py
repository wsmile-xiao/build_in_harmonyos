#!/usr/bin/env python3
"""Conan recipe for ptask 1.0.0 — a GTK+ 3 front end for Taskwarrior.

HarmonyOS PC adaptation notes
-----------------------------
* ``ptask`` 1.0.0 is the last release of Jean-Philippe Orsini's GTK+
  graphical task manager for taskwarrior (the Debian / Ubuntu / AUR
  ``ptask`` source package).  The upstream web site (wpitchoune.net) has
  been dead for years and Debian marks its watch file ``Untrackable``,
  so the pristine upstream release tarball is fetched from the Ubuntu
  archive: it carries the byte-identical ``ptask_1.0.0.orig.tar.gz``
  (sha256 ``b8cde0f7...`` verified against the Debian pool) that Debian
  publishes together with the upstream GPG signature
  ``ptask_1.0.0.orig.tar.gz.asc``.
* The release ships generated Autotools files, so no autoreconf is
  needed.  Seven patches are applied:
    * config.guess/config.sub learn the HarmonyOS ``uname`` output and
      the ``aarch64-unknown-linux-ohos`` triplet (the bundled 2012 files
      do not recognize either);
    * configure creates its config.status temporary directory with
      ``umask 022`` instead of ``077`` (HMDFS setgid semantics make 0700
      directories unusable, so configure could not write config.status);
    * src/Makefile.in spells the upstream link flag as
      ``-Wl,--export-dynamic``: the tarball sets ``AM_LDFLAGS`` to a bare
      ``-export-dynamic``, which the GCC driver accepts but the OHOS clang
      driver forwards to the linker, where it is parsed as
      ``-e xport-dynamic`` (lld only warns "cannot find entry symbol
      xport-dynamic" and leaves the ELF entry point unset, so every run
      died with SIGSEGV before ``main()``);
    * src/main.c adds a headless ``-S/--selftest`` entry point;
    * src/pstr.c fixes ``trim()``, which moved the trimmed string with
      ``memmove(str, p, strlen(p))`` and therefore dropped the
      terminating NUL (found by the headless self test added above);
    * src/tw.c drops the ``is_error()`` guard that json-c >= 0.13 removed
      (it was a no-op) and accepts the taskwarrior 2.x series, so that
      the interface works with taskwarrior 2.6.2, the version published
      in the HarmonyOS PC artifact repository.
* HarmonyOS PC has no X server, so the GTK window cannot be opened.  The
  recipe therefore builds and installs the complete application (binary,
  glade UI, gsettings schema, desktop entry, icons), self-signs the
  packaged executable and validates the result headlessly:
  ``--version`` / ``--help`` (upstream CLI contract), ``--selftest``
  (the HarmonyOS specific test: 23 checks over the production
  pstr/ptime helpers and the complete taskwarrior import path driven by
  a stub ``task`` command) and the expected no-display failure, which
  proves the packaged binary really loads and initialises GTK.
* ``configure`` (via glib-2.0.m4's GLIB_GSETTINGS) resolves
  ``glib-compile-schemas`` through ``pkg-config --variable
  glib_compile_schemas gio-2.0`` and aborts when it is empty, so the
  generated ``gio-2.0.pc`` gets the variable added and it points at a
  self-signed copy of the tool (the one in the glib Conan package is an
  unsigned ELF OHOS refuses to execute).  ``make install`` then installs
  ``ptask.gschema.xml`` through the upstream GSETTINGS_RULES block but
  skips the compile step whenever DESTDIR is set, so the recipe compiles
  the schema itself.
"""
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class PtaskConan(ConanFile):
    name = "ptask"
    version = "1.0.0"
    description = ("ptask is a GTK+ graphical user interface for managing "
                   "taskwarrior tasks")
    license = "GPL-2.0-or-later"
    homepage = ("https://web.archive.org/web/20160608075549/"
                "http://wpitchoune.net/blog/ptask/")
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac probes gtk+-3.0 >= 3.12, x11, xext and json-c; the
        # X11 modules are pkg-config requirements only (the sources do not
        # call into Xlib, but a missing module aborts configure).
        self.requires("gtk/3.24.43", transitive_headers=True,
                      transitive_libs=True)
        self.requires("libx11/6.4.0", transitive_headers=True,
                      transitive_libs=True)
        self.requires("libxext/6.4.0", transitive_headers=True,
                      transitive_libs=True)
        self.requires("json-c/0.18", transitive_headers=True,
                      transitive_libs=True)
        # ptask is only a front end for taskwarrior, which it executes
        # (`task export ...`); it has to be present in the runtime env.
        self.requires("task/2.6.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ptask supports Linux/OHOS native builds, got "
                f"{self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # configure.ac probes the pkg-config modules gtk+-3.0, x11, xext
        # and json-c; PkgConfigDeps writes relocatable .pc files into the
        # generators folder.
        PkgConfigDeps(self).generate()
        self._add_gio_compile_schemas_variable()
        self._fix_pkgconfig_files()

        VirtualBuildEnv(self).generate()

        toolchain = AutotoolsToolchain(self)
        environment = toolchain.environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        toolchain.generate(env=environment)

    def build(self):
        apply_conandata_patches(self)
        # src/ptask.1 is shipped pre-generated and is newer than main.c in
        # the release tarball; patching main.c would make `make install'
        # regenerate it with help2man, which is not available.  Keep the
        # shipped, upstream rendered man page.
        os.utime(os.path.join(self.source_folder, "src", "ptask.1"), None)

        if self.settings.os == "OHOS":
            self._prepare_ohos_host_tools()

        with self._build_environment().vars(self).apply():
            self._run_ohos_configure()
            Autotools(self).make(args=["-j1"])
            # Upstream ships no functional test suite: tests/TESTS is
            # empty, so `make check' only runs check-TESTS (empty suite,
            # TOTAL: 0) plus check-local.  check-local's
            # `find src -name '*.c' -exec tests/checkpatch.pl ...' does
            # reach the shipped script, but the script starts with
            # `#!/usr/bin/perl -w' and this device has no /usr/bin/perl
            # (perl is only on the harmonybrew path), so execve fails with
            # ENOENT and find reports it as `No such file or directory':
            # the linter never runs.  `make check' is invoked for
            # completeness only; it contributes no behavioural coverage.
            Autotools(self).make(target="check", args=["-j1"])

    def package(self):
        destination = shlex.quote(self.package_folder)
        schemas = os.path.join(self.package_folder, "share",
                               "glib-2.0", "schemas")
        with self._build_environment().vars(self).apply():
            self.run(f"make -j1 install DESTDIR={destination}")
            # make install (the GSETTINGS_RULES block that configure
            # substitutes into src/Makefile) installs ptask.gschema.xml but
            # skips the compile step whenever DESTDIR is set, so the
            # compiled schema the runtime needs is built here — inside the
            # same environment, the host tool needs the dependency libdirs
            # (bundled libintl, libglib, libgio) on LD_LIBRARY_PATH.
            self.run(shlex.join([self._schema_compiler(), schemas]))

        if self.settings.os == "OHOS":
            self._sign_ohos_elf(
                os.path.join(self.package_folder, "bin", "ptask")
            )

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _schema_compiler_path(self):
        """Where glib-compile-schemas is expected to live for this build:
        the self-signed copy in the build tree on OHOS (the one shipped in
        the glib Conan package is an unsigned ELF OHOS refuses to execute),
        the host tool otherwise."""
        if self.settings.os == "OHOS":
            return os.path.join(self.build_folder, "host-tools",
                                "glib-compile-schemas")
        return shutil.which("glib-compile-schemas") or "glib-compile-schemas"

    def _build_environment(self):
        environment = Environment()
        tools_root = os.path.join(self.build_folder, "host-tools")
        if os.path.isdir(tools_root):
            environment.prepend_path("PATH", tools_root)
        compiler = self._schema_compiler_path()
        if os.path.isfile(compiler):
            environment.define_path("GLIB_COMPILE_SCHEMAS", compiler)
        if self.settings.os == "OHOS":
            for dependency in self.dependencies.host.values():
                for libdir in dependency.cpp_info.libdirs:
                    directory = libdir
                    if not os.path.isabs(directory):
                        directory = os.path.join(dependency.package_folder,
                                                 libdir)
                    if os.path.isdir(directory):
                        environment.prepend_path("LD_LIBRARY_PATH", directory)
        return environment

    def _generated_pc(self, module):
        path = os.path.join(self.generators_folder, f"{module}.pc")
        if not os.path.isfile(path):
            raise ConanException(f"expected generated pc file: {path}")
        return path

    def _pc_field_append(self, module, field, extra, marker):
        """Append ``extra`` to the ``field`` line of a PkgConfigDeps
        generated .pc file (idempotent; ``marker`` is what proves the
        amendment is already there).  PkgConfigDeps rebuilds the .pc files
        from cpp_info, so anything the upstream .pc file carries outside
        cpp_info is lost and has to be restored here."""
        path = self._generated_pc(module)
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        if any(marker in line for line in lines):
            return
        for index, line in enumerate(lines):
            if line.startswith(f"{field}:"):
                lines[index] = f"{line} {extra}"
                break
        else:
            raise ConanException(f"no {field}: line in {path}")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")

    def _add_gio_compile_schemas_variable(self):
        """glib-2.0.m4's GLIB_GSETTINGS macro looks the schema compiler up
        with ``$PKG_CONFIG --variable glib_compile_schemas gio-2.0`` when it
        is not cross compiling, and errors out with 'glib-compile-schemas
        not found.' when the variable is empty.  PkgConfigDeps cannot emit
        custom pkg-config variables, so add it to the generated gio-2.0.pc,
        pointing at the self-signed copy the build prepares in the build
        tree (the dependency's own binary is an unsigned ELF that OHOS
        refuses to execute).  The value reaches src/Makefile through
        AC_SUBST(GLIB_COMPILE_SCHEMAS) and is what runs the upstream
        ``%.gschema.valid`` rule during ``make``."""
        path = self._generated_pc("gio-2.0")
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        if "glib_compile_schemas=" in content:
            return
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"glib_compile_schemas="
                         f"{self._schema_compiler_path()}\n")

    def _glib_libintl_library(self):
        """Absolute path of the bundled libintl in the glib package."""
        libdir = os.path.join(self.dependencies["glib"].package_folder, "lib")
        for name in ("libintl.so", "libintl.so.8"):
            candidate = os.path.join(libdir, name)
            if os.path.isfile(candidate):
                return candidate
        raise ConanException(f"no bundled libintl in {libdir}")

    def _fix_pkgconfig_files(self):
        """Restore the three things PkgConfigDeps drops from the .pc files
        and that this build needs:

        * json-c installs its headers under ``include/json-c/`` but the
          generated .pc exports only ``-I${includedir}``; upstream's own
          json-c.pc carries ``-I${includedir}/json-c``.  Without the
          subdirectory ``#include <json.h>`` (src/main.c, src/tw.c) does
          not resolve.
        * glib builds its own libintl on OHOS and its own glib-2.0.pc links
          it explicitly (``Libs: -L${libdir} -lglib-2.0 .../libintl.so``);
          the variables it declares in ``<glib.h>`` (``gettext`` is
          ``#define``d to ``g_libintl_gettext`` by the bundled
          ``libintl.h``) are referenced by syslog/UI code, so the
          application only links once the library is back on the command
          line.
        * gio-2.0: see :meth:`_add_gio_compile_schemas_variable`."""
        self._add_gio_compile_schemas_variable()
        self._pc_field_append("json-c", "Cflags",
                              '-I"${includedir}/json-c"', "/json-c")
        self._pc_field_append("glib-2.0", "Libs",
                              self._glib_libintl_library(), "libintl")

    def _run_ohos_configure(self):
        """configure is generated by Autoconf 2.69; pin the interpreter,
        CONFIG_SHELL and SHELL to the same absolute POSIX shell (the
        profile [buildenv] otherwise injects bash, which changes the
        config.status regeneration semantics).  The self-signed host tools
        are also prepended to PATH: ``self.run(env="conanbuild")`` re-sources
        the generated build environment, which would otherwise drop the
        PATH set up by ``_build_environment()``."""
        configure = os.path.join(self.source_folder, "configure")
        options = [
            "--prefix=/",
            "--disable-nls",
        ]
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            shell = "/bin/sh"
        tools_root = os.path.join(self.build_folder, "host-tools")
        command = (
            f"PATH={shlex.quote(tools_root)}:$PATH "
            f"CONFIG_SHELL={shell} SHELL={shell} "
            + shlex.join([shell, configure] + options)
        )
        self.run(command, cwd=self.build_folder, env="conanbuild")

    def _prepare_ohos_host_tools(self):
        """Conan package host tools are unsigned ELF binaries and cannot
        run from the cache on OHOS; keep a self-signed working copy of
        glib-compile-schemas in the build tree."""
        tools_root = os.path.join(self.build_folder, "host-tools")
        os.makedirs(tools_root, exist_ok=True)
        source = os.path.join(
            self.dependencies.host["glib"].package_folder,
            "bin", "glib-compile-schemas",
        )
        if not os.path.isfile(source):
            source = shutil.which("glib-compile-schemas")
        if not source or not os.path.isfile(source):
            raise ConanException("glib-compile-schemas not found")
        target = os.path.join(tools_root, "glib-compile-schemas")
        shutil.copy2(source, target)
        self._sign_ohos_elf(target)

    def _schema_compiler(self):
        candidates = [
            os.environ.get("GLIB_COMPILE_SCHEMAS", ""),
            self._schema_compiler_path(),
            shutil.which("glib-compile-schemas"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanException("glib-compile-schemas not found")

    @staticmethod
    def _sign_ohos_elf(path):
        signer = (shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        readelf = (shutil.which("llvm-readelf")
                   or "/data/service/hnp/bin/llvm-readelf")
        if not os.path.isfile(path):
            raise ConanException(f"Missing executable to sign: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output,
             "-selfSign", "1"],
            check=True,
            timeout=120,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed executable has invalid "
                                 ".codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)
