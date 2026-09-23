#!/usr/bin/env python3
"""Conan recipe — cdebconf-terminal 0.49 (Autotools, configure bypass).

cdebconf-terminal (Debian Installer Team) provides terminal plugins for
cdebconf: gtk-plugin-terminal (GTK/VTE) and newt-plugin-terminal (newt).
Upstream: https://salsa.debian.org/installer-team/cdebconf-terminal
Tarball: cdebconf-terminal_0.49.tar.xz (Debian pool, sha256 verified
against the 0.49 .dsc).

Build: autotools-style (configure.ac + Makefile.in, no pre-generated
configure in the tarball). The Debian configure step is trivial — it only
probes pkg-config for libnewt / gtk+-x11-2.0+vte and substitutes
Makefile.in -> Makefile (AC_SUBST of prefix/CC/CFLAGS/FRONTENDS/...).
The HMBS device has no working autotools bootstrap chain (preflight
2026-09-09: `autoreconf` not found; conan automake/1.18 `aclocal` wrapper
fails with `.aclocal-real: No such file or directory` on hardlink/chmod-less
HMDFS; conan libtool/2.5.4 `libtoolize` aborts with `One of these is
required: gm4 gnum4 m4`), so this recipe deliberately declares NO
tool_requires and replicates the exact configure.ac logic in Python
(pkg-config frontend probing + Makefile.in substitution). The compiled
plugins are the real upstream sources with real flags — no stubs.
Hard deps libdebconfclient/libdebian-installer come from cdebconf/0.283
(requires). The GTK2/VTE-0.28 GUI stack is absent on OHOS so the gtk
plugin is skipped when pkg-config cannot detect it, mirroring configure's
`echo "*** Cannot build GTK+ plugin ***"` branch.

Install: cdebconf terminal plugin .so files
(lib/cdebconf/frontend/<frontend>/plugin-terminal.so layout, same as
upstream `make install`). On OHOS neither libnewt nor the GTK2/VTE-0.28
stack is detectable, so FRONTENDS is legitimately empty and `make install`
ships zero plugins — exactly what upstream configure+make would produce
here. test_package verifies that consistency live (re-probing pkg-config)
instead of demanding a plugin upstream itself would not build.

Upstream tests: none — audited tarball file list (HACKING,
Makefile.in, autogen.sh, configure.ac, gtk-plugin-terminal.c,
newt-plugin-terminal.c, debian/) has no tests/ dir, no TESTS /
check_PROGRAMS targets; see test_package/MANIFEST.yml audit.
"""
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import get, chdir, export_conandata_patches


def _run_capture(cmd):
    """Run a shell command, return (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True,
                              text=True, timeout=60)
        return (proc.returncode, (proc.stdout or "").strip(),
                (proc.stderr or "").strip())
    except Exception as exc:  # pragma: no cover - defensive
        return 127, "", str(exc)


def _pkg_config():
    """Resolve pkg-config (PATH first, hnp tool dir fallback)."""
    found = shutil.which("pkg-config")
    if found:
        return found
    for cand in ("/data/service/hnp/bin/pkg-config",
                 "/usr/bin/pkg-config"):
        if os.path.isfile(cand):
            return cand
    return "pkg-config"


class CdebconfTerminalConan(ConanFile):
    name = "cdebconf-terminal"
    version = "0.49"
    description = "cdebconf terminal plugins (gtk/newt) from Debian Installer Team"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/installer-team/cdebconf-terminal"
    url = "https://salsa.debian.org/installer-team/cdebconf-terminal"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    # Plugin API + libdebconfclient come from cdebconf (same team).
    # cdebconf 0.283 self-contains libdebian-installer, so requiring it
    # gives us both hard deps without vendoring them twice.
    requires = "cdebconf/0.283"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        # Forward the writable HMBS tmp root into the conanbuild env
        # (device /tmp is read-only). Make/configure-equivalent temp
        # files honor TMPDIR; without this builds fail with
        # "can't create temporary file /tmp/....tmp: Read-only file
        # system".
        tmp = self._writable_tmpdir()
        env = Environment()
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        env.define("SHELL", "/bin/sh")
        env.define("CONFIG_SHELL", "/bin/sh")
        env.vars(self, scope="build").save_script("hmbs_env")

    def _writable_tmpdir(self):
        # Prefer HMBS-provided writable roots; fall back to a build-tree
        # tmp dir. Probe with mkstemp so we never return a read-only dir.
        for var in ("HMBS_AUTOCONF_MKTEMP_FALLBACK", "HMBS_TMPDIR",
                    "TMPDIR", "TMP", "TEMP"):
            d = os.environ.get(var)
            if not d or d in ("0", "1"):
                continue
            if os.path.isdir(d):
                try:
                    fd, p = tempfile.mkstemp(dir=d)
                    os.close(fd)
                    os.unlink(p)
                    return d
                except Exception:
                    continue
        d = os.path.join(self.build_folder, "tmp")
        os.makedirs(d, exist_ok=True)
        return d

    def _detect_frontends(self):
        """Mirror configure.ac frontend probing via pkg-config.

        configure.ac runs PKG_CHECK_MODULES([NEWT], [libnewt]) then (with
        --with-gtk-version defaulting to 2) PKG_CHECK_MODULES([GTK],
        [gtk+-x11-2.0 vte]); on failure each branch only echoes
        "*** Cannot build ... plugin ***" and leaves FRONTENDS without
        that entry. Returns (frontends, newt_cflags, newt_libs,
        gtk_cflags, gtk_libs).
        """
        pc = _pkg_config()
        frontends = []
        newt_cflags, newt_libs = "", ""
        rc, _, _ = _run_capture('"%s" --exists libnewt' % pc)
        if rc == 0:
            _, newt_cflags, _ = _run_capture('"%s" --cflags libnewt' % pc)
            _, newt_libs, _ = _run_capture('"%s" --libs libnewt' % pc)
            frontends.append("newt")
            self.output.info("frontend newt enabled (NEWT_CFLAGS=%r "
                             "NEWT_LIBS=%r)" % (newt_cflags, newt_libs))
        else:
            self.output.info("*** Cannot build Newt plugin *** "
                             "(pkg-config cannot find libnewt)")
        gtk_cflags, gtk_libs = "", ""
        rc, _, _ = _run_capture('"%s" --exists "gtk+-x11-2.0 vte"' % pc)
        if rc == 0:
            _, gtk_cflags, _ = _run_capture(
                '"%s" --cflags "gtk+-x11-2.0 vte"' % pc)
            _, gtk_libs, _ = _run_capture(
                '"%s" --libs "gtk+-x11-2.0 vte"' % pc)
            frontends.append("gtk")
            self.output.info("frontend gtk enabled (GTK_CFLAGS=%r "
                             "GTK_LIBS=%r)" % (gtk_cflags, gtk_libs))
        else:
            self.output.info("*** Cannot build GTK+ plugin *** "
                             "(pkg-config cannot find gtk+-x11-2.0 vte)")
        return (" ".join(frontends), newt_cflags, newt_libs,
                gtk_cflags, gtk_libs)

    def _write_makefile(self):
        """Generate Makefile from Makefile.in (configure AC_OUTPUT)."""
        frontends, newt_cflags, newt_libs, gtk_cflags, gtk_libs = \
            self._detect_frontends()
        cdebconf_pkg = self.dependencies["cdebconf"].package_folder
        cc = (os.environ.get("CC")
              or shutil.which("cc")
              or shutil.which("clang")
              or "cc")
        # Honor profile CC/CFLAGS/CPPFLAGS/LDFLAGS from the environment
        # (what AC_PROG_CC/configure would pick up) and append the
        # cdebconf plugin-API include/lib paths, mirroring the previous
        # `env CFLAGS=... ./configure` invocation.
        cflags = (os.environ.get("CFLAGS", "")
                  + " -I%s/include" % cdebconf_pkg).strip()
        cppflags = (os.environ.get("CPPFLAGS", "")
                    + " -I%s/include" % cdebconf_pkg).strip()
        ldflags = (os.environ.get("LDFLAGS", "")
                   + " -L%s/lib" % cdebconf_pkg).strip()
        subs = {
            "@prefix@": self.package_folder,
            "@sysconfdir@": "${prefix}/etc",
            "@PACKAGE@": "terminal",
            "@CC@": cc,
            "@CFLAGS@": cflags,
            "@CPPFLAGS@": cppflags,
            "@LDFLAGS@": ldflags,
            "@NEWT_CFLAGS@": newt_cflags,
            "@NEWT_LIBS@": newt_libs,
            "@GTK_CFLAGS@": gtk_cflags,
            "@GTK_LIBS@": gtk_libs,
            "@FRONTENDS@": frontends,
        }
        template = os.path.join(self.source_folder, "Makefile.in")
        with open(template, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        for key, value in subs.items():
            content = content.replace(key, value)
        self.output.info("configure bypass: FRONTENDS=%r CC=%r" % (frontends, cc))
        out = os.path.join(self.source_folder, "Makefile")
        with open(out, "w", encoding="utf-8") as f:
            f.write(content)
        return frontends

    def build(self):
        # Debian tarball ships no pre-generated configure and the device
        # cannot run the autotools bootstrap (see module docstring), so
        # generate Makefile directly from Makefile.in instead of
        # autoreconf/configure. With empty FRONTENDS (OHOS lacks both GUI
        # stacks) `make`/`make install` are trivially successful no-ops,
        # exactly as configure+make would be.
        tmp = self._writable_tmpdir()
        os.makedirs(tmp, exist_ok=True)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = tmp
        os.environ["SHELL"] = "/bin/sh"
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        frontends = self._write_makefile()
        with chdir(self, self.source_folder):
            # --build/--host equivalent: config.guess cannot identify
            # HarmonyOS; upstream is treated as aarch64 Linux (same as
            # cdebconf 0.283). No configure script exists, so the triplet
            # only matters via the profile CC/CFLAGS, already honored.
            self.run("make -j1", env="conanbuild")
            self.run("make install", env="conanbuild")
        if not frontends:
            self.output.warning(
                "no frontends detected (missing libnewt and gtk+-2.0/vte) "
                "- package installs zero plugins, mirroring upstream "
                "configure with undetectable GUI stacks")

    def package(self):
        # build() already ran `make install` into package_folder.
        pass

    def package_info(self):
        # Terminal plugins are dlopened .so files, not link-time libs.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib", "libexec/cdebconf"]
        self.cpp_info.bindirs = []
