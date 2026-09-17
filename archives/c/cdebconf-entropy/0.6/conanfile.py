#!/usr/bin/env python3
"""Conan recipe — cdebconf-entropy 0.6 (Autotools, configure bypass).

cdebconf-entropy (Debian Installer Team) provides entropy plugins for
cdebconf: text-plugin-entropy (always built), newt-plugin-entropy
(optional, libnewt) and gtk-plugin-entropy (optional, GTK2).
Upstream: https://salsa.debian.org/installer-team/cdebconf-entropy
Tarball: cdebconf-entropy_0.60.tar.xz (Debian pool, sha256 verified
against the 0.60 .dsc). Task version directory is 0.6, which maps to
upstream release 0.60 (Debian has no 0.6 release; 0.60 is the current
stable tarball in pool).

Build: autotools-style (configure.ac + Makefile.in, no pre-generated
configure in the tarball). The Debian configure step probes textwrap
(AC_CHECK_LIB), pkg-config for libnewt and gtk+-x11-2.0/gtk+-x11-3.0,
then substitutes Makefile.in -> Makefile (AC_SUBST of
prefix/CC/CFLAGS/FRONTENDS/...). The HMBS device has no working
autotools bootstrap chain (cdebconf-terminal 0.49 preflight 2026-09-09:
`autoreconf` not found; conan automake/1.18 `aclocal` wrapper fails on
hardlink/chmod-less HMDFS; conan libtool/2.5.4 `libtoolize` aborts for
missing m4), so this recipe deliberately declares NO tool_requires and
replicates the exact configure.ac logic in Python (textwrap probe +
pkg-config frontend probing + Makefile.in substitution). The compiled
plugins are the real upstream sources with real flags — no stubs.
Hard deps libdebconfclient/libdebian-installer come from cdebconf/0.283
(requires). The GTK2 GUI stack is absent on OHOS so the gtk plugin is
skipped when pkg-config cannot detect it, mirroring configure's
`echo "*** Cannot build GTK+ plugin ***"` branch. The text plugin has
no GUI deps and is always built.

Install: cdebconf entropy plugin .so files
(lib/cdebconf/frontend/<frontend>/plugin-entropy.so layout, same mapping
as upstream `make install`, performed with pure-Python copies in
package() so it does not depend on device `install(1)`/chmod).
test_package requires the text plugin to
exist and verifies newt/gtk consistency live (re-probing pkg-config)
instead of hardcoding an empty install.

Upstream tests: none — audited tarball file list (HACKING,
Makefile.in, autogen.sh, configure.ac, gtk-plugin-entropy.c,
newt-plugin-entropy.c, text-plugin-entropy.c, debian/) has no tests/
dir, no TESTS / check_PROGRAMS targets; see test_package/MANIFEST.yml
audit.
"""
import glob
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


class CdebconfEntropyConan(ConanFile):
    name = "cdebconf-entropy"
    version = "0.6"
    description = "cdebconf entropy plugins (text/newt/gtk) from Debian Installer Team"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/installer-team/cdebconf-entropy"
    url = "https://salsa.debian.org/installer-team/cdebconf-entropy"

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

        configure.ac starts with FRONTENDS="text", runs
        AC_CHECK_LIB([textwrap], ...) for TEXTWRAP_LIBS, then
        PKG_CHECK_MODULES([NEWT], [libnewt]) and PKG_CHECK_MODULES([GTK],
        [gtk+-x11-2.0] or [gtk+-x11-3.0]); on failure each branch only
        echoes "*** Cannot build ... plugin ***" and leaves FRONTENDS
        without that entry. Returns (frontends, textwrap_libs,
        newt_cflags, newt_libs, gtk_cflags, gtk_libs).
        """
        pc = _pkg_config()
        # textwrap is optional (AC_CHECK_LIB); OHOS has no libtextwrap,
        # so this stays empty — same as configure on a system without it.
        textwrap_libs = ""
        frontends = ["text"]
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
        rc2, _, _ = _run_capture('"%s" --exists "gtk+-x11-2.0"' % pc)
        rc3, _, _ = _run_capture('"%s" --exists "gtk+-x11-3.0"' % pc)
        if rc2 == 0:
            _, gtk_cflags, _ = _run_capture(
                '"%s" --cflags "gtk+-x11-2.0"' % pc)
            _, gtk_libs, _ = _run_capture(
                '"%s" --libs "gtk+-x11-2.0"' % pc)
            frontends.append("gtk")
            self.output.info("frontend gtk enabled (GTK2 GTK_CFLAGS=%r "
                             "GTK_LIBS=%r)" % (gtk_cflags, gtk_libs))
        elif rc3 == 0:
            _, gtk_cflags, _ = _run_capture(
                '"%s" --cflags "gtk+-x11-3.0"' % pc)
            _, gtk_libs, _ = _run_capture(
                '"%s" --libs "gtk+-x11-3.0"' % pc)
            frontends.append("gtk")
            self.output.info("frontend gtk enabled (GTK3 GTK_CFLAGS=%r "
                             "GTK_LIBS=%r)" % (gtk_cflags, gtk_libs))
        else:
            self.output.info("*** Cannot build GTK+ plugin *** "
                             "(pkg-config cannot find gtk+-x11-2.0/3.0)")
        return (" ".join(frontends), textwrap_libs, newt_cflags, newt_libs,
                gtk_cflags, gtk_libs)

    def _write_makefile(self):
        """Generate Makefile from Makefile.in (configure AC_OUTPUT)."""
        frontends, textwrap_libs, newt_cflags, newt_libs, gtk_cflags, \
            gtk_libs = self._detect_frontends()
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
            "@PACKAGE@": "entropy",
            "@CC@": cc,
            "@CFLAGS@": cflags,
            "@CPPFLAGS@": cppflags,
            "@LDFLAGS@": ldflags,
            "@TEXTWRAP_LIBS@": textwrap_libs,
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
        self.output.info("configure bypass: FRONTENDS=%r CC=%r"
                         % (frontends, cc))
        out = os.path.join(self.source_folder, "Makefile")
        with open(out, "w", encoding="utf-8") as f:
            f.write(content)
        return frontends

    def build(self):
        # Debian tarball ships no pre-generated configure and the device
        # cannot run the autotools bootstrap (see module docstring), so
        # generate Makefile directly from Makefile.in instead of
        # autoreconf/configure. The text plugin has no GUI deps and is
        # always built; newt/gtk are appended only when detectable.
        # NOTE: only `make` runs here. Installation is done in package()
        # with pure-Python copies mirroring upstream `make install`
        # (lib/cdebconf/frontend/<frontend>/plugin-entropy.so) so the
        # result does not depend on the device `install(1)` binary or on
        # chmod (HMDFS reports chmod=0; `install -m644` is fragile there).
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
        # Fail fast if the link step did not emit the expected .so files
        # (upstream `all` must always produce at least text-plugin.so).
        built = sorted(glob.glob(os.path.join(self.source_folder,
                                              "*-plugin-entropy.so")))
        self.output.info("built plugins: %r"
                         % ([os.path.basename(p) for p in built],))
        missing = ["%s-plugin-entropy.so" % f
                   for f in frontends.split() if f]
        for expect in missing:
            cand = os.path.join(self.source_folder, expect)
            if not (os.path.isfile(cand)
                    and os.path.getsize(cand) > 0):
                raise RuntimeError(
                    "expected plugin %s missing/empty after make "
                    "(source dir listing: %r)"
                    % (expect, sorted(os.listdir(self.source_folder))))
        if "gtk" not in frontends.split() or "newt" not in frontends.split():
            self.output.info(
                "optional frontend(s) skipped (missing libnewt and/or "
                "gtk+-x11 stack) - text plugin always built, mirroring "
                "upstream configure with undetectable GUI stacks")

    def package(self):
        # Mirror upstream `make install` mapping in pure Python:
        #   for p in $(PLUGIN_MODULES); do
        #     install -d $(DESTDIR)/$(moddir)/${p%%-*}
        #     install $p $(DESTDIR)/$(moddir)/${p%%-*}/${p#*-}
        #   done
        # i.e. <front>-plugin-entropy.so ->
        # lib/cdebconf/frontend/<front>/plugin-entropy.so.
        # Python copies avoid the device `install(1)` helper and any
        # implicit chmod (unsupported on HMDFS).
        built = sorted(glob.glob(os.path.join(self.source_folder,
                                              "*-plugin-entropy.so")))
        if not built:
            raise RuntimeError(
                "no *-plugin-entropy.so built in %r (listing: %r)"
                % (self.source_folder,
                   sorted(os.listdir(self.source_folder))))
        for src in built:
            base = os.path.basename(src)
            if "-" not in base:
                continue
            front, rest = base.split("-", 1)
            dst_dir = os.path.join(self.package_folder, "lib", "cdebconf",
                                   "frontend", front)
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, rest)
            shutil.copyfile(src, dst)
            try:
                # CI workers dlopen the packaged .so; ensure it is
                # readable even if the build-tree umask/mode is odd.
                # Best-effort: HMDFS reports chmod=0, never fail there.
                os.chmod(dst, 0o644)
            except Exception:
                pass
            self.output.info("installed %s -> %s"
                             % (base, os.path.relpath(dst,
                                                      self.package_folder)))
        # The text plugin has no GUI deps and is always built upstream.
        text_dst = os.path.join(self.package_folder, "lib", "cdebconf",
                                "frontend", "text", "plugin-entropy.so")
        if not (os.path.isfile(text_dst)
                and os.path.getsize(text_dst) > 0):
            raise RuntimeError(
                "text plugin missing/empty after package install "
                "(package listing: %r)"
                % (sorted(os.listdir(self.package_folder))))

    def package_info(self):
        # Entropy plugins are dlopened .so files, not link-time libs.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib", "libexec/cdebconf"]
        self.cpp_info.bindirs = []
