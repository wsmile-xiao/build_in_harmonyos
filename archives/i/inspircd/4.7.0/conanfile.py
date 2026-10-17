#!/usr/bin/env python3
"""Conan recipe — inspircd 4.7.0 (modular IRCv3 server daemon, C++17).

InspIRCd is a high-performance IRC server. The main product is the
`inspircd` server binary plus loadable `core_*.so`/`m_*.so` modules
(application package, R38), so no library packaging or shared/static
option is needed.

Build system: upstream perl `Configure` (requires perl >= 5.26, core
modules only) generating GNU makefiles, then `make` / `make install`.
Configure is non-interactive whenever any option is passed; this recipe
passes `--prefix=/ --disable-auto-extras --disable-ownership
--disable-interactive` and lets Configure probe the real toolchain:

- compiler: `$ENV{CXX}` from the conan build env (AutotoolsToolchain
  computes CC/CXX/CPPFLAGS/CXXFLAGS/LDFLAGS for the OHOS clang; the
  generated make/template/main.mk appends `$(CPPFLAGS) $(CXXFLAGS)` to
  CORECXXFLAGS and `$(LDFLAGS)` to CORELDFLAGS/PICLDFLAGS, so toolchain
  flags flow without hardcoding, R33).
- socket engine: first available probe (epoll via sys/epoll.h, kqueue,
  poll, select fallback); the choice is read back from
  .configure/cache.cfg and logged.
- extras: `--disable-auto-extras` disables all dependency-bearing extra
  modules (ssl_openssl/mysql/pgsql/sqlite3/ldap/pcre2/...), so the core
  server has zero external library requirements (fmt/http_parser/
  bcrypt/md5/sha2/utfcpp/lyra are all vendored). No TLS-module mandate
  applies in this mode (the mandate is only enforced when auto-extras
  are enabled).

OHOS/aarch64 notes (see notes.md):
- Upstream Configure is a fully in-source build and fatally aborts
  unless the tree is writable (`-w $RealDir`); the conan cache and even
  a fresh copy under the conan build folder keep failing `-w` on the
  HarmonyOS host (preflight 2026-09-27, two rounds), so build() syncs
  a fresh user-owned copy under the HMBS task TMPDIR area, proves
  real file creation with an open/write/unlink probe, and relaxes only
  the copy's `-w` fatal to a warning (source cache untouched).
- SYSTEM_NAME is `lc $^O` = "linux" under the OHOS perl, so the
  makefile takes the Linux branches (-pthread -ldl -lrt -rdynamic).
- `make install` honors DESTDIR; install lines are `-`-prefixed
  (failures ignored), so package() verifies bin/inspircd plus the
  auto-loaded core_*.so modules and refuses to ship an empty package.
- Upstream ships no automated tests (main.mk has no check/test target;
  make/test/ holds configure-time compiler probes; CI uses the external
  irctest pytest harness against a live server). build() therefore emits
  HMBS_UPSTREAM_TEST_RESULT with status "no_tests" (counts 0/0 + audit
  reason) and persists it to res/upstream_test_result.json so
  test_package can re-emit it on cache-hit rounds where build() output
  is skipped.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class InspircdConan(ConanFile):
    name = "inspircd"
    version = "4.7.0"
    description = "Modular high-performance Internet Relay Chat (IRCv3) server daemon"
    license = "GPL-2.0-only"
    homepage = "https://www.inspircd.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # NOTE: deliberately NO tool_requires("perl/..."). Conan perl 5.42.2
        # is unusable on the HarmonyOS build host: its PERL5LIB (5.42.2 lib)
        # leaks onto the system perl 5.42.0 executable, aborting with
        # "Perl lib version (5.42.2) doesn't match executable 'perl'
        # version (5.42.0)" (preflight 2026-09-27). Upstream Configure is a
        # perl program (`use v5.26.0`, core modules only), so the HNP
        # system perl (/data/service/hnp/bin/perl, 5.42.0) is sufficient
        # (mdocml/avimetaedit/burp2 precedent).
        pass

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "inspircd only supports Linux/OHOS, got %s" % self.settings.os)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Flag source only: conanbuild.sh exports CC/CXX/CPPFLAGS/
        # CXXFLAGS/LDFLAGS for the OHOS toolchain. Configure picks up
        # $ENV{CXX}; make picks up CPPFLAGS/CXXFLAGS/LDFLAGS via the
        # generated makefile. No configure_args: Configure is not
        # autoconf and is driven explicitly in build().
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _build_tree_base(self):
        """Task-writable base dir for the in-source build copy.

        HMBS injects a task-independent TMPDIR/TMP/TEMP (local_mktemp=1);
        the conan build folder itself lives under conan-home on HMDFS
        where perl `-w` keeps reporting "not writable" even for a fresh
        user-owned copy (preflight 2026-09-27, two rounds). TMPDIR is a
        different, proven-writable area, so the copy lives there now.
        """
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val:
                try:
                    os.makedirs(val, exist_ok=True)
                    return val
                except OSError:
                    continue
        return self.build_folder

    def _build_tree(self):
        """Writable copy of the source tree where Configure/make run.

        Upstream Configure is a fully in-source build: it fatally aborts
        (`print_error ... exit 1`) unless `-w $RealDir`, and writes
        .configure/cache.cfg, generated makefiles, probe binaries and all
        objects into the tree. Two preflight rounds proved that syncing
        the copy under the conan build folder does NOT clear the `-w`
        check on this host (same "not writable ... no" on the fresh
        copy), so this round uses the HMBS task TMPDIR area instead, and
        additionally relaxes the copy-only `configure` fatal after a
        real file-creation probe passes (see _relax_writable_check).
        """
        return os.path.join(self._build_tree_base(), "inspircd-src")

    def _tree_record(self):
        return os.path.join(self.build_folder, "inspircd_build_root.txt")

    @staticmethod
    def _copy_writable(src_file, dst_file):
        try:
            shutil.copy2(src_file, dst_file)
        except OSError:
            shutil.copyfile(src_file, dst_file)
        try:
            st = os.stat(dst_file)
            os.chmod(dst_file, st.st_mode | 0o200)
        except OSError:
            pass  # HMBS_CAP_CHMOD=0: chmod is a no-op, ignore

    def _ensure_writable_dirs(self, root):
        for cur, dirs, files in os.walk(root):
            for name in dirs:
                p = os.path.join(cur, name)
                try:
                    st = os.stat(p)
                    os.chmod(p, st.st_mode | 0o300)
                except OSError:
                    pass
        try:
            st = os.stat(root)
            os.chmod(root, st.st_mode | 0o300)
        except OSError:
            pass

    def _sync_build_tree(self):
        src = os.path.normpath(self.source_folder)
        dst = os.path.normpath(self._build_tree())
        if src == dst:
            raise ConanException(
                "inspircd build copy equals source folder (%s); "
                "refusing in-source build on the conan cache" % src)
        if os.path.isdir(dst):
            shutil.rmtree(dst, ignore_errors=False)
        os.makedirs(dst, mode=0o755, exist_ok=True)
        # TMPDIR lives outside the conan source tree, so no nested-copy
        # exclusion is needed (previous ENAMETOOLONG class is gone by
        # construction); every entry below is pure upstream source.
        for entry in sorted(os.listdir(src)):
            s = os.path.join(src, entry)
            d = os.path.join(dst, entry)
            try:
                if os.path.islink(s):
                    os.symlink(os.readlink(s), d)
                elif os.path.isdir(s):
                    shutil.copytree(s, d, symlinks=True,
                                    copy_function=self._copy_writable)
                else:
                    self._copy_writable(s, d)
            except OSError as exc:
                raise ConanException(
                    "inspircd: sync %s -> %s failed (%s)" % (s, d, exc))
        self._ensure_writable_dirs(dst)
        try:
            with open(self._tree_record(), "w", encoding="utf-8") as f:
                f.write(dst)
        except OSError:
            pass
        return dst

    def _resolve_build_tree(self):
        try:
            with open(self._tree_record(), "r", encoding="utf-8") as f:
                cand = f.read().strip()
            if cand and os.path.isfile(os.path.join(cand, "configure")):
                return cand
        except OSError:
            pass
        cand = os.path.normpath(self._build_tree())
        if os.path.isfile(os.path.join(cand, "configure")):
            return cand
        raise ConanException(
            "inspircd build tree missing (%s); build() must sync it first"
            % cand)

    def _prove_tree_writable(self, tree):
        access_ok = os.access(tree, os.W_OK)
        probe_ok = False
        detail = ""
        probe = os.path.join(tree, ".hmbs_write_probe")
        try:
            with open(probe, "w", encoding="utf-8") as f:
                f.write("writable\n")
            with open(probe, "r", encoding="utf-8") as f:
                probe_ok = (f.read() == "writable\n")
            detail = "create+read ok"
        except OSError as exc:
            detail = "probe failed: %s" % exc
            probe_ok = False
        finally:
            try:
                os.unlink(probe)
            except OSError:
                pass
        self.output.info(
            "inspircd writability: access=%s probe=%s (%s) tree=%s"
            % (access_ok, probe_ok, detail, tree))
        if not probe_ok:
            raise ConanException(
                "inspircd build tree not really writable (%s: %s); "
                "refusing to fake the upstream check" % (tree, detail))
        return access_ok, probe_ok

    def _relax_writable_check(self, tree):
        """Downgrade the copy-only fatal `-w` abort to a warning.

        Only the writable *copy's* `configure` is edited (the conan
        source cache is untouched). The fatal is scoped precisely to
        the "source directory is not writable" block; every other
        print_error stays fatal. This is honest: build() already
        proved real file creation works via _prove_tree_writable, so a
        remaining `-w` "no" is the known HMDFS access()-vs-open
        discrepancy (chmod=0/hardlink=0 host), not a real read-only
        tree. If the probe had failed we would have aborted above.
        """
        cfg = os.path.join(tree, "configure")
        try:
            with open(cfg, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as exc:
            raise ConanException(
                "inspircd: cannot read copy configure (%s)" % exc)
        marker = "the source directory is not writable"
        idx = content.find(marker)
        if idx < 0:
            self.output.warning(
                "inspircd: writable-check marker not found, skipping relax")
            return False
        perr = content.rfind("print_error", 0, idx)
        if perr < 0:
            self.output.warning(
                "inspircd: print_error not found before marker, skipping")
            return False
        content = (content[:perr] + "print_warning"
                   + content[perr + len("print_error"):])
        try:
            with open(cfg, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as exc:
            raise ConanException(
                "inspircd: cannot relax copy configure (%s)" % exc)
        self.output.info(
            "inspircd: relaxed copy-only -w fatal to warning (probe passed)")
        return True

    def _read_cache_setting(self, key):
        """Read one setting from .configure/cache.cfg (best effort)."""
        try:
            path = os.path.join(self._build_tree(), ".configure", "cache.cfg")
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    if k.strip() == key:
                        return v.strip().strip("'\"")
        except OSError as exc:
            self.output.warning("inspircd: cannot read cache.cfg (%s)" % exc)
        return None

    def _emit_upstream_marker(self):
        """Emit + persist the no_tests upstream marker (audit-backed)."""
        engine = self._read_cache_setting("SOCKETENGINE") or "unknown"
        self.output.info("inspircd: configured socket engine: %s" % engine)
        for probe in ("HAS_ARC4RANDOM_BUF", "HAS_CLOCK_GETTIME", "HAS_GETENTROPY"):
            self.output.info("inspircd: configure probe %s=%s"
                             % (probe, self._read_cache_setting(probe)))
        marker = {
            "status": "no_tests",
            "framework": "inspircd-configure",
            "command": "./configure --disable-auto-extras (no in-tree test target)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "inspircd 4.7.0 ships no automated tests: "
                "make/template/main.mk defines only all/clean/configureclean/"
                "debug/install/deinstall/distclean (no check/test target); "
                "make/test/*.cpp are configure-time compiler/socket probes, "
                "not registered tests; upstream CI quality gate is the "
                "external irctest pytest harness (.github/workflows/"
                "ci-irctest.yml) which needs a live server plus Anope/Atheme "
                "services and cannot run inside a conan build. Socket engine "
                "selected on device: %s." % engine
            ),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        try:
            persist = os.path.join(self.build_folder, "upstream_test_result.json")
            with open(persist, "w", encoding="utf-8") as f:
                json.dump(marker, f, indent=2)
        except OSError as exc:
            self.output.warning("inspircd: cannot persist upstream marker (%s)" % exc)
        return marker

    def build(self):
        # Do NOT force INSPIRCD_VERBOSE=1: verbose echoes the full clang++
        # command per translation unit (~200 core+module compiles), which
        # bloats the preflight log past 200KB and coincides with the
        # 2026-09-27 "Connection closed by remote host" mid-build drop.
        # Upstream default (unset) prints short "BUILD: foo.cpp" lines via
        # --silent with identical artifacts; keep it unset for transport
        # stability.
        os.environ.pop("INSPIRCD_VERBOSE", None)
        try:
            jobs = int(self.conf.get("tools.build:jobs", default=1) or 1)
        except (ValueError, TypeError):
            jobs = 1
        jobs = max(1, jobs)
        # Use the HNP system perl explicitly and drop any stale PERL5LIB
        # pointing at the (removed) conan perl 5.42.2 lib tree; otherwise
        # `perl` aborts with the 5.42.2-vs-5.42.0 version mismatch above.
        perl = "/data/service/hnp/bin/perl"
        if not os.path.isfile(perl):
            perl = "perl"
        configure_cmd = (
            "unset PERL5LIB; export PERL=%s; "
            "%s configure --prefix=/ --disable-auto-extras "
            "--disable-ownership --disable-interactive" % (perl, perl)
        )
        self.output.info("inspircd configure: %s" % configure_cmd)
        tree = self._sync_build_tree()
        self.output.info("inspircd build tree: %s" % tree)
        self._prove_tree_writable(tree)
        self._relax_writable_check(tree)
        self.run(configure_cmd, cwd=tree, env="conanbuild")
        self.run("make -j%d" % jobs, cwd=tree, env="conanbuild")
        self._emit_upstream_marker()

    def _ensure_package_dir(self, path):
        """mkdir -p that survives a file/symlink collision at `path`.

        `make install` rules are `-`-prefixed (failures ignored) and the
        HMBS install shim fails them with Error 64 on this host, so the
        package tree can be left with a plain file (or broken symlink)
        where `bin/`/`modules/` should be. Plain
        `os.makedirs(path, exist_ok=True)` then raises FileExistsError
        (exist_ok only suppresses existing *directories*), which is the
       exact preflight failure at package() line 403. If the path is
        already a directory this is a no-op; otherwise the stray file
        entry is unlinked first and the directory is created.
        """
        if os.path.isdir(path):
            return
        if os.path.lexists(path):
            try:
                kind = ("symlink" if os.path.islink(path)
                        else "file" if os.path.isfile(path) else "other")
            except OSError:
                kind = "unknown"
            self.output.warning(
                "inspircd: package path %s exists as %s; "
                "replacing with directory" % (path, kind))
            try:
                if os.path.islink(path) or os.path.isfile(path):
                    os.unlink(path)
                else:
                    shutil.rmtree(path, ignore_errors=True)
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
            except OSError as exc:
                raise ConanException(
                    "inspircd: cannot clear stray %s at %s (%s)"
                    % (kind, path, exc))
        try:
            os.makedirs(path, exist_ok=True)
        except FileExistsError:
            if os.path.isdir(path):
                return
            raise
        if not os.path.isdir(path):
            raise ConanException(
                "inspircd: failed to create package dir %s" % path)

    def package(self):
        import glob as _glob
        tree = self._resolve_build_tree()
        destdir = self.package_folder.replace("\\", "/")
        self.run('make DESTDIR="%s" install' % destdir,
                 cwd=tree, env="conanbuild")
        bindir = os.path.join(self.package_folder, "bin")
        binary = os.path.join(bindir, "inspircd")
        if not (os.path.isfile(binary) and os.path.getsize(binary) > 0):
            # `make install` lines are `-`-prefixed (failures ignored) and
            # the HMBS install shim fails them with Error 64 on this host,
            # so an "INSTALL COMPLETE" exit 0 can still leave an empty
            # package. Fall back to copying the built artifacts directly
            # out of BUILDPATH (build/<Compiler>-<Ver>/bin|modules), the
            # idsgrep/yydecode precedent anticipated in notes.md.
            self.output.warning(
                "inspircd: make install left no bin/inspircd; "
                "falling back to manual copy from BUILDPATH")
            cands = sorted(_glob.glob(
                os.path.join(tree, "build", "*", "bin", "inspircd")))
            if not cands:
                raise ConanException(
                    "inspircd binary missing after make install (%s) and "
                    "no build/*/bin/inspircd candidate under %s; refusing "
                    "to ship an empty package" % (binary, tree))
            built_bin = cands[0]
            self.output.info("inspircd: manual copy %s -> %s"
                             % (built_bin, binary))
            self._ensure_package_dir(bindir)
            self._copy_writable(built_bin, binary)
            moddir = os.path.join(self.package_folder, "modules")
            self._ensure_package_dir(moddir)
            mod_cands = sorted(_glob.glob(
                os.path.join(tree, "build", "*", "modules", "*.so")))
            for m in mod_cands:
                self._copy_writable(
                    m, os.path.join(moddir, os.path.basename(m)))
            if not (os.path.isfile(binary) and os.path.getsize(binary) > 0):
                raise ConanException(
                    "inspircd manual copy failed (%s); refusing to ship "
                    "an empty package" % binary)
        moddir = os.path.join(self.package_folder, "modules")
        core_mods = []
        if os.path.isdir(moddir):
            core_mods = sorted(f for f in os.listdir(moddir)
                               if f.startswith("core_") and f.endswith(".so"))
        self.output.info("inspircd: packaged core modules: %d (%s)"
                         % (len(core_mods), ", ".join(core_mods[:8])))
        if not core_mods:
            raise ConanException(
                "no core_*.so modules under %s; the server auto-loads "
                "core modules from the module dir at startup, refusing "
                "to ship a package that cannot start" % moddir)
        copy(self, "LICENSE.txt", src=os.path.join(tree, "docs"),
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "upstream_test_result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
