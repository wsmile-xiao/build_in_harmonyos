#!/usr/bin/env python3
"""Conan recipe — xymon 4.3.30 (Xymon network/host/service monitor) for HarmonyOS PC.

Upstream: https://sourceforge.net/projects/xymon/files/Xymon/4.3.30/

OHOS adaptations (each one is required for the upstream build to work on OHOS):

 1. `configure.server` is an interactive shell script -> answers are fed on stdin.
 2. OHOS has no shebang support -> every build script is invoked through bash.
 3. No `gcc` on OHOS -> platform Makefiles are forced to clang.
 4. Platform detection based on `uname` -> pinned to build/Makefile.Linux.
 5. `rpc/rpc.h` is provided by libtirpc as <tirpc/rpc/rpc.h>.
 6. OHOS libc has no getrpcbyname() -> local stub via macro in xymonnet.c.
 7. Cross-compiled probe programs (lfs / test-endianness / test-*) cannot run on
    the build machine -> skipped and their results hard-coded.
 8. build/Makefile builds helper ELF tools (merge-sects, merge-lines, ...) which
    are used by `make install` -> their build rules must be preserved.
 9. An empty `-Wl,--rpath,` would swallow the following object file at link time.
10. rrdtool >= 1.9 needs RRDTOOL12 for the 8-argument rrd_graph() API.
11. HMDFS (the FUSE filesystem backing the Conan cache) denies *symlink
    resolution* inside Conan's build process tree: `os.path.isfile("libX.so")`
    returns False for `libX.so -> libX.so.X.Y.Z`, and ld.lld correspondingly
    reports "unable to find library -lX" for a library that *is* present.
    openldap and rrdtool ship shared libraries, so the dependency lib dirs are
    materialised without ever traversing a symlink (`_materialize_shims`
    synthesises the unversioned `libX.so` alias from the versioned real file).
12. `make install` creates links itself, and HMDFS denies *both* symlink and
    hard-link creation. The mandatory ones are rewritten to real copies in the
    Makefiles (`bin/bb` & friends as cp, `$(XYMONHOME)/xymon.sh` as cp from the
    real bindir, every CGI script as a cp of `cgiwrap`); the *optional*
    `$(XYMONHOME)/{bin,etc,ext,tmp,web,www}` links are materialised as real
    directories after `make install` (`_materialize_package_links`).
"""
import os
import shutil
import stat as stat_mod
import tarfile
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
)
from conan.tools.layout import basic_layout

_TARBALL_ROOT = "xymon-4.3.30"


class XymonConan(ConanFile):
    name = "xymon"
    version = "4.3.30"
    package_type = "application"
    license = "GPL-2.0-only"
    homepage = "https://xymon.sourceforge.net/"
    url = "https://sourceforge.net/projects/xymon/files/"
    description = "Xymon network/host/service monitoring system (OHOS adaptation)"
    topics = ("monitoring", "network", "server", "alerting")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_rrd": [True, False],
        "with_ssl": [True, False],
        "with_ldap": [True, False],
        "with_cares": [True, False],
    }
    default_options = {
        "with_rrd": True,
        "with_ssl": True,
        "with_ldap": True,
        "with_cares": True,
    }

    # ── helpers ──────────────────────────────────────────────────────────

    _HNP_BIN = "/data/service/hnp/bin"

    def _hnp_bin(self):
        """Directory that holds the OHOS native tools (bash, clang, ...)."""
        candidates = []
        for key in ("CONFIG_SHELL", "SHELL"):
            value = os.environ.get(key, "")
            if value:
                candidates.append(os.path.dirname(value))
        candidates.append(self._HNP_BIN)
        for cand in candidates:
            if cand and os.path.isfile(os.path.join(cand, "bash")):
                return cand
        return self._HNP_BIN

    def _dep(self, name):
        return str(self.dependencies[name].package_folder)

    # dependency lib dirs are copied here (see _materialize_shims)
    _SHIM_NAMES = ("zlib", "pcre", "libtirpc", "openssl", "c-ares",
                   "openldap", "rrdtool")
    _shim_libdirs = {}

    def _libdir(self, name):
        """Linker search dir for a dependency, free of HMDFS symlinks."""
        shim = self._shim_libdirs.get(name)
        if shim:
            return shim
        return os.path.join(self._dep(name), "lib")

    def _materialize_shims(self):
        """Copy every dependency lib dir into a symlink-free scratch dir.

        Rationale (see module docstring, item 11): the Conan cache lives on
        HMDFS, where resolving a symlink is denied inside Conan's build process
        tree.  Even `os.path.isfile("libfoo.so")` returns False for
        `libfoo.so -> libfoo.so.X.Y.Z`, and ld.lld then reports
        "unable to find library -lfoo" although the library exists.

        The shim must therefore never traverse a symlink: it copies the real
        files and *synthesises* the unversioned `libfoo.so` alias itself from
        the versioned real file.  openldap and rrdtool are the shared
        dependencies; the other five ship static archives, whose `.a` files are
        regular files and copy verbatim.  The copies keep their SONAME, so the
        produced binaries are identical to a symlink-based link.
        """
        shims = {}
        root = self._root()
        for name in self._SHIM_NAMES:
            if name not in self.dependencies:
                continue
            src = os.path.join(self._dep(name), "lib")
            if not os.path.isdir(src):
                continue
            dst = os.path.join(root, "_shlibs", name)
            os.makedirs(dst, exist_ok=True)
            shims[name] = dst
            for entry in os.listdir(src):
                if not (entry.endswith(".a") or ".so" in entry):
                    continue
                target = os.path.join(src, entry)
                try:
                    st = os.lstat(target)
                except OSError:
                    continue
                # lstat does not follow the link, so it works on HMDFS; only
                # regular files are copied, symlinks are ignored on purpose.
                if not stat_mod.S_ISREG(st.st_mode):
                    continue
                self._copy_file(target, os.path.join(dst, entry))
                if ".so." in entry:
                    alias = entry.split(".so.", 1)[0] + ".so"
                    alias_path = os.path.join(dst, alias)
                    if not os.path.isfile(alias_path):
                        self._copy_file(target, alias_path)
        self._shim_libdirs = shims
        return shims

    @staticmethod
    def _copy_file(src, dst):
        """Copy a file, retrying a few times (HMDFS I/O is flaky)."""
        for attempt in range(6):
            try:
                shutil.copyfile(src, dst)
                return
            except OSError:
                if attempt == 5:
                    raise
                time.sleep(0.25)

    def _root(self):
        """Folder that holds the extracted xymon tree during build()."""
        if os.path.isfile(os.path.join(self.build_folder, "configure.server")):
            return self.build_folder
        return self.source_folder

    # ── conan entry points ───────────────────────────────────────────────

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("xymon only builds on Linux/OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Build in place: the xymon build system generates its own Makefile in
        # the top directory and the patches must land on the extracted tree.
        basic_layout(self, build_folder=".")

    def source(self):
        src = self.conan_data["sources"][self.version]
        tar_path = os.path.join(self.source_folder, "xymon-src.tar.gz")
        if os.path.isfile(tar_path):
            os.remove(tar_path)
        download(self, src["url"], tar_path, sha256=src["sha256"])
        with tarfile.open(tar_path, "r:gz") as tar:
            members = tar.getmembers()
            by_name = {m.name: m for m in members}
            # 1st pass: plain files and directories
            for m in members:
                rel = self._strip_root(m.name)
                if rel is None:
                    continue
                dst = os.path.join(self.source_folder, rel)
                if m.isdir():
                    os.makedirs(dst, exist_ok=True)
                elif m.isfile():
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    src_f = tar.extractfile(m)
                    if src_f is not None:
                        with open(dst, "wb") as out:
                            out.write(src_f.read())
            # 2nd pass: materialise symlinks as regular files (HMDFS on OHOS
            # does not reliably support symlink creation).
            for m in members:
                if not (m.issym() or m.islnk()):
                    continue
                rel = self._strip_root(m.name)
                if rel is None:
                    continue
                dst = os.path.join(self.source_folder, rel)
                if m.linkname.startswith("/"):
                    target = m.linkname.lstrip("/")
                else:
                    target = os.path.normpath(
                        os.path.join(os.path.dirname(m.name), m.linkname)
                    )
                tgt = by_name.get(target)
                if tgt is not None and tgt.isfile():
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    src_f = tar.extractfile(tgt)
                    if src_f is not None:
                        with open(dst, "wb") as out:
                            out.write(src_f.read())
        os.remove(tar_path)

    @staticmethod
    def _strip_root(name):
        prefix = _TARBALL_ROOT + "/"
        if not name.startswith(prefix):
            return None
        rel = name[len(prefix):]
        return rel or None

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("pcre/8.45")
        self.requires("libtirpc/1.3.7")
        if self.options.with_ssl:
            self.requires("openssl/3.5.8.1")
        if self.options.with_cares:
            self.requires("c-ares/1.34.6")
        if self.options.with_ldap:
            self.requires("openldap/2.6.7")
        if self.options.with_rrd:
            self.requires("rrdtool/1.9.0")

    # ── configure helpers ────────────────────────────────────────────────

    def _configure_args(self):
        args = ["--server", "--fping", "xymonping"]
        pcre = self._dep("pcre")
        args += ["--pcreinclude", pcre + "/include",
                 "--pcrelib", self._libdir("pcre")]
        if self.options.with_ssl:
            p = self._dep("openssl")
            args += ["--sslinclude", p + "/include",
                     "--ssllib", self._libdir("openssl")]
        if self.options.with_cares:
            p = self._dep("c-ares")
            args += ["--caresinclude", p + "/include",
                     "--careslib", self._libdir("c-ares")]
        if self.options.with_ldap:
            p = self._dep("openldap")
            args += ["--ldapinclude", p + "/include",
                     "--ldaplib", self._libdir("openldap")]
        if self.options.with_rrd:
            p = self._dep("rrdtool")
            args += ["--rrdinclude", p + "/include",
                     "--rrdlib", self._libdir("rrdtool")]
        return args

    def _configure_env(self):
        pkg = self.package_folder
        pcre = self._dep("pcre")
        env = {
            "XYMONUSER": "xymon",
            "XYMONTOPDIR": pkg,
            "XYMONVAR": pkg + "/var",
            "XYMONLOGDIR": pkg + "/var/log",
            "CGIDIR": pkg + "/cgi-bin",
            "SECURECGIDIR": pkg + "/cgi-secure",
            "MANROOT": pkg + "/share/man",
            "HTTPDGID": "nobody",
            "XYMONHOSTNAME": "localhost",
            "XYMONHOSTIP": "127.0.0.1",
            "XYMONHOSTURL": "/xymon",
            "XYMONCGIURL": "/xymon-cgi",
            "SECUREXYMONCGIURL": "/xymon-seccgi",
            "ENABLESSL": "y" if self.options.with_ssl else "n",
            "ENABLELDAP": "y" if self.options.with_ldap else "n",
            "USEXYMONPING": "y",
            "INSTALLBINDIR": pkg + "/bin",
            "INSTALLETCDIR": pkg + "/etc",
            "INSTALLEXTDIR": pkg + "/libexec",
            "INSTALLTMPDIR": pkg + "/tmp",
            "INSTALLWEBDIR": pkg + "/www",
            "INSTALLWWWDIR": pkg + "/www",
            "OS": "Linux",
            "MAKE": "make",
            "USERPCREINC": pcre + "/include",
            "USERPCRELIB": self._libdir("pcre"),
            "PCREOK": "YES",
            "CARESOK": "YES",
            "SSLOK": "YES",
            "LDAPOK": "YES",
            "RRDOK": "YES",
            "LIBRTDEF": "",
            "ENABLERRD": "y" if self.options.with_rrd else "n",
        }
        if self.options.with_ssl:
            p = self._dep("openssl")
            env["USEROSSLINC"] = p + "/include"
            env["USEROSSLLIB"] = self._libdir("openssl")
        if self.options.with_cares:
            p = self._dep("c-ares")
            env["USERCARESINC"] = p + "/include"
            env["USERCARESLIB"] = self._libdir("c-ares")
        if self.options.with_ldap:
            p = self._dep("openldap")
            env["USERLDAPINC"] = p + "/include"
            env["USERLDAPLIB"] = self._libdir("openldap")
        if self.options.with_rrd:
            p = self._dep("rrdtool")
            env["USERRRDINC"] = p + "/include"
            env["USERRRDLIB"] = self._libdir("rrdtool")
        return env

    # ── patch helpers ────────────────────────────────────────────────────

    def _replace(self, rel_path, pairs):
        path = os.path.join(self._root(), rel_path)
        if not os.path.isfile(path):
            return
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            text = fh.read()
        original = text
        for old, new in pairs:
            text = text.replace(old, new)
        if text != original:
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(text)

    def _strip_shebang(self, rel_path):
        path = os.path.join(self._root(), rel_path)
        if not os.path.isfile(path):
            return
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            text = fh.read()
        if text.startswith("#!/bin/sh\n"):
            text = text[10:]
        elif text.startswith("#!/bin/sh"):
            text = text[9:]
        with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
            fh.write(text)

    def _patch_scripts(self):
        bdir = os.path.join(self._root(), "build")
        if os.path.isdir(bdir):
            for name in os.listdir(bdir):
                if name.endswith(".sh") and os.path.isfile(os.path.join(bdir, name)):
                    self._strip_shebang(os.path.join("build", name))
                    self._replace(
                        os.path.join("build", name),
                        [("`uname -s | sed -e's@/@_@g'`", "Linux")],
                    )
            # lfs.sh cross-compiles and executes a probe; hard-code the answer.
            lfs = os.path.join(bdir, "lfs.sh")
            if os.path.isfile(lfs):
                with open(lfs, "w", encoding="utf-8") as fh:
                    fh.write('echo "Large File Support OK (OHOS: cross-compile probe skipped)"\n'
                             'LIBRTDEF=""\n')
        for name in ("configure", "configure.server"):
            self._strip_shebang(name)

    def _patch_configure_server(self):
        self._replace("configure", [
            ("exec $BASEDIR/configure.server $*", ". $BASEDIR/configure.server $*"),
        ])
        self._replace("configure.server", [
            # `uname` does not report a platform that ships a Makefile here.
            ("build/Makefile.`uname -s | tr '/' '_'`", "build/Makefile.Linux"),
            ("XYMONHOSTOS=`uname -s | tr '[A-Z]' '[a-z]'`", "XYMONHOSTOS=linux"),
            # replacing . build/*.sh probes with their (known) results
            (". build/pcre.sh", 'PCREOK="YES"'),
            (". build/c-ares.sh", 'CARESOK="YES"'),
            (". build/ssl.sh", 'SSLOK="YES"'),
            (". build/ldap.sh", 'LDAPOK="YES"'),
            (". build/rrd.sh", 'RRDOK="YES"'),
            (". build/clock-gettime-librt.sh", 'LIBRTDEF=""'),
            (". build/fping.sh", 'FPINGVER="xymonping"'),
        ])

    def _patch_build_makefile(self):
        """Keep build/Makefile untouched.

        merge-lines / merge-sects / setup-newfiles / renamevars / renametasks are
        compiled ELF helpers listed in the `all: $(TOOLS)` target and are invoked
        by `make install`.  Removing their build rules makes the install fail, so
        the only thing done here is to make sure CFLAGS reaches them (it does,
        through the exported CFLAGS variable).
        """
        return

    def _patch_genconfig(self):
        self._replace("build/genconfig.sh", [
            ("$CC -o build/testfile $CFLAGS build/test-pathmax.c 1>/dev/null 2>&1\n"
             "if test -x build/testfile; then ./build/testfile >>include/config.h; fi",
             'echo "#define PATH_MAX 4096" >>include/config.h'),
            ("$CC -o build/testfile $CFLAGS build/test-shutdown.c 1>/dev/null 2>&1\n"
             "if test -x build/testfile; then ./build/testfile >>include/config.h; fi",
             'echo "#define SHUT_RD 0" >>include/config.h\n'
             'echo "#define SHUT_WR 1" >>include/config.h\n'
             'echo "#define SHUT_RDWR 2" >>include/config.h'),
        ])

    def _patch_lib_makefile(self):
        pcre = self._dep("pcre")
        self._replace("lib/Makefile", [
            ("CC = cc\n", "CC = clang\n"),
            ("CC = gcc\n", "CC = clang\n"),
            # test-endianness is compiled *and executed* -> cannot run on a
            # cross-compiled aarch64 target from here; hard-code little endian.
            ("all: test-endianness $(XYMONLIB)", "all: $(XYMONLIB)"),
            ("client: test-endianness $(XYMONCLIENTLIB)", "client: $(XYMONCLIENTLIB)"),
            ("test-endianness: test-endianness.c\n\t$(CC) $(CFLAGS) -o $@ $<\n",
             "# test-endianness probe skipped on OHOS\n"),
            ("`./test-endianness`", "-DXYMON_LITTLE_ENDIAN"),
            ("CFLAGS += -I../include", "CFLAGS += -I../include -I" + pcre + "/include -DXYMON_LITTLE_ENDIAN"),
        ])

    def _patch_platform_makefiles(self):
        for name in ("Makefile.Linux", "Makefile.generic"):
            # Use += so the CFLAGS exported by the generated top Makefile
            # (which carries all the Conan include paths) is preserved.
            self._replace(os.path.join("build", name), [
                ("CFLAGS = -g -O2 -Wall -Wno-unused -Wno-pointer-sign -D_REENTRANT $(LFSDEF) $(OSDEF)",
                 "CFLAGS += $(LFSDEF) $(OSDEF)"),
                ("CFLAGS = -g -O2 -Wall -Wno-unused -D_REENTRANT $(LFSDEF) $(OSDEF)",
                 "CFLAGS += $(LFSDEF) $(OSDEF)"),
                ("CC = gcc", "CC = clang"),
                ("CC = cc", "CC = clang"),
            ])

    def _patch_xymonnet(self):
        cares = self._dep("c-ares")
        tirpc = self._dep("libtirpc")
        tirpc_inc = os.path.join(tirpc, "include", "tirpc")
        self._replace("xymonnet/Makefile", [
            ("ifeq ($(SYSTEMCARES),no)\n"
             "\tCARESINC = -I./c-ares\n"
             "\tCARESLIBS = libcares.a\n"
             "\tLOCALCARES = libcares.a\n"
             "endif",
             "SYSTEMCARES=yes\n"
             "CARESINC = -I" + cares + "/include\n"
             "CARESLIBS = -L" + self._libdir("c-ares") + " -lcares\n"
             "LOCALCARES ="),
            ("$(CC) $(CFLAGS) $(SSLFLAGS) $(LDAPFLAGS) $(SSLINCDIR) $(LDAPINCDIR) -c -o $@ xymonnet.c",
             "$(CC) $(CFLAGS) $(SSLFLAGS) $(LDAPFLAGS) $(SSLINCDIR) $(LDAPINCDIR) "
             "-I" + tirpc_inc + " -c -o $@ xymonnet.c"),
            # an empty $(RPATHOPT) would make the linker treat the following
            # object file as the rpath argument -> drop it from the link line
            ("\t$(CC) $(CFLAGS) -o $@ $(RPATHOPT) $(NETTESTOBJS)",
             "\t$(CC) $(CFLAGS) -o $@ $(NETTESTOBJS)"),
        ])
        if "getrpcbyname" in self._read("xymonnet/xymonnet.c"):
            self._replace("xymonnet/xymonnet.c", [
                ("#include <rpc/rpc.h>",
                 "#include <rpc/rpc.h>\n"
                 "#ifdef OHOS\n"
                 "/* OHOS libc has no getrpcbyname(): provide a local no-op stub. */\n"
                 "static inline struct rpcent *xymon_getrpcbyname(char *name)\n"
                 "{ (void)name; return NULL; }\n"
                 "#define getrpcbyname(x) xymon_getrpcbyname(x)\n"
                 "#endif"),
            ])

    def _read(self, rel_path):
        path = os.path.join(self._root(), rel_path)
        if not os.path.isfile(path):
            return ""
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            return fh.read()

    def _patch_install_symlinks(self):
        """Replace the mandatory install-time links with real copies.

        HMDFS denies both `ln -s` and `ln -f` (hard links).  These sites do not
        tolerate failure (unlike the optional $(XYMONHOME)/* links in
        build/Makefile.rules, which are guarded by `|| true`):

          * common/Makefile  - the BigBrother compatibility names in bin/
            (bb/bbcmd/...); also exercised by the consumer test.
          * xymond/Makefile  - $(XYMONHOME)/xymon.sh, whose upstream source is
            addressed through the $(XYMONHOME)/bin symlink that cannot exist
            here, so the real bindir is referenced instead.
          * web/Makefile     - every CGI script is a hard link to the single
            `cgiwrap` binary (upstream dispatch relies on argv[0], which a copy
            preserves).
        """
        self._replace("common/Makefile", [
            ("\tcd $(INSTALLROOT)$(INSTALLBINDIR)/; rm -f bb bbcmd bbhostgrep "
             "bbhostshow; ln -s xymon bb; ln -s xymoncmd bbcmd; ln -s xymongrep "
             "bbhostgrep; ln -s xymondigest bbdigest; ln -s xymoncfg bbhostshow",
             "\tcd $(INSTALLROOT)$(INSTALLBINDIR)/; rm -f bb bbcmd bbhostgrep "
             "bbhostshow; cp -fp xymon bb; cp -fp xymoncmd bbcmd; cp -fp xymongrep "
             "bbhostgrep; cp -fp xymondigest bbdigest; cp -fp xymoncfg bbhostshow"),
        ])
        self._replace("xymond/Makefile", [
            ("\tcd $(INSTALLROOT)$(XYMONHOME); rm -f xymon.sh; "
             "ln -sf bin/xymon.sh .",
             "\tcd $(INSTALLROOT)$(XYMONHOME); rm -f xymon.sh; "
             "cp -f $(INSTALLROOT)$(INSTALLBINDIR)/xymon.sh ."),
        ])
        self._replace("web/Makefile", [
            (" do ln -f $(INSTALLROOT)$(INSTALLBINDIR)/cgiwrap",
             " do cp -f $(INSTALLROOT)$(INSTALLBINDIR)/cgiwrap"),
        ])

    def _patch_script_invocations(self):
        """OHOS does not execute scripts through shebangs -> prefix with bash.

        Only *shell scripts* are wrapped: merge-sects / merge-lines are compiled
        ELF helpers and must be executed directly.
        """
        self._replace("xymond/Makefile", [
            ("../build/bb-commands.sh", "bash ../build/bb-commands.sh"),
        ])
        self._replace("client/Makefile", [
            ("../build/bb-commands.sh", "bash ../build/bb-commands.sh"),
        ])
        self._replace("xymonnet/Makefile", [
            ("\t../build/convert-bbservices", "\tbash ../build/convert-bbservices"),
        ])

    def _patch_top_makefile(self):
        """Inject the Conan-provided toolchain / dependency settings.

        Must happen *after* configure generated the Makefile and *before*
        `include build/Makefile.rules` is reached, because Makefile.rules is what
        turns these variables into compiler flags.
        """
        zlib = self._dep("zlib")
        pcre = self._dep("pcre")
        block = [
            "",
            "# === Conan injected (OHOS) ===",
            "PKGBUILD = yes",
            "CC = clang",
            "AR = llvm-ar",
            "RANLIB = llvm-ranlib",
            "ZLIBINCDIR = -I" + zlib + "/include",
            "ZLIBLIBS = -L" + self._libdir("zlib") + " -lz",
            "PCREINCDIR = -I" + pcre + "/include",
            "PCRELIBS = -L" + self._libdir("pcre") + " -lpcre",
            "NETLIBS = -L" + self._libdir("libtirpc") + " -ltirpc",
        ]
        if self.options.with_ssl:
            p = self._dep("openssl")
            block += ["SSLINCDIR = -I" + p + "/include",
                      "SSLLIBS = -L" + self._libdir("openssl") + " -lssl -lcrypto"]
        if self.options.with_cares:
            p = self._dep("c-ares")
            block += ["CARESINCDIR = -I" + p + "/include",
                      "CARESLIBS = -L" + self._libdir("c-ares") + " -lcares"]
        if self.options.with_ldap:
            p = self._dep("openldap")
            block += ["LDAPINCDIR = -I" + p + "/include",
                      "LDAPLIBS = -L" + self._libdir("openldap") + " -lldap -llber"]
        if self.options.with_rrd:
            p = self._dep("rrdtool")
            block += ["RRDINCDIR = -I" + p + "/include",
                      "RRDLIBS = -L" + self._libdir("rrdtool") + " -lrrd",
                      "RRDDEF = -DRRDTOOL12"]
        block += [
            "OSDEF = -DOHOS",
            "RPATH =",
            "RPATHOPT =",
            "export CC",
            "export CFLAGS = -g -O2 -Wall -Wno-unused -D_REENTRANT "
            "-D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64 -DOHOS "
            "-I$(BUILDTOPDIR)/include $(ZLIBINCDIR) $(PCREINCDIR) "
            "$(SSLINCDIR) $(CARESINCDIR) $(LDAPINCDIR) $(RRDINCDIR)",
            "",
        ]
        text = self._read("Makefile")
        if not text:
            raise ConanException("top-level Makefile was not generated by configure")
        marker = "\ninclude build/Makefile.rules"
        injected = "\n" + "\n".join(block) + "\n"
        pos = text.find(marker)
        if pos > 0:
            text = text[:pos] + injected + text[pos:]
        else:
            text += injected
        with open(os.path.join(self._root(), "Makefile"), "w",
                  encoding="utf-8", errors="surrogateescape") as fh:
            fh.write(text)

    # ── build / package ──────────────────────────────────────────────────

    def _run_logged(self, bash, command, log_name="_build.log"):
        """Run a build command with its stdout/stderr redirected to a file.

        Conan wires the child stdio to its own stderr. On the OHOS worker that
        stream can be a pipe (the CI harness runs `conan create ... | tee log`),
        and a broken pipe there swallows the compiler diagnostics and reduces a
        real failure to a bare "Error 1". Writing the build log to a file keeps
        the diagnostics intact; on failure the tail is echoed so the error is
        still visible in the conan output.
        """
        script = (
            command + " > " + log_name + " 2>&1 || "
            '{ echo "--- ' + log_name + ' (last 80 lines) ---"; '
            'tail -n 80 ' + log_name + '; exit 1; }'
        )
        self.run(bash + " -c '" + script + "'", cwd=self._root())

    def build(self):
        apply_conandata_patches(self)

        # A fully deterministic environment: drop anything the ambient shell may
        # carry and re-create the colour variables explicitly (R33).
        for key in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "LIBS",
                    "PKG_CONFIG_PATH", "PKG_CONFIG_LIBDIR", "LD_LIBRARY_PATH",
                    "CMAKE_PREFIX_PATH", "BASH_ENV"):
            os.environ.pop(key, None)
        os.environ["CC"] = "clang"
        os.environ["AR"] = "llvm-ar"
        os.environ["RANLIB"] = "llvm-ranlib"
        hnp = self._hnp_bin()
        parts = [p for p in os.environ.get("PATH", "").split(":")
                 if p and p != hnp]
        os.environ["PATH"] = os.pathsep.join([hnp] + parts)

        root = self._root()
        os.makedirs(os.path.join(root, "_tmp"), exist_ok=True)
        os.environ["TMPDIR"] = os.path.join(root, "_tmp")

        # Remove the dependency symlink lookups from the link step (see item 11).
        self._materialize_shims()

        self._patch_scripts()
        self._patch_configure_server()
        self._patch_build_makefile()
        self._patch_genconfig()
        self._patch_lib_makefile()
        self._patch_platform_makefiles()
        self._patch_xymonnet()
        self._patch_script_invocations()
        self._patch_install_symlinks()

        bash = os.path.join(self._hnp_bin(), "bash")
        cfg = os.path.join(root, "configure.server")
        args = " ".join('"' + a + '"' for a in self._configure_args())
        env = " ".join(k + '="' + v + '"' for k, v in self._configure_env().items())
        stdin_path = os.path.join(root, "configure.stdin")
        with open(stdin_path, "w", encoding="utf-8") as fh:
            # configure.server asks a handful of questions; the defaults are all
            # acceptable for a package build.
            fh.write("y\ny\n" + "\n" * 12)
        self.run(env + " " + bash + " " + cfg + " " + args + " < " + stdin_path,
                 cwd=root)
        os.remove(stdin_path)

        self._patch_top_makefile()
        self.run("MAKE='make' " + bash + " build/genconfig.sh", cwd=root)
        self._run_logged(bash, "make", "_make.log")

    def package(self):
        hnp = self._hnp_bin()
        bash = os.path.join(hnp, "bash")
        self._run_logged(bash, "make install INSTALL=/bin/install", "_install.log")
        copy(self, "COPYING", src=self._root(),
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_binaries()
        self._materialize_package_links()

    def _materialize_package_links(self):
        """Give the package the real files that upstream installs as symlinks.

        `build/Makefile.rules` wants `$(XYMONHOME)/{bin,etc,ext,tmp,web,www}` to
        point at the real install dirs (they are guarded by `|| true`, so on
        HMDFS they silently end up missing).  Copying is the OHOS equivalent of
        a symlink; it is done *after* `make install` so the sources are complete
        and *after* `_sign_binaries()` so the duplicated ELFs keep a valid
        signature.

        The copy *merges* because `install-client` already created some of these
        directories itself (it writes the client tools into $(XYMONHOME)/bin and
        its config into $(XYMONHOME)/etc); merging reproduces the union a
        symlink would expose, whereas skipping would leave `server/bin` with the
        client tools only.
        """
        env = self._configure_env()
        home = os.path.join(self.package_folder, "server")
        for rel, env_key in (("bin", "INSTALLBINDIR"),
                             ("etc", "INSTALLETCDIR"),
                             ("ext", "INSTALLEXTDIR"),
                             ("tmp", "INSTALLTMPDIR"),
                             ("web", "INSTALLWEBDIR"),
                             ("www", "INSTALLWWWDIR")):
            src = env[env_key]
            dst = os.path.join(home, rel)
            if os.path.isdir(src) and not os.path.islink(dst):
                shutil.copytree(src, dst, symlinks=False, dirs_exist_ok=True)

    def _sign_binaries(self):
        """Self-sign every packaged ELF so OHOS can load it.

        The whole package is walked rather than just bin/: the CGI scripts are
        copies of the `cgiwrap` ELF and `install-client` also drops ELFs into
        server/bin, so every one of them needs a signature.  Running before
        `_materialize_package_links()` means the duplicated binaries inherit a
        valid signature instead of needing a second signing pass.
        """
        signer = os.path.join(self._hnp_bin(), "binary-sign-tool")
        objcopy = os.path.join(self._hnp_bin(), "llvm-objcopy")
        if str(self.settings.os) != "OHOS" or not os.path.isfile(signer):
            return
        for dirpath, _dirnames, filenames in os.walk(self.package_folder):
            for name in filenames:
                path = os.path.join(dirpath, name)
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                try:
                    with open(path, "rb") as fh:
                        if fh.read(4) != b"\x7fELF":
                            continue
                except OSError:
                    continue
                self.run(objcopy + ' --remove-section .codesign "' + path + '" '
                         "2>/dev/null || true", quiet=True)
                self.run(signer + ' sign -inFile "' + path + '" -outFile "' + path
                         + '" -selfSign 1', quiet=True)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "xymon")
