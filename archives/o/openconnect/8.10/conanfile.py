#!/usr/bin/env python3
"""Conan recipe for openconnect 8.10 — OpenConnect VPN client (C, autotools).

openconnect is the client application for OpenConnect/Cisco AnyConnect
(and Juniper/Pulse/GlobalProtect) SSL VPN gateways. It is the sister
client of ocserv (the server). This recipe cross-builds the openconnect
executable (plus the libopenconnect static library and headers) for
HarmonyOS PC (aarch64, musl, clang 15).

Build system: official infradead.org release tarball ships a
pre-generated configure (no autoreconf needed, no automake/libtool
tool_requires).

Key adaptation notes (all verified on device during exploration):
- Source tarball: official www.infradead.org release (R39 official
  source), sha256 30e64c6e...
- OHOS musl <linux/tcp.h> pulls in <linux/socket.h> which redefines
  struct sockaddr_storage already provided by <sys/socket.h> →
  patches/0001 switches cstp.c/gpst.c to <netinet/tcp.h> under
  __OHOS__ (TCP_INFO + struct tcp_info are available there too).
- musl does not leak <stdlib.h> through other system headers (glibc
  does) → patches/0002 adds explicit #include <stdlib.h> to the 8
  files using malloc/calloc/free/exit/setenv/mkstemp/atoi but not
  including it (upstream -Werror-implicit-function-declaration).
- The 2020-era libtool (2.4.6 ltmain.sh shipped in the tarball)
  generates broken libtool scripts under autoconf 2.72: template
  variables ($AR/$oldobjs/...) expand at assignment time inside
  double quotes → "ar cru" with no arguments, "chmod 644" with no
  file. _fix_libtool_quoting() rewrites the damaged double-quoted
  assignments back to single-quoted (deferred expansion) semantics
  after configure, plus replaces the ksh-style ECHO="print -r --"
  with printf (no print builtin in this environment's /bin/sh).
- config.status uses "umask 077 && mktemp" for its temp dir; on
  HMDFS the 0700 dir makes subs1.awk creation fail (Permission
  denied) → _fix_config_status() drops the umask prefix and chmods
  the tmp dir (opensp/ncurses/cattle precedent).
- ohpcd binary packages were built with prefix=/ and their .la files
  carry libdir='//lib' / stale dependency_libs paths → libtool
  aborts with "not a valid libtool archive" during the final link.
  _fix_dependency_la_paths() rewrites libdir and cross-package
  references to the actual conan cache folders (cattle-1.0/CI#16082
  precedent, adapted to openconnect's gnutls dependency chain).
- make must run with -j1: the OHOS sandbox does not support mkfifo
  (automake jobserver), and 'make -j2' silently degrades (opensp
  precedent) or hits HMDFS races.
- openconnect produces libopenconnect.la + sbin/openconnect. With
  --disable-shared the .a is misnamed lib.a by the broken libname
  resolution; this recipe only ships the executable + headers and
  deletes the stray library artefacts (application package).
- Optional features disabled to minimise the dependency surface
  (W0-verified absent from the ohpcd registry): lz4, libproxy,
  stoken, libpcsclite, libpskc, gssapi, java. Core VPN functionality
  (AnyConnect/nc/pulse/gp protocols, HOTP/TOTP software tokens,
  DTLS, ESP) is unaffected — see 'openconnect --version' output.
- --disable-symvers: the AX_CHECK_VSCRIPT-generated version-script
  link commands are mangled by the same libtool quoting bug; symbol
  versioning is cosmetic for an application package.
- ELF executables must be signed (binary-sign-tool -selfSign) before
  they can run on OHOS.

R32: settings.os checked with in ("Linux", "OHOS").
R33: no reliance on ambient shell CC/CFLAGS — AutotoolsToolchain.
R38: CLI tool package — commands.json declared at software level.
"""
import glob
import os
import time
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class OpenconnectConan(ConanFile):
    name = "openconnect"
    version = "8.10"
    description = (
        "OpenConnect VPN client for Cisco AnyConnect, Juniper and "
        "GlobalProtect/Pulse SSL VPN gateways (ocserv's sister client)"
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://www.infradead.org/openconnect/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported"
            )

    def requirements(self):
        # W0 verified on the ohpcd registry via `conan download --only-recipe`
        # (2026-09-02). gnutls transitively provides nettle/hogweed,
        # libtasn1, libgcrypt, libgpg-error, gmp and libunistring.
        self.requires("gnutls/3.8.10")
        # configure unconditionally PKG_CHECK_MODULES(libxml-2.0) — hard dep.
        self.requires("libxml2/2.15.3")
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # The official infradead.org server intermittently rate-limits
        # CI worker egress IPs (HTTP 429 — see PR #7713 CI builds
        # #36947/#36955/#36961). conan's get() tries a URL exactly once;
        # wrap it with backoff retries so transient 429s don't abort the
        # build (mirror prefixes don't exist for this host; retries are
        # the only compliant option, R39 official source preserved).
        last_err = None
        for attempt in range(3):
            try:
                get(self, **self.conan_data["sources"], strip_root=True)
                break
            except ConanException as e:
                last_err = e
                if attempt < 2:
                    wait = 30 * (attempt + 1)
                    self.output.warn(
                        f"source download attempt {attempt + 1} failed "
                        f"({e}); retrying in {wait}s "
                        f"({2 - attempt} left)")
                    time.sleep(wait)
        else:
            raise last_err
        # E490: autotools helper scripts must be executable after
        # extraction (HMDFS may not preserve the tarball modes).
        for script in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing", "compile", "depcomp",
                       "ltmain.sh", "config.rpath"):
            p = os.path.join(self.source_folder, script)
            if os.path.isfile(p):
                os.chmod(p, 0o755)

    def generate(self):
        # ROOT CAUSE fix for '//lib/…' libtool failures (PR #7713
        # builds #36820..#37167): the default prefix='/' makes the
        # toolchain pass --libdir='${prefix}/lib' → '//lib', which
        # libtool then uses to resolve dependency .la search paths.
        # Absolute prefixes get mangled into nested relative paths by
        # this old configure's cross mode, so use a short RELATIVE
        # prefix and copy from build/pkg in package().
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # autoconf 2.72 + old config.guess (2018) cannot detect OHOS
            "--build=aarch64-unknown-linux-gnu",
            # ROOT CAUSE of the '//lib/libgpg-error.la' CI failures: the
            # default prefix='/' passes --libdir='${prefix}/lib' → '//lib'
            # which libtool uses for dependency .la resolution. Absolute
            # dir args verified working (build+link green); this configure's
            # cross mode treats them as relative for INSTALL paths, which
            # package() un-nests below.
            f"--libdir={self.package_folder}/lib",
            f"--bindir={self.package_folder}/bin",
            f"--sbindir={self.package_folder}/bin",
            f"--includedir={self.package_folder}/include",
            f"--oldincludedir={self.package_folder}/include",
            "--host=aarch64-unknown-linux-ohos",
            # distribution packaging default (no /etc/vpnc on build host)
            "--with-vpnc-script=/etc/vpnc/vpnc-script",
            # application package: only the executable is shipped
            "--disable-shared",
            # version-script link cmds mangled by libtool quoting bug
            "--disable-symvers",
            # optional deps not in the ohpcd registry (W0 verified)
            "--without-lz4",
            "--without-libproxy",
            "--without-stoken",
            "--without-libpcsclite",
            "--without-libpskc",
            "--without-gssapi",
            "--without-java",
        ])
        tc.generate()
        # PkgConfigDeps: generate .pc files so that configure's
        # PKG_CHECK_MODULES(gnutls/libxml-2.0/zlib) resolves the conan
        # packages (air-quality-sensor precedent — AutotoolsDeps alone
        # only feeds -I/-L/-l flags, not pkg-config lookups).
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        self._strip_pthread_from_generated_pc()

    def _strip_pthread_from_generated_pc(self):
        """Remove '-lpthread' from the generated gpg-error.pc.

        libgpg-error's conan recipe declares system_libs=['pthread'];
        PkgConfigDeps then emits 'Libs: ... -lpthread'. On OHOS/musl
        pthread lives inside libc (there is no libpthread.so), so the
        flag is harmless for the compiler — but this project's libtool
        (old ltmain.sh, see _fix_libtool_quoting) resolves -lpthread
        against .la files and derives a bogus '../.libs/libpthread.a'
        which aborts the link with 'no such file or directory'.
        Stripping the flag from the generated .pc is the minimal fix.
        """
        gen_dir = os.path.join(self.generators_folder)
        for pc in glob.glob(os.path.join(gen_dir, "*.pc")):
            try:
                content = load(self, pc)
            except Exception:
                continue
            if content and "-lpthread" in content:
                patched = re.sub(r"\s+-lpthread\b", "", content)
                save(self, pc, patched)
                self.output.info(f"stripped -lpthread from {pc}")

    # ------------------------------------------------------------------
    # OHOS build-workaround helpers (all discovered during on-device
    # exploration; see module docstring for the full explanation)
    # ------------------------------------------------------------------
    def _fix_libtool_quoting(self):
        """Repair the libtool script generated by config.status.

        The 2020 tarball's ltmain.sh predates autoconf 2.72's config.status
        escaping: template command variables are emitted double-quoted, so
        $AR/$oldobjs/... expand (to empty) at assignment time. Rewrite the
        damaged assignments to single quotes (deferred expansion). Also
        replace the ksh-style ECHO with printf.
        """
        lt = os.path.join(self.build_folder, "libtool")
        if not os.path.isfile(lt):
            return
        content = load(self, lt)
        if content is None:
            return
        lines = content.split("\n")
        template_vars = (
            "$AR", "$AR_FLAGS", "$RANLIB", "$CC", "$LD", "$libobjs",
            "$deplibs", "$compiler_flags", "$soname", "$lib", "$oldobjs",
            "$oldlib", "$objdir", "$wl", "$pic_flag", "$convenience",
            "$export_symbols", "$output_objdir", "$libname", "$dlname",
            "$install_libdir", "$dir", "$inst_prefix_dir", "$name",
            "$rename", "$dest", "$file", "$chmodcmd", "$reload_flag",
            "$output", "$reload_objs", "$libdir", "$release",
            "$shared_ext", "$versuffix", "$major",
        )
        out = []
        for line in lines:
            m = re.match(r'^([a-z_]+)="(.*)"\s*$', line)
            if m and "'" not in m.group(2) and any(
                    tv in m.group(2) for tv in template_vars):
                line = f"{m.group(1)}='{m.group(2)}'"
            # config.status over-escapes '$' to '\$' inside the *_spec
            # template assignments (libname_spec='lib\$name'); undo it so
            # libtool's runtime eval expands the variables.
            m2 = re.match(r"^([a-z_]+(_spec|_cmds)?)='(.*)'\s*$", line)
            if m2 and "\\$" in line:
                line = line.replace("\\$", "$")
            out.append(line)
        content = "\n".join(out)
        # ksh-style ECHO is not available under the OHOS /bin/sh
        content = content.replace('ECHO="print -r --"',
                                  'ECHO="printf %s\\n"')
        # archive_expsym_cmds: already-broken multi-line double-quoted
        # assignment (symvers disabled, variable never used) — neutralise
        broken = 'archive_expsym_cmds="echo "{ global:" > $output_objdir/$libname.ver~'
        if broken in content:
            idx = content.find(broken)
            end = content.find("\n\n", idx)
            content = content[:idx] + 'archive_expsym_cmds=""' + content[end:]
        save(self, lt, content)
        self.output.info("libtool quoting repaired (autoconf 2.72 + "
                         "ltmain.sh 2.4.6 compatibility)")

    def _fix_configure_umask(self):
        """Drop 'umask 077' from the configure script itself (E011).

        autoconf 2.72 emits `(umask 077 && mktemp -d ...)` at the top of
        configure and the config.status it generates; on HMDFS the 0700
        temp dir breaks subs1.awk creation (Permission denied). Patch the
        configure script in the source folder BEFORE running it, so the
        in-configure config.status run and the standalone one are both
        fixed (openfortivpn/cattle/opensp precedent).
        """
        cf = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cf):
            return
        content = load(self, cf)
        patched = content.replace(
            '(umask 077 && mktemp -d "./confXXXXXX")',
            '(mktemp -d "./confXXXXXX")',
        ).replace(
            '(umask 077 && mkdir "$tmp")',
            '(mkdir "$tmp" 2>/dev/null); chmod 755 "$tmp" 2>/dev/null',
        )
        if patched != content:
            save(self, cf, patched)
            self.output.info("configure umask patched for HMDFS")

    def _fix_config_status(self):
        """Drop 'umask 077' from config.status temp-dir creation.

        On HMDFS the 0700 temporary directory makes the subs1.awk creation
        fail with Permission denied (cattle/opensp/ncurses precedent).
        """
        cs = os.path.join(self.build_folder, "config.status")
        if not os.path.isfile(cs):
            return
        content = load(self, cs)
        patched = content.replace(
            '(umask 077 && mktemp -d "./confXXXXXX")',
            '(mktemp -d "./confXXXXXX")',
        ).replace(
            '(umask 077 && mkdir "$tmp")',
            '(mkdir "$tmp" 2>/dev/null); chmod 755 "$tmp" 2>/dev/null',
        )
        if patched != content:
            save(self, cs, patched)
            self.output.info("config.status umask patched for HMDFS")

    def _fix_dependency_la_paths(self):
        """Rewrite broken .la paths inside the ohpcd dependency packages.

        ohpcd binary packages were built with prefix=/, so their .la files
        carry libdir='//lib' and dependency_libs pointing at //lib or stale
        package folders; libtool aborts the final link with 'is not a
        valid libtool archive' (cattle-1.0 precedent, CI#16082). Rewrite
        libdir to the owning folder and re-point cross-package .la
        references to the folder conan actually installed for this graph.
        """
        seen = {}
        # Walk the FULL dependency graph (direct + transitive): libtool's
        # final link resolves cross-package .la references through
        # dependency_libs chains (e.g. gnutls.la -> libgpg-error.la), so a
        # stale '//lib/...' in ANY .la of the graph aborts the build on a
        # clean CI cache (local runs pass only because the local cache was
        # already rewritten by earlier attempts).
        deps = []
        frontier = list(self.dependencies.values())
        while frontier:
            d = frontier.pop(0)
            if d in deps:
                continue
            deps.append(d)
            try:
                frontier.extend(d.dependencies.values())
            except Exception:
                pass  # leaf/host packages expose no sub-graph
        # Pass 1: collect the full basename -> owning lib dir map for
        # the whole graph BEFORE rewriting anything, so cross-package
        # '//lib/<name>.la' references can be routed to the package that
        # actually ships <name>.la (the earlier single-pass rewrite
        # misrouted libgpg-error.la into libgcrypt's directory).
        la_owner = {}
        for dep in deps:
            lib_dir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(lib_dir):
                continue
            for la in glob.glob(os.path.join(lib_dir, "*.la")):
                la_owner.setdefault(os.path.basename(la), lib_dir)
        # Pass 2: rewrite
        for dep in deps:
            lib_dir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(lib_dir):
                continue
            for la in glob.glob(os.path.join(lib_dir, "*.la")):
                try:
                    content = load(self, la)
                except Exception as e:
                    self.output.warning(f"DEBUG-lafix: load FAILED {la}: {e}")
                    continue
                if content is None:
                    self.output.warning(f"DEBUG-lafix: load None {la}")
                    continue
                new = content.replace("libdir='//lib'",
                                      f"libdir='{lib_dir}'")

                def _route(mo):
                    # '//lib/<name>.la' -> owning package's dir
                    name = mo.group(1)
                    owner = la_owner.get(name)
                    return os.path.join(owner if owner else lib_dir, name)

                new = re.sub(r"//lib/([A-Za-z0-9_.+-]+\.la)", _route, new)
                # bare search dirs, any remaining context
                new = new.replace(" -L//lib", f" -L{lib_dir}")
                new = new.replace("-L//lib", f"-L{lib_dir}")
                new = new.replace("//lib", lib_dir)
                # forensics: after the rewrite nothing may survive
                m = re.search(r"^dependency_libs='(.*)'$", new, re.M)
                if m and "//lib" in m.group(1):
                    self.output.warn(
                        f"UNRESOLVED //lib in {os.path.basename(la)} "
                        f"after rewrite: {m.group(1)[:200]}")
                # musl: pthread is part of libc; the '-lpthread' that
                # libgpg-error's mtlibs leaves in dependency_libs makes
                # this project's old libtool resolve a bogus
                # '../.libs/libpthread.a' and abort the link.
                new = re.sub(r"(dependency_libs='[^']*)\s+-lpthread\b", r"\1",
                             new)
                # SAVE (this was lost in an earlier refactor — the
                # rewrite above computed `new` but never wrote it back!)
                if new != content:
                    try:
                        save(self, la, new)
                        self.output.info(
                            f"fixed .la paths: {la}")
                    except Exception as e:
                        self.output.warning(
                            f"cannot write .la {la}: {e}")

    def _purge_double_slash_lib_from_generated_files(self):
        """Rewrite any '//lib' leftovers in configure-generated files.

        Scans Makefile / libtool / *.la / *.pc under the build folder and
        replaces '//lib/...' (and '-L//lib') literals with the first real
        dependency lib dir of this graph, so the final link never
        references an unresolvable .la path on a clean CI cache.
        """
        # collect real lib dirs from the dependency graph
        lib_dirs = []
        frontier = list(self.dependencies.values())
        while frontier:
            d = frontier.pop(0)
            ld = os.path.join(d.package_folder, "lib")
            if os.path.isdir(ld) and ld not in lib_dirs:
                lib_dirs.append(ld)
            try:
                frontier.extend(d.dependencies.values())
            except Exception:
                pass
        self.output.info(f"DEBUG-privfix: lib_dirs={lib_dirs}")
        if not lib_dirs:
            self.output.warn("DEBUG-privfix: EMPTY lib_dirs, early return!")
            return
        # Definitive fix: conan re-extracts package archives between graph
        # resolutions (test_package round), so edits to dependency cache
        # .la files are silently reverted — CI keeps failing on the
        # pristine '//lib/...' inside e.g. libgcrypt.la. Copy every
        # dependency .la into a private build-folder dir, rewrite the
        # copies, and repoint the generated Makefiles at the copies.
        import shutil
        priv = os.path.join(self.build_folder, "ohpcd-la")
        os.makedirs(priv, exist_ok=True)
        # basename -> owning dir map (two-pass, same as cache fix)
        la_owner = {}
        for ld in lib_dirs:
            for la in glob.glob(os.path.join(ld, "*.la")):
                la_owner.setdefault(os.path.basename(la), ld)
        priv_map = {}
        for name, owner in la_owner.items():
            src_la = os.path.join(owner, name)
            try:
                content = load(self, src_la)
            except Exception:
                continue
            if content is None:
                continue
            new = content.replace("libdir='//lib'", f"libdir='{owner}'")
            new = new.replace(f"libdir='{owner}'",
                              f"libdir='{priv}'")  # live where we ship it
            # route cross-package '//lib/<name>.la' to the owning package
            def _route(mo):
                own = la_owner.get(mo.group(1))
                return os.path.join(own if own else priv, mo.group(1))
            new = re.sub(r"//lib/([A-Za-z0-9_.+-]+\.la)", _route, new)
            new = new.replace(" -L//lib", " -L" + priv)
            new = new.replace("-L//lib", "-L" + priv)
            # strip -lpthread (musl: pthread in libc)
            new = re.sub(r"(dependency_libs='[^']*)\s+-lpthread\b", r"\1", new)
            dst = os.path.join(priv, name)
            with open(dst, "w") as f:
                f.write(new)
            priv_map[os.path.join(owner, name)] = dst
        # repoint generated Makefiles: any dependency-cache .la reference
        # becomes the private copy; any leftover '//lib/<name>.la' is
        # routed through the owner map too
        def repoint(text):
            for orig, priv_la in priv_map.items():
                text = text.replace(orig, priv_la)
            def _route2(mo):
                own = la_owner.get(mo.group(1))
                return os.path.join(priv if not own else own, mo.group(1))
            text = re.sub(r"//lib/([A-Za-z0-9_.+-]+\.la)", _route2, text)
            text = text.replace("-L//lib", "-L" + priv)
            text = text.replace(" -L//lib", " -L" + priv)
            return text
        for name in ("Makefile", "libtool", "libtool-disable-static"):
            p = os.path.join(self.build_folder, name)
            if os.path.isfile(p):
                content = load(self, p)
                if content:
                    new = repoint(content)
                    if new != content:
                        save(self, p, new)
                        self.output.info(f"repoin .la refs in {name}")
        for sub in ("tests", "lib"):
            mk = os.path.join(self.build_folder, sub, "Makefile")
            if os.path.isfile(mk):
                content = load(self, mk)
                if content:
                    new = repoint(content)
                    if new != content:
                        save(self, mk, new)
                        self.output.info(f"repoin .la refs in {sub}/Makefile")

    def _strip_libpthread_from_makefile(self):
        """Drop '-lpthread' from the generated Makefiles' LIBS.

        AutotoolsDeps aggregates the dependency chain's system_libs into
        LIBS='... -lpthread' (from libgpg-error's conan recipe). OHOS
        musl has an (empty stub) libpthread.a in the sysroot — the
        compiler accepts the flag — but this project's old libtool
        resolves it against .la files and derives '../.libs/libpthread.a'
        which aborts the final link. Strip it from every generated
        Makefile (root + tests/) after configure (pthread symbols live
        in libc on musl).
        """
        for mk in glob.glob(os.path.join(self.build_folder, "**", "Makefile"),
                            recursive=True):
            try:
                content = load(self, mk)
            except Exception:
                continue
            patched = re.sub(r"(^LIBS\s*=.*?)(\s+-lpthread\b)", r"\1",
                             content, flags=re.M)
            if patched != content:
                save(self, mk, patched)
                self.output.info(f"stripped -lpthread from {mk}")

    def _run_upstream_tests(self):
        """Run the upstream tests that are runnable on OHOS.

        Upstream `make check` (tests/Makefile.am) registers 3 tests:
        - autocompletion: bash-completion script exercising the built
          openconnect binary's --help/--version parsing
        - lzstest: LZS decompressor unit test (C)
        - seqtest: ESP sequence replay test (C)
        All 3 pass on device when LD_LIBRARY_PATH carries the conan
        dependency libs. The remaining upstream tests live in
        tests/scripts (server-side ocserv interop, softhsm PKCS#11,
        dtls-psk...) and are not registered in check_PROGRAMS; they
        need a VPN server + softhsm2 + root netns — out of scope for
        the conan sandbox (documented in notes.md / MANIFEST.yml).
        """
        env_libs = []
        for dep in self.dependencies.values():
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                env_libs.append(lib_dir)
        ld_path = ":".join(env_libs)
        cwd = os.getcwd()
        os.environ["LD_LIBRARY_PATH"] = (
            ld_path + ":" + os.environ.get("LD_LIBRARY_PATH", "")
        ).rstrip(":")
        self.output.info(f"test LD_LIBRARY_PATH: {ld_path}")
        try:
            self.run("make check", cwd=self.build_folder)
        finally:
            pass

    def build(self):
        apply_conandata_patches(self)
        # cattle/opensp precedent: HMDFS-friendly umask for the whole build
        old_umask = os.umask(0o022)
        try:
            self._fix_dependency_la_paths()
            self._fix_configure_umask()
            autotools = Autotools(self)
            autotools.configure()
            self._fix_config_status()
            # configure's internal config.status run hits the HMDFS umask
            # issue — if Makefile is missing, re-run config.status directly
            if not os.path.isfile(os.path.join(self.build_folder, "Makefile")):
                self.run("bash config.status", cwd=self.build_folder)
            self._fix_libtool_quoting()
            self._strip_libpthread_from_makefile()
            # Final sweep: some ohpcd binary packages ship .la files with
            # '//lib/...' references that leak into the configure-generated
            # Makefile/libtool even after the dependency-cache fix above
            # (clean CI caches pull the pristine packages; local caches may
            # already be rewritten). Rewrite any remaining '//lib' literal
            # in the generated build artefacts to a real dependency lib dir
            # so libtool never sees an unresolvable .la path.
            self._purge_double_slash_lib_from_generated_files()
            # SECOND dependency-cache .la fix: conan re-extracts the
            # package archives (conan_package.tgz) between the configure
            # run above and make, silently reverting the first fix (the
            # pristine tgz ships libdir='//lib' and '//lib/libfoo.la'
            # cross references — verified by extracting conan_package.tgz
            # directly). Re-apply the cache fix NOW, immediately before
            # make, when no further conan step can revert it. libtool
            # resolves dependency .la paths at link time (CCLD), which
            # happens inside the make invocation that follows.
            self._fix_dependency_la_paths()
            # remove stale artefacts from any earlier broken run (a
            # damaged libname_spec materialises a literal 'lib$name.a')
            for junk in glob.glob(
                    os.path.join(self.build_folder, ".libs", "lib$*")):
                os.remove(junk)
            # -j1: OHOS sandbox lacks mkfifo (automake jobserver)
            autotools.make(args=["-j1"])
            self._run_upstream_tests()
        finally:
            os.umask(old_umask)

    def package(self):
        # DESTDIR staging (the autotools-native way): absolute dir args
        # are path-mangled unpredictably by this configure's cross mode
        # (observed: nested pkg/storage/... trees, build/bash/...), so
        # never trust `make install` prefix semantics. DESTDIR prepends
        # the staging root to EVERY install path — deterministic.
        import shutil
        staging = os.path.join(self.build_folder, "destroot")
        autotools = Autotools(self)
        autotools.install(args=[f"DESTDIR={staging}"])
        pkg = self.package_folder
        # the install tree under staging mirrors the absolute dirs:
        # <staging>/<each-abs-dir-without-leading-slash>/
        for root, dirs, files in os.walk(staging):
            for f in files:
                s = os.path.join(root, f)
                rel = os.path.relpath(s, staging)
                # rel looks like storage/.../p/bin/openconnect — find
                # the tail after the known layout markers
                for marker in ("/bin/", "/lib/", "/include/", "/share/",
                               "/sbin/", "/libexec/"):
                    idx = rel.find(marker)
                    if idx >= 0:
                        dst_rel = rel[idx + 1:]
                        dst = os.path.join(pkg, dst_rel)
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(s, dst)
                        break
        shutil.rmtree(staging, ignore_errors=True)
        # relocate sbin/libexec content to bin/ (conan convention)
        for sub in ("sbin", "libexec"):
            src_dir = os.path.join(pkg, sub)
            if os.path.isdir(src_dir):
                for name in os.listdir(src_dir):
                    copy(self, name, src=src_dir,
                         dst=os.path.join(pkg, "bin"))
                shutil.rmtree(src_dir, ignore_errors=True)
        # application package: drop stray library artefacts, keep
        # headers + pkgconfig for the libopenconnect API users
        for pat in ("lib.a", "libopenconnect.a", "*.la", "*.so*", "*.lai"):
            for f in glob.glob(os.path.join(pkg, "lib", pat)):
                os.remove(f)
        libdir = os.path.join(pkg, "lib")
        if os.path.isdir(libdir) and not os.listdir(libdir):
            shutil.rmtree(libdir, ignore_errors=True)
        share_doc = os.path.join(pkg, "share", "doc")
        if os.path.isdir(share_doc):
            shutil.rmtree(share_doc, ignore_errors=True)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        """Sign ELF executables for the OHOS XPM (openfortivpn precedent)."""
        if self.settings.os != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warn("Signing tools not found, skipping ELF signing")
            return
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        for name in sorted(os.listdir(bindir)):
            f = os.path.join(bindir, name)
            if not os.path.isfile(f) or os.path.islink(f):
                continue
            if not self._is_elf(f):
                continue
            try:
                self.run(f'{objcopy} --remove-section .codesign "{f}"')
            except Exception:
                pass
            self.run(
                f'{signer} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
            )

    def package_info(self):
        # Application package: executable in bin/; the libopenconnect API
        # headers are exposed via the global includedir for consumers that
        # link against the (upstream) library interface. Runtime .so
        # dependencies (gnutls/libxml2/zlib) are resolved by VirtualRunEnv
        # from the requirements graph automatically.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
