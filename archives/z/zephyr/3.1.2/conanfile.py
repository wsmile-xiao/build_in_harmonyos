#!/usr/bin/env python3
"""Conan recipe — zephyr 3.1.2 (autotools) for HarmonyOS PC (aarch64).

``zephyr`` is Project Athena's notification service (the original Zephyr IM
system).  This recipe packages its **core client library libzephyr** — the
artifact Debian ships as the ``libzephyr4`` binary package.

Scope
-----
Upstream ``SUBDIRS`` is ``lib clients server zhm zwgc``.  Only ``lib`` is
built here.  ``clients``/``server``/``zhm``/``zwgc`` are standalone programs
(Debian packages them separately as ``zephyr-clients``/``zephyr-server``),
``zwgc`` additionally needs the X11 client stack, and ``server``/``zwgc``
need c-ares for asynchronous DNS — none of which the library itself uses
(``HAVE_ARES`` appears only in ``server/`` and ``zwgc/``).  Restricting the
build to ``lib`` keeps the recipe free of X11 and runtime-service
dependencies while still shipping the complete public API
(``zephyr/zephyr.h``, ``zephyr/zephyr_err.h``, ``libzephyr.so``).

Adaptation notes (all of them are reproduced below with their rationale)
-----------------------------------------------------------------------
1. The upstream git archive ships ``configure.ac`` plus hand-written
   ``Makefile.in`` files but no ``configure`` and no ``Makefile.am`` — it is a
   pure autoconf project.  ``build()`` bootstraps with ``autoreconf -fi`` and
   pulls the autotools chain in through ``tool_requires`` (the OHOS worker
   image only carries the autoconf suite, no automake/libtool).
2. The OHOS image exposes the system autoconf suite under
   ``/data/service/hnp/bin`` first on ``PATH``, while the conan autotools
   packages export ``PERL5LIB`` for **their own** perl.  Mixing the two makes
   perl abort while loading an XS module (``Perl_my_cxt_init: symbol not
   found``).  The bootstrap therefore runs with the conan tool variables
   unset and ``PERL5LIB`` restricted to automake's perl module directory, so
   the system perl/autoconf and conan's automake/libtool form one consistent
   chain (see ``_bootstrap_env_prefix``).
3. ``compile_et`` (from e2fsprogs) generates ``zephyr_err.c``/``zephyr_err.h``.
   The shipped script hard-codes an empty prefix for its template directory
   and honours ``_ET_DIR_OVERRIDE``, which is pointed at the tool package.
4. automake/libtool ship a 2023 vintage ``config.sub`` that does not know
   ``ohos``, so an ``aarch64-unknown-linux-ohos`` triplet is rejected.  The
   generated ``config.sub`` is taught the HarmonyOS OS/kernel names after
   ``autoreconf`` (same edits as the repository's
   ``scripts/patch-autotools-ohos.pl``, plus the kernel/OS validation entry
   that script skips on this ``config.sub`` version — see
   ``_add_ohos_config_sub``).
5. ``configure.ac`` runs four krb5 signature probes *outside* the
   ``--with-krb5`` block.  krb5 is disabled here (the library is the
   non-Kerberos variant, matching ``libzephyr4``), and the probes cannot
   succeed without krb5 headers, so their autoconf cache entries are supplied
   explicitly (``KRB5_PROBE_CACHE``).
6. In-source build: ``lib/Makefile.in`` hard-codes ``${BUILDTOP}/h/zephyr/
   zephyr.h``, which only exists when the build happens in the source tree.
7. E114: HMDFS forces setgid on new directories, so ``umask 077 && mktemp -d``
   inside the freshly generated ``configure`` yields an unusable temp dir;
   ``umask 077`` is stripped before ``./configure`` runs.
8. E074: the HMDFS jobserver fifo is not usable, so ``make`` runs with ``-j1``.
9. The upstream test suite is Python 2 and is invoked as ``python``; both are
   ported by the patches in ``patches/`` (see ``notes.md``).  ``make check``
   keeps the API suite as the blocking gate and reports the
   documentation-style doctests without failing on them (they need a live
   Zephyr HostManager).
10. The OHOS PC build sandbox refuses ``dlopen`` of shared objects located in
   user directories (``Error loading shared library <path>: Permission
   denied``) while exec-time ``DT_NEEDED`` loading works, so the ctypes-based
   upstream suite is started from an embedded CPython launcher that links the
   freshly built library (and is signed, E077/E083).  The launcher is used only
   after a self-test that runs the mechanism the suite depends on
   (``ctypes.CDLL(None)`` resolving a libzephyr symbol); otherwise the suite
   keeps the plain interpreter.  See ``notes.md``.
"""
import glob
import json
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (apply_conandata_patches,
                               export_conandata_patches, get, save)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Upstream SUBDIRS minus the standalone programs (see module docstring).
BUILD_SUBDIRS = "lib"

# E077/E083: HarmonyOS refuses to map an ELF without a valid `.codesign`
# section, so `python3`/ctypes `dlopen` of a freshly linked library fails with
# `Permission denied`.  The signature has to be created where the library is
# actually loaded — the build tree, before the upstream suite runs.  The
# installed copy is a byte copy of the signed file and inherits the signature.
OHOS_SIGN_TOOL = "/data/service/hnp/bin/binary-sign-tool"
OHOS_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"

#: Embedded CPython launcher (note 10).  It links the freshly built library so
#: that it is mapped at exec time, because the build sandbox refuses
#: ``dlopen`` of shared objects in user directories.
PY_LAUNCHER_SOURCE = r"""
/* Embedded CPython launcher used as the interpreter for `make check`.
 *
 * The HarmonyOS PC build sandbox refuses dlopen() of shared objects located in
 * user directories ("Error loading shared library <path>: Permission denied")
 * while exec-time DT_NEEDED loading works.  Linking this launcher against the
 * freshly built library maps it into the process at exec time, and
 * python/zephyr_ctypes.py picks the symbols up through CDLL(None).
 *
 * The Python C API is declared by hand so that no development headers are
 * required (the OHOS python installation is shipped without them in some
 * environments).  The declarations match CPython 3.x.
 */
#include <stdio.h>
#include <wchar.h>

extern void Py_Initialize(void);
extern int Py_FinalizeEx(void);
extern void *PyMem_RawMalloc(size_t size);
extern wchar_t *Py_DecodeLocale(const char *arg, size_t *size);
extern void PySys_SetArgvEx(int argc, wchar_t **argv, int updatepath);
extern int PyRun_SimpleFileEx(FILE *fp, const char *filename, int closeit);

int main(int argc, char **argv)
{
    wchar_t **wargv;
    FILE *fp;
    int i;
    int rc;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <script.py> [args...]\n", argv[0]);
        return 2;
    }
    Py_Initialize();
    wargv = (wchar_t **)PyMem_RawMalloc(sizeof(wchar_t *) * (argc + 1));
    if (wargv == NULL)
        return 3;
    for (i = 0; i < argc; i++)
        wargv[i] = Py_DecodeLocale(argv[i], NULL);
    wargv[argc] = NULL;
    /* sys.argv == [script, args...], mirroring `python3 script args...` */
    PySys_SetArgvEx(argc - 1, wargv + 1, 0);
    fp = fopen(argv[1], "r");
    if (fp == NULL) {
        perror(argv[1]);
        return 4;
    }
    rc = PyRun_SimpleFileEx(fp, argv[1], 1);
    if (Py_FinalizeEx() < 0)
        rc = 120;
    return rc;
}
"""

#: Probe run with the build interpreter to locate libpython (the OHOS python
#: layout reports a staging LIBDIR and a virtual environment reports its own
#: libraryless prefix, so several candidate roots are globbed and reported
#: instead of trusting a single sysconfig value).
PY_RUNTIME_INFO_SOURCE = r"""
import glob, json, os, sys, sysconfig

py_version = "{0}.{1}".format(*sys.version_info[:2])
roots = []


def add(path):
    if path and os.path.isdir(path) and path not in roots:
        roots.append(path)


# A virtual environment (or a wrapper interpreter) reports its own prefix,
# which holds no shared library at all: the base installation and the real
# interpreter behind the symlink are candidate roots as well.
real_exe = os.path.realpath(sys.executable)
here = os.path.dirname(real_exe)
add(sys.prefix)
add(sys.base_prefix)
add(sys.base_exec_prefix)
add(sysconfig.get_config_var("LIBDIR"))
add(sysconfig.get_config_var("LIBPL"))
add(sysconfig.get_config_var("installed_base"))
add(sysconfig.get_config_var("installed_platbase"))
for directory in (here, os.path.join(here, os.pardir),
                  os.path.join(here, os.pardir, os.pardir)):
    add(directory)
    add(os.path.join(directory, "lib"))
paths = sysconfig.get_paths() or {}
for key in ("stdlib", "platstdlib", "purelib", "platlib", "include", "platinclude"):
    add(paths.get(key))
add(os.path.expanduser(os.path.join("~", "usr", "local")))
add(os.path.expanduser(os.path.join("~", "usr", "local", "lib")))

found = []
for root in roots:
    for pattern in ("libpython%s*.so*" % py_version,
                    os.path.join("lib", "libpython%s*.so*" % py_version)):
        for hit in sorted(glob.glob(os.path.join(root, pattern))):
            directory = os.path.dirname(os.path.abspath(hit))
            if directory not in found:
                found.append(directory)
json.dump({"py_version": py_version,
           "py_prefix": sys.base_prefix or sys.prefix,
           "executable": real_exe, "libdirs": found},
          open(sys.argv[1], "w"))
"""

#: Self-test for the launcher (note 10).  It must start the embedded
#: interpreter *and* resolve a libzephyr symbol from the process' global symbol
#: scope, which is the mechanism the upstream ctypes suite relies on
#: (``CDLL(None)``, see python/zephyr_ctypes.py).  Tying the self-test to the
#: real mechanism keeps the fallback honest: when the loader refuses the
#: launcher's DT_NEEDED chain, or the embedded interpreter cannot build its
#: stdlib path, the suite keeps plain python3 instead of failing differently.
PY_LAUNCHER_SELFTEST_SOURCE = r"""
import ctypes
import sys

lib = ctypes.CDLL(None)
if not hasattr(lib, "ZGetRealm"):
    raise SystemExit("libzephyr is not in the global symbol scope")

with open(sys.argv[1], "w") as handle:
    handle.write("ok %s ctypes=%s" % (sys.version.split()[0],
                                      ctypes.__name__))
"""

#: Interpreters tried for the launcher, most specific first: the interpreter of
#: the build environment, then the HNP one, which the PC images ship with a
#: shared libpython (barvinok/0.41.9, E2167).
PY_INTERPRETER_CANDIDATES = ("python3", "/data/service/hnp/bin/python3")

# autoconf cache entries for the unconditional krb5 signature probes (note 5).
KRB5_PROBE_CACHE = {
    "ac_cv_krb5_auth_con_getauthenticator_takes_double_pointer": "no",
    "ac_cv_krb5_auth_con_flags_type": "krb5_flags",
}

# Variables exported by the conan autotools packages that would drag their own
# perl/autoconf into the bootstrap (note 2).  They are unset for the autoreconf
# run so the system chain is used consistently, including the internal macro
# directories of the conan autoconf package (AC_MACRODIR & friends).
# ``ACLOCAL_PATH`` and ``_lt_pkgdatadir`` are intentionally kept: they carry
# the 3rd-party m4 macro directories and libtool's auxiliary data.
_CONAN_TOOL_VARS = ("AUTOCONF", "AUTOHEADER", "AUTOM4TE", "AUTORECONF",
                    "AUTOSCAN", "AUTOUPDATE", "IFNAMES", "AUTOMAKE", "ACLOCAL",
                    "LIBTOOLIZE", "PERL", "M4", "autom4te_perllibdir",
                    "AC_MACRODIR", "trailer_m4", "autom4te_buildauxdir")

# config.sub edits that teach it the HarmonyOS names (note 4).  The whole
# android-linux case, including its `;;` terminator, is matched so the new case
# is inserted after it; inserting before the `;;` would leave a case clause
# unterminated and make config.sub unparseable.
_CONFIG_SUB_TRIPLET_RE = re.compile(
    r"(\n(?P<i>[ \t]*)android-linux\)\s*\n"
    r"(?P=i)[ \t]*basic_machine=\$field1-unknown\s*\n"
    r"(?P=i)[ \t]*basic_os=linux-android\s*\n"
    r"(?P=i)[ \t]*;;\s*\n)")
_CONFIG_SUB_TRIPLET_ADD = ("\n%(i)sohos-linux)\n"
                           "%(i)s\tbasic_machine=$field1-unknown\n"
                           "%(i)s\tbasic_os=linux-ohos\n"
                           "%(i)s\t;;\n")
_CONFIG_SUB_OS_LIST = ("gnu* | android*", "gnu* | android* | ohos*")
_CONFIG_SUB_KERNEL_LIST = ("linux-musl*- | linux-relibc*- | linux-uclibc*- | linux-mlibc*- )",
                           "linux-musl*- | linux-relibc*- | linux-uclibc*- | linux-mlibc*- \\\n"
                           "\t   | linux-ohos*- )")


def _automake_share(conanfile):
    """Path to the automake perl module directory of the tool package."""
    pkg = conanfile.dependencies.build["automake"].package_folder
    share = os.path.join(pkg, "share")
    for entry in sorted(os.listdir(share)):
        if entry.startswith("automake-"):
            return os.path.join(share, entry)
    raise ConanException("automake module directory not found under %s" % share)


def _bootstrap_env_prefix(conanfile):
    """Environment prefix for the autoreconf bootstrap (note 2).

    ``unset`` + a ``PERL5LIB`` that only carries automake's own perl modules
    keeps the system perl/autoconf and conan's automake/libtool in one
    consistent tool chain.  ``ACLOCAL_PATH`` and ``_lt_pkgdatadir`` are left
    untouched: the packages export correct values for them.
    """
    return 'unset %s; PERL5LIB="%s" ' % (" ".join(_CONAN_TOOL_VARS),
                                         _automake_share(conanfile))


def _add_ohos_config_sub(conanfile, folder):
    """Teach the generated config.sub about HarmonyOS (note 4)."""
    path = os.path.join(folder, "config.sub")
    if not os.path.exists(path):
        conanfile.output.warn("config.sub not found, skipping OHOS triplet support")
        return
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        data = handle.read()
    original = data

    if "ohos-linux)" not in data:
        match = _CONFIG_SUB_TRIPLET_RE.search(data)
        if match:
            data = data.replace(match.group(1),
                                match.group(1) + _CONFIG_SUB_TRIPLET_ADD % {"i": match.group("i")})
        else:
            conanfile.output.warn("config.sub: android-linux case not found")

    if _CONFIG_SUB_OS_LIST[1] not in data:
        if _CONFIG_SUB_OS_LIST[0] in data:
            data = data.replace(*_CONFIG_SUB_OS_LIST, 1)
        else:
            conanfile.output.warn("config.sub: OS list entry 'gnu* | android*' not found")

    if _CONFIG_SUB_KERNEL_LIST[0] in data:
        data = data.replace(*_CONFIG_SUB_KERNEL_LIST, 1)
    elif "linux-ohos*" not in data:
        conanfile.output.warn("config.sub: kernel/OS validation list entry not found")

    if data == original:
        conanfile.output.warn("config.sub unchanged: OHOS triplet may not be recognised")
        return
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(data)
    conanfile.output.info("config.sub: HarmonyOS OS/kernel names added")


def _drop_umask_077(conanfile, path):
    """E114: drop `umask 077` from the freshly generated configure so that
    config.status can create its temp dir under HMDFS (note 7)."""
    if not os.path.exists(path):
        conanfile.output.warn("E114 guard: generated configure not found")
        return
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        data = handle.read()
    patched = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    patched = patched.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    if patched == data:
        conanfile.output.warn("E114 guard: umask 077 pattern absent in configure")
        return
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(patched)


class ZephyrConan(ConanFile):
    name = "zephyr"
    version = "3.1.2"
    description = ("Project Athena's notification service - core library "
                   "libzephyr (Zephyr instant-messaging client API)")
    license = "MIT"
    homepage = "https://github.com/zephyr-im/zephyr"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libzephyr links -lcom_err (lib/Makefile.in) and the public header
        # zephyr/zephyr.h includes <com_err.h>, so the dependency must be
        # visible to consumers (headers and libs) — not a private one.
        self.requires("e2fsprogs/1.47.4",
                      transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # autoreconf bootstrap (note 1) and compile_et (note 3).
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")
        self.tool_requires("e2fsprogs/1.47.4")

    def layout(self):
        # In-source build (note 6).
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def validate(self):
        # R32: settings.os must be compared against the (Linux, OHOS) pair.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "zephyr is only supported on Linux/OHOS, not " + str(self.settings.os))

    def source(self):
        get(self, **self.conan_data["sources"])
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R1: minimal configure args — com_err is the only mandatory
        # third-party library and upstream has no autodetection path for it.
        # The shared/static flags are already contributed by the toolchain
        # from the `shared` option, so they are not repeated here.
        tc.configure_args.append(
            "--with-com_err=%s" % self.dependencies["e2fsprogs"].package_folder)
        # note 5: krb5 probes run unconditionally upstream.
        for var, value in sorted(KRB5_PROBE_CACHE.items()):
            tc.configure_args.append("%s=%s" % (var, value))
        if self.settings.os in ("Linux", "OHOS"):
            # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS"),
            # so the triplet is passed explicitly; config.sub is taught the
            # names by _add_ohos_config_sub().
            tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # note 3: compile_et template directory of the tool package.
        env = tc.environment()
        env.define(
            "_ET_DIR_OVERRIDE",
            os.path.join(self.dependencies.build["e2fsprogs"].package_folder,
                         "share", "et"))
        tc.generate(env=env)
        # The exact configure argument list is needed by build() (note 10).
        self._zephyr_configure_args = list(tc.configure_args)

    def _shared_objects(self, directory):
        """Real (non-symlink) ``libzephyr.so.<version>`` files in *directory*.

        ``libzephyr.so`` and ``libzephyr.so.4`` are libtool symlinks onto the
        real object, which is the file the loader maps and therefore the file
        that has to carry the signature.
        """
        if not os.path.isdir(directory):
            return []
        out = []
        for name in sorted(os.listdir(directory)):
            path = os.path.join(directory, name)
            if (name.startswith("libzephyr.so.") and os.path.isfile(path)
                    and not os.path.islink(path)):
                out.append(path)
        return out

    def _codesign(self, path):
        """E077 step order: remove an old signature, sign, restore the mode.

        `binary-sign-tool` refuses to overwrite an existing `.codesign` section
        ("section already exists") and zeroes the file mode after signing, so
        the removal is tolerated and the mode is restored afterwards.  Like the
        other recipes in this repository (asciitex, arturo, aggdraw) the tool is
        resolved from SIGN_TOOL / PATH first, with the SDK location as fallback.
        """
        sign_tool = (os.environ.get("SIGN_TOOL")
                     or shutil.which("binary-sign-tool") or OHOS_SIGN_TOOL)
        if not os.path.isfile(sign_tool):
            self.output.warning(
                "binary-sign-tool not found; %s stays unsigned (E077/E083)"
                % os.path.relpath(path, self.build_folder))
            return
        objcopy = shutil.which("llvm-objcopy") or OHOS_OBJCOPY
        if os.path.isfile(objcopy):
            self.run('"%s" --remove-section .codesign "%s" 2>/dev/null || true'
                     % (objcopy, path))
        self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                 % (sign_tool, path, path))
        os.chmod(path, 0o755)
        self.output.info(
            "codesign: %s (mode=%s)"
            % (os.path.relpath(path, self.build_folder),
               oct(os.stat(path).st_mode & 0o777)))

    def _python_runtime_info(self, workdir, interpreter):
        """Ask one interpreter where its libpython lives (note 10).

        The shared library is not always next to the interpreter (the OHOS
        python layout reports a staging LIBDIR), so the interpreter reports
        every candidate root it can think of and the caller globs them.
        """
        script = os.path.join(workdir, "_zephyr_pyinfo.py")
        out = os.path.join(workdir, "_zephyr_pyinfo.json")
        save(self, script, PY_RUNTIME_INFO_SOURCE)
        if os.path.isfile(out):
            os.remove(out)
        self.run('"%s" "%s" "%s"' % (interpreter, script, out), cwd=workdir,
                 env="conanbuild", ignore_errors=True)
        if not os.path.isfile(out):
            return None
        with open(out, encoding="utf-8") as handle:
            return json.load(handle)

    def _find_libpython(self, info):
        """First existing libpython of the probing interpreter, or None."""
        pattern = "libpython%s*.so*" % info["py_version"]
        for directory in info["libdirs"]:
            for candidate in (sorted(glob.glob(os.path.join(directory, pattern)))
                              + sorted(glob.glob(
                                  os.path.join(directory, "lib", pattern)))):
                if os.path.isfile(candidate):
                    return candidate
        return None

    def _launcher_self_test(self, exe, workdir, home):
        """Run the launcher; return the environment prefix it needs, else None.

        ``home`` (a PYTHONHOME candidate) is only used when the launcher cannot
        build its module search path on its own: the embedded interpreter is
        started from a build directory, so the prefix normally comes from the
        interpreter libpython was built for.
        """
        script = os.path.join(workdir, "_zephyr_launcher_selftest.py")
        out = os.path.join(workdir, "_zephyr_launcher_selftest.out")
        save(self, script, PY_LAUNCHER_SELFTEST_SOURCE)
        if os.path.isfile(out):
            os.remove(out)
        env_prefix = 'PYTHONHOME="%s" ' % home if home else ""
        self.run(env_prefix + '"%s" "%s" "%s"' % (exe, script, out),
                 cwd=workdir, env="conanbuild", ignore_errors=True)
        if not os.path.isfile(out):
            return None
        with open(out, encoding="utf-8") as handle:
            self.output.info("launcher self-test: %s" % handle.read().strip())
        return env_prefix.strip()

    def _build_python_launcher(self, workdir):
        """Build, sign and self-test the embedded interpreter for `make check`.

        Returns ``(launcher, extra_env)``, where ``extra_env`` is the make
        command-line variable the launcher needs ("" when it runs with the
        inherited environment), or None when no self-tested launcher could be
        produced on this host — the caller then keeps plain python3 and the
        upstream suite behaves exactly as it did without this adaptation.

        Note 10: dlopen() of a shared object below a user directory is refused
        by the build sandboxes (E2167), while exec-time DT_NEEDED loading of the
        same file works, so the suite is started from an interpreter that links
        the freshly built library as one of its own NEEDED entries.
        """
        libzephyr = os.path.join(self.build_folder, "lib", ".libs",
                                 "libzephyr.so")
        libsdir = os.path.dirname(libzephyr)
        if not os.path.isfile(libzephyr):
            self.output.warning("libzephyr.so is not built: the upstream suite "
                                "will run with plain python3")
            return None
        source = os.path.join(workdir, "_zephyr_launcher.c")
        exe = os.path.join(workdir, "_zephyr_python_launcher")
        save(self, source, PY_LAUNCHER_SOURCE)
        compiler = os.environ.get("CC") or "clang"
        for interpreter in PY_INTERPRETER_CANDIDATES:
            info = self._python_runtime_info(workdir, interpreter)
            if not info:
                continue
            libpython = self._find_libpython(info)
            if not libpython:
                self.output.warning(
                    "%s reports no shared libpython: trying the next "
                    "interpreter" % interpreter)
                continue
            homes = [""]
            prefix = info.get("py_prefix")
            if prefix and os.path.isdir(os.path.join(
                    prefix, "lib", "python" + info["py_version"])):
                homes.append(prefix)
            if os.path.isfile(exe):
                os.remove(exe)
            # The libraries are linked by path, so the NEEDED entries come from
            # their SONAMEs; the rpaths are what the loader uses at exec time
            # (no LD_LIBRARY_PATH is involved).
            self.run(
                '"{cc}" -o "{exe}" "{src}" "{libpy}" "{libz}" '
                '-Wl,-rpath,"{libpydir}" -Wl,-rpath,"{libs}" '
                "-Wl,-rpath,'$ORIGIN/lib/.libs'".format(
                    cc=compiler, exe=exe, src=source, libpy=libpython,
                    libz=libzephyr, libpydir=os.path.dirname(libpython),
                    libs=libsdir),
                cwd=workdir, env="conanbuild", ignore_errors=True)
            if not os.path.isfile(exe):
                self.output.warning("launcher compile failed (%s, libpython %s)"
                                    % (interpreter, libpython))
                continue
            # E077: an unsigned ELF cannot be executed on OHOS.
            self._codesign(exe)
            for home in homes:
                extra_env = self._launcher_self_test(exe, workdir, home)
                if extra_env is not None:
                    self.output.info(
                        "upstream suite launcher: %s (%s%s)"
                        % (exe, libpython,
                           ", %s" % extra_env if extra_env else ""))
                    return exe, extra_env
        self.output.warning(
            "no self-tested launcher on this host: the upstream suite will run "
            "with plain python3")
        return None

    def build(self):
        # note 1/2: bootstrap configure with a consistent autotools chain.
        self.run(_bootstrap_env_prefix(self) + "autoreconf -fi",
                 cwd=self.source_folder, env="conanbuild")
        _add_ohos_config_sub(self, self.source_folder)
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        # note 10: the OHOS profile exports CONFIG_SHELL/SHELL pointing at the
        # HNP bash, under which this configure aborts with "working directory
        # cannot be determined" (getcwd fails inside the re-executed shell).
        # /bin/sh (toybox sh) is used for configure and — through the @SHELL@
        # substitution — for the generated makefiles as well.
        configure = os.path.join(self.source_folder, "configure")
        args = " ".join(shlex.quote(a) for a in self._zephyr_configure_args)
        self.run('CONFIG_SHELL=/bin/sh SHELL=/bin/sh "%s" %s' % (configure, args),
                 cwd=self.source_folder, env="conanbuild")
        autotools = Autotools(self)
        # E074: parallel make hits the HMDFS jobserver fifo EPERM (note 8).
        autotools.make(args=["-j1", "SUBDIRS=%s" % BUILD_SUBDIRS])
        # note 13: OHOS refuses to map an unsigned ELF, so the library must be
        # signed *before* the upstream suite dlopens it through ctypes
        # (E077/E083; without this, CI fails at check-unit with
        # "Error loading shared library ...: Permission denied").
        check_args = ["-j1", "SUBDIRS=%s" % BUILD_SUBDIRS]
        if self.settings.os == "OHOS":
            for library in self._shared_objects(
                    os.path.join(self.build_folder, "lib", ".libs")):
                self._codesign(library)
            # note 10: the sandbox refuses dlopen() of user-directory shared
            # objects, so the ctypes suite runs inside a launcher that has the
            # library mapped at exec time.  PYTHON must be a make command-line
            # variable: an environment prefix is overridden by the Makefile's
            # own assignment (E2167, barvinok #33918).
            launcher = self._build_python_launcher(self.build_folder)
            if launcher:
                exe, extra_env = launcher
                check_args.append('PYTHON="%s"' % exe)
                if extra_env:
                    check_args.append(extra_env)
        # R51/L1: upstream test suite (note 9).
        autotools.make(target="check", args=check_args)

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["SUBDIRS=%s" % BUILD_SUBDIRS])

    def package_info(self):
        self.cpp_info.libs = ["zephyr"]
        # e2fsprogs (com_err) is propagated through requirements() with
        # transitive_headers/transitive_libs because zephyr/zephyr.h includes
        # <com_err.h> and libzephyr links the com_err archive.
        self.cpp_info.requires = ["e2fsprogs::com_err"]
