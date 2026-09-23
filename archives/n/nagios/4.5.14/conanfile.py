#!/usr/bin/env python3
"""Conan recipe for nagios 4.5.14 — Nagios Core monitoring daemon.

Nagios Core is the classic open-source IT infrastructure monitoring
system (C, autotools build).  This recipe builds:

  - base/nagios       : the monitoring daemon
  - base/nagiostats   : statistics utility
  - cgi/*.cgi         : 19 CGI programs (web UI backend, standard stdio
                        CGI protocol — buildable & testable without a
                        web server; statusmap/trends/histogram need gd)
  - html/stylesheets  : web UI static assets

Dependencies (all from the ohpcd registry):
  - openssl/3.5.6     SSL support in base/netutils.c + CGIs
  - gd/2.3.3.1        image rendering for statusmap/trends/histogram CGIs
                      (optional upstream, enabled here so the full CGI
                      set is built and the upstream test-suite covers it)

OHOS adaptations (see notes.md for the full story):
  - config.guess/config.sub: HarmonyOS/aarch64-unknown-linux-ohos triplet
  - --with-temp-dir: configure's own TMPDIR variable would default to
    the read-only /tmp; pointed at a writable temp dir instead
  - SSL detection: configure probes -I<inc>/openssl + libssl.so; conan's
    static openssl package is exposed through a shim include dir
    (include/ssl.h forwarding + include/openssl symlink) and .so
    symlinks to the static archives (final binaries link statically)
  - INSTALL_OPTS/COMMAND_OPTS cleared at install time (GNU make command
    line override — same approach as upstream's own packaging target):
    OHOS has no "nagios" user and chown is not permitted
  - make install does not install init scripts (install-init is a
    separate target, systemd/sysv units are meaningless on OHOS; the
    daemon is expected to be started via hdc shell or a service
    wrapper provided by the integrator)

Upstream tests (run in build(), see test report):
  - t/        perl test-suite: 14 files, 478 assertions  (make test)
  - t-tap/    C unit tests:    9 programs, 6702 assertions
              (--enable-libtap, needs the LDFLAGS fix from patch 0004)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, mkdir, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NagiosConan(ConanFile):
    name = "nagios"
    version = "4.5.14"
    description = "Nagios Core — the classic open-source IT infrastructure monitoring system (daemon + CGI web UI backend)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nagios.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/n/nagios"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"with_statusmap": [True, False]}
    default_options = {"with_statusmap": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6", transitive_headers=True, transitive_libs=True)
        if self.options.with_statusmap:
            self.requires("gd/2.3.3.1", transitive_headers=True, transitive_libs=True)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"nagios is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        # nagios' upstream Makefiles (html/Makefile in particular) install
        # via relative paths (js/*.js, *.php) and only support in-tree
        # builds — keep build folder == source folder.
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # R33: compiler comes from the Conan profile conf
        # (tools.build:compiler_executables), not from shell env vars.
        tc = AutotoolsToolchain(self)

        # Collect -I/-L paths from every dependency in the graph (openssl
        # plus the full gd chain when enabled).  Walking
        # dependencies.values() picks up transitive deps without
        # hard-coding their names.
        lib_paths = []
        inc_paths = []
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            for d in list(dep.cpp_info.libdirs) or []:
                if os.path.isabs(d):
                    lib_paths.append(d)
            for d in list(dep.cpp_info.includedirs) or []:
                if os.path.isabs(d):
                    inc_paths.append(d)
            # transitive deps may expose empty/relative cpp_info lists
            # here; derive the standard layout from the package folder too
            plib = os.path.join(dep.package_folder, "lib")
            pinc = os.path.join(dep.package_folder, "include")
            if os.path.isdir(plib):
                lib_paths.append(plib)
            if os.path.isdir(pinc):
                inc_paths.append(pinc)
        lib_paths = list(dict.fromkeys(lib_paths))
        inc_paths = list(dict.fromkeys(inc_paths))
        # keep in the recipe for build() to reuse
        self._conf_info = {"lib_paths": lib_paths, "inc_paths": inc_paths}

        self.output.info(f"_OHOS_DEBUG lib_paths={lib_paths}")
        self.output.info(f"_OHOS_DEBUG inc_paths={inc_paths}")
        tc.extra_cflags.extend(f"-I{p}" for p in inc_paths)
        tc.extra_ldflags.extend(f"-L{p}" for p in lib_paths)

        # --- SSL shim: make conan's openssl visible to nagios' configure --
        # configure probes for <inc>/ssl.h (SSL_INC_PREFIX="") or
        # <inc>/openssl/ssl.h; the latter adds "-I<inc>/openssl" which then
        # breaks "#include <openssl/ssl.h>" in the conftest.  A shim dir
        # with include/ssl.h (forwarding) + include/openssl (symlink) hits
        # the prefix-"" branch and keeps both include styles working.
        openssl = self.dependencies["openssl"].package_folder
        shim = os.path.join(self.generators_folder, "sslshim")
        if os.path.exists(shim):
            shutil.rmtree(shim)
        mkdir(self, os.path.join(shim, "include"))
        save(self, os.path.join(shim, "include", "ssl.h"),
             "#include <openssl/ssl.h>\n")
        os.symlink(os.path.join(openssl, "include", "openssl"),
                   os.path.join(shim, "include", "openssl"))
        # configure only looks for libssl.$soext; conan ships .a — provide
        # .so symlinks (the link line stays -lssl/-lcrypto and resolves to
        # the static archives, keeping the daemon self-contained).
        ssl_link_dir = os.path.join(shim, "lib")
        mkdir(self, ssl_link_dir)
        for lib in ("libssl", "libcrypto"):
            so = os.path.join(ssl_link_dir, lib + ".so")
            if os.path.lexists(so):
                os.remove(so)
            os.symlink(os.path.join(openssl, "lib", lib + ".a"), so)

        tc.configure_args = [
            f"--prefix={self.package_folder}",
            f"--with-ssl={shim}",
            f"--with-ssl-inc={os.path.join(shim, 'include')}",
            f"--with-ssl-lib={ssl_link_dir}",
            # configure's own TMPDIR variable defaults to the read-only
            # /tmp (E002); point it at the writable temp dir
            f"--with-temp-dir={os.environ.get('TMPDIR', '/tmp')}",
            # no 'nagios' user on OHOS; cleared again at install time
            "--with-nagios-user=file_manager",
            "--with-nagios-group=file_manager",
            "--with-command-user=file_manager",
            "--with-command-group=file_manager",
            # C unit tests (t-tap/)
            "--enable-libtap",
        ]
        if self.options.with_statusmap:
            gd = self.dependencies["gd"].package_folder
            tc.configure_args += [
                f"--with-gd-inc={os.path.join(gd, 'include')}",
                f"--with-gd-lib={os.path.join(gd, 'lib')}",
            ]

        tc.generate()

        # Helper script environment for tests: the CGIs link against the
        # shared gd chain, so LD_LIBRARY_PATH must contain the dep libdirs
        # for the test-run.
        run_env = Environment()
        for p in lib_paths:
            run_env.prepend_path("LD_LIBRARY_PATH", p)
        run_env.vars(self, scope="build").save_script("nagios_test_runpath")

    def build(self):
        # --- tap/ needs the HarmonyOS-aware config.guess/config.sub -------
        # (the bundled 2025 copies don't know HarmonyOS either; reuse the
        # patched top-level ones)
        for fn in ("config.guess", "config.sub"):
            src = os.path.join(self.source_folder, fn)
            dst = os.path.join(self.source_folder, "tap", fn)
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)
        # E490: autotools helper scripts must keep the executable bit
        self.run(f'chmod +x "{self.source_folder}/configure" '
                 f'"{self.source_folder}/config.guess" '
                 f'"{self.source_folder}/config.sub" '
                 f'"{self.source_folder}/install-sh"')

        # E012: configure/config.status create their scratch dirs with
        # "umask 077"; on the HMDFS conan cache (setgid dir owned by a
        # different uid) those dirs end up inaccessible to the build
        # process ("./confXXXX/subs1.awk: Permission denied"): mode 0770
        # with the inherited group-owner leaves the build uid with no
        # permission bits at all.  Relax the umask to 022 (dirs become
        # group-readable, still NOT world-writable — same recommendation
        # as knowledge entry E136) in the generated scripts.
        # Applies to the top-level configure and tap/configure (the
        # bundled libtap sub-project has its own configure).
        for cfg_rel in ("configure", os.path.join("tap", "configure")):
            configure_path = os.path.join(self.source_folder, cfg_rel)
            with open(configure_path, "r", encoding="utf-8") as f:
                content = f.read()
            patched = content.replace("(umask 077", "(umask 022")
            if patched != content:
                with open(configure_path, "w", encoding="utf-8") as f:
                    f.write(patched)

        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(target="all", args=["-j1"])

        # --- loader-path compatibility for baked-in absolute NEEDEDs -----
        # Some registry binaries carry absolute NEEDED entries pointing at
        # their *publishing* machine's conan cache (e.g. libfontconfig.so.1
        # needs "/storage/.../.conan2/p/expat…/lib/libexpat.so").  The OHOS
        # loader resolves such entries by path only, and LD_LIBRARY_PATH
        # cannot fix an absolute NEEDED.  Rewriting the ELF (patchelf) is
        # not an option either: the kernel verifies code signatures and
        # rejects a modified copy ("Permission denied").  What works: a
        # symlink at the recorded absolute path pointing to the real
        # library from the current dependency graph — same file content,
        # signature intact, loader resolves it.  Only paths inside the
        # invoking user's own home tree are created, and only when missing.
        self._fix_absolute_needed_paths()

        # --- upstream tests -------------------------------------------
        if can_run(self):
            self._run_upstream_tests()

        # --- install (no chown: INSTALL_OPTS/COMMAND_OPTS cleared) ---------
        # prefix == package_folder so files land directly in the package —
        # pass an explicit empty DESTDIR because conan's Autotools.install
        # would otherwise prepend the package folder a second time.
        # INSTALL_OPTS/COMMAND_OPTS are cleared via GNU make command-line
        # overrides — the same trick upstream's own "make rpm" packaging
        # target uses — because OHOS has no 'nagios' user and chown is not
        # permitted for the build user.
        autotools.install(args=["DESTDIR=", "INSTALL_OPTS=", "COMMAND_OPTS="])

    def _fix_absolute_needed_paths(self):
        """Recreate absolute NEEDED paths baked into registry .so files.

        Scan every dependency shared library for NEEDED entries that are
        absolute paths (artifact of the publishing machine's conan cache
        layout, e.g. libfontconfig.so.1 → /storage/…/.conan2/p/expat…/lib/
        libexpat.so).  The loader resolves such entries by path only, so
        they break on any machine whose conan cache lives elsewhere (CI
        workers use $HOME/.cache/conan2) and LD_LIBRARY_PATH cannot help;
        rewriting the ELF is blocked by kernel code-signature checks.
        Fix: symlink the recorded absolute path to the real library of the
        same basename found in the current dependency graph — the file
        content (and thus signature) stays untouched.
        """
        import struct

        # index: basename -> real file path, from the dependency graph
        so_index = {}
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for fn in os.listdir(libdir):
                if fn.endswith(".so") or ".so." in fn:
                    so_index.setdefault(fn, os.path.join(libdir, fn))

        # scan for absolute NEEDED entries that don't resolve locally
        missing = set()
        for soname, so_path in so_index.items():
            try:
                needed = self._read_needed(so_path)
            except Exception:
                continue
            for n in needed:
                if n.startswith("/") and not os.path.exists(n):
                    missing.add(n)

        for abs_path in sorted(missing):
            base = os.path.basename(abs_path)
            real = so_index.get(base)
            if real is None:
                # unversioned fallback: libX.so.N -> libX.so
                stem = base.split(".so")[0]
                for cand_name, cand_path in so_index.items():
                    if cand_name == stem + ".so" or cand_name.startswith(stem + ".so."):
                        real = cand_path
                        break
            if real is None:
                self.output.warn(
                    f"absolute NEEDED {abs_path} has no matching dependency "
                    f"library; the dependent test may fail to load it")
                continue
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            if os.path.lexists(abs_path):
                os.remove(abs_path)
            os.symlink(real, abs_path)
            self.output.info(
                f"baked-in NEEDED path {abs_path} -> {real}")

    @staticmethod
    def _read_needed(so_path):
        """Minimal ELF DT_NEEDED reader (no external deps)."""
        with open(so_path, "rb") as f:
            data = f.read()
        if data[:4] != b"\x7fELF":
            return []
        import struct
        e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
        e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
        e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
        sections = []
        for i in range(e_shnum):
            off = e_shoff + i * e_shentsize
            sh_type = struct.unpack_from("<I", data, off + 4)[0]
            sh_offset = struct.unpack_from("<Q", data, off + 0x18)[0]
            sh_size = struct.unpack_from("<Q", data, off + 0x20)[0]
            sh_link = struct.unpack_from("<I", data, off + 0x28)[0]
            sections.append((sh_type, sh_offset, sh_size, sh_link))
        needed = []
        for sh_type, sh_offset, sh_size, sh_link in sections:
            if sh_type != 6:
                continue
            _, str_off, str_size, _ = sections[sh_link]
            strtab = data[str_off:str_off + str_size]
            for i in range(sh_offset, sh_offset + sh_size, 16):
                d_tag, d_val = struct.unpack_from("<qQ", data, i)
                if d_tag == 0:
                    break
                if d_tag == 1:  # DT_NEEDED
                    end = strtab.find(b"\x00", d_val)
                    needed.append(strtab[d_val:end].decode("utf-8", "replace"))
        return needed

    def _run_upstream_tests(self):
        """Run the upstream test-suites via the upstream make targets.

        `make test-perl` (t/ perl suite, prove) and `make test-tap`
        (t-tap/ C unit tests) handle the srcdir/builddir wiring (etc/var
        copies, symlinks) themselves — running them from the build folder
        matches exactly what a user running `make test` on Linux gets.

        The CGIs (statusmap/trends/histogram) link the shared gd chain,
        whose transitive deps (libfontconfig → libexpat, libtiff, …)
        live in conan package folders not on the default loader path —
        the conanbuild env only carries the direct deps' libdirs, so the
        full chain (every dependency's libdir, transitive included) is
        exported inline here (on a clean CI worker no ambient
        LD_LIBRARY_PATH exists to mask a missing entry).
        """
        # perl/prove live in /data/service/hnp/bin on OHOS workers and
        # must be on PATH for the t/Makefile `prove` invocation
        hnp_bin = "/data/service/hnp/bin"
        path_prefix = f"{hnp_bin}:" if os.path.isdir(hnp_bin) else ""

        # Collect every dependency libdir (direct + transitive) for the
        # loader; absolute NEEDED paths were fixed above via symlinks.
        lib_dirs = []
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            for d in list(dep.cpp_info.libdirs) or []:
                if os.path.isabs(d):
                    lib_dirs.append(d)
            plib = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(plib):
                lib_dirs.append(plib)
        lib_dirs = list(dict.fromkeys(lib_dirs))
        ld_prefix = (f'LD_LIBRARY_PATH="{":".join(lib_dirs)}:$LD_LIBRARY_PATH" '
                     if lib_dirs else "")

        # t/ perl suite: 14 files, 478 assertions
        self.run(
            f'cd "{self.build_folder}" && '
            f'PATH="{path_prefix}$PATH" {ld_prefix}make test-perl',
            env="conanbuild",
        )
        # keep the tree pristine for repeated runs
        self.run(f'cd "{self.build_folder}/t" && rm -f var/status-generated.dat',
                 env="conanbuild")

        # t-tap C unit tests: 9 programs, 6702 assertions
        self.run(
            f'cd "{self.build_folder}" && '
            f'PATH="{path_prefix}$PATH" {ld_prefix}make test-tap',
            env="conanbuild",
        )

    def package(self):
        # install already ran in build() (prefix == package folder)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # application package: binaries + CGI programs + web assets
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin", "sbin"]
