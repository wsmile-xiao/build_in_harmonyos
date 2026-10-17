#!/usr/bin/env python3
"""Conan recipe — gpgme 1.24.2 (GPGME, autotools) on HarmonyOS PC (aarch64).

GPGME is a library providing easy access to GnuPG cryptographic operations.

OHOS-specific adaptations:
  1. E007 — config.guess/config.sub patched to recognize `linux-ohos`
     (patches/0001, 0002). Native build, no --build/--host.
  2. E011 — configure umask 077 -> 022 for HMDFS temp dirs (patches/0003).
  3. E027 — --disable-nls: published libgpg-error/1.55 is built --disable-nls,
     so we do the same (no libintl/gettext dependency required).
  4. gpgrt-config shell compatibility: build-local wrappers invoke the SDK's
     supported bash instead of the device's /bin/sh (mksh).
  5. E012 — libgpg-error/libassuan .pc/.la from the conan packages use
     prefix=/ (wrong absolute paths). config-overrides provides corrected
     gpg-error.pc + libassuan-config wrapper + corrected .la files, and the
     build-local la dir is prepended to LDFLAGS so libtool resolves the
     dependency .la files correctly.
  6. make -j1 (E074: OHOS SELinux forbids FIFO jobserver).
  7. Upstream make check uses the published gnupg/2.5.22 build tool to supply
     gpg/gpgsm and their runtime; the Conan tool requirement is test-only.
  8. Upstream test bootstrap: each suite's GNUPGHOME is its own build dir, so it
     gets mode 0700 and a pre-started gpg-agent before make imports the demo
     keys during BUILT_SOURCES. The packaged gnupg resolves its helpers through
     an absolute install prefix that HarmonyOS keeps read-only, so gpg cannot
     autospawn gpg-agent itself.
  9. A build-local gpgconf shim rewrites the "//" install prefix that the
     relocatable gnupg package reports, because GPGME resolves gpg/gpgsm from
     "gpgconf --list-components". See _run_upstream_test_suites for the suite
     that is left out and why. A suite's build dir is also its GNUPGHOME, so
     that directory must accept an AF_UNIX bind. The HMDFS mount behind
     /storage (Conan's default cache) returns EPERM; build() copies the
     in-tree work tree onto the first probed directory that accepts the bind
     and configures there. CI does not relocate CONAN_HOME. On the CI worker
     the parents of that directory are searchable but not readable, so a shell
     started already inside it loses getcwd() and libtool records
     `(cd ; $SHELL /libtool ...)`. Commands cd there from the Conan build
     folder and export PWD; libtool's pwd falls back to that value.
"""
import os
import shutil
import shlex
import subprocess

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GpgmeConan(ConanFile):
    name = "gpgme"
    version = "1.24.2"
    description = "Library providing easy access to GnuPG for cryptographic operations"
    license = "LGPL-2.1-or-later"
    homepage = "https://gnupg.org/software/gpgme/"
    url = "https://git.gnupg.org/cgi-bin/gitweb.cgi?p=gpgme.git"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires(
            "libgpg-error/1.55",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libassuan/3.0.2",
            transitive_headers=True,
            transitive_libs=True,
        )

    def build_requirements(self):
        # GPGME's enabled upstream tests exercise the GnuPG/GPGSM backends.
        # gnupg is a build-time test runner, not a runtime dependency of GPGME.
        self.tool_requires("gnupg/2.5.22")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # config-overrides: correct the dependency config scripts / .la files #
    # ------------------------------------------------------------------ #
    def _co_dir(self):
        return os.path.join(self.build_folder, "config-overrides")

    def _create_config_overrides(self):
        lgp = self.dependencies["libgpg-error"].package_folder
        las = self.dependencies["libassuan"].package_folder
        qt = self.dependencies["qtbase"].package_folder
        co = self._co_dir()
        for d in ("bin", "lib/pkgconfig"):
            os.makedirs(os.path.join(co, d), exist_ok=True)

        # The worker may expose bash from different SDK prefixes. Resolve it
        # from the active PATH so generated wrappers use the executable that
        # is actually available in this build environment.
        bash = shutil.which("bash") or "/data/service/hnp/bin/bash"

        # 1) gpgrt-config wrapper: force bash (OHOS /bin/sh = mksh hangs).
        with open(os.path.join(co, "bin", "gpgrt-config"), "w") as f:
            f.write(
                "#!/bin/sh\n"
                f"exec {bash} {shlex.quote(os.path.join(lgp, 'bin', 'gpgrt-config'))} \"$@\"\n"
            )
        os.chmod(os.path.join(co, "bin", "gpgrt-config"), 0o755)

        # gpg-error-config has the same obsolete interpreter in its shebang.
        # Execute it through the supported bash and let it find our gpgrt shim.
        with open(os.path.join(co, "bin", "gpg-error-config"), "w") as f:
            f.write(
                "#!/bin/sh\n"
                f"exec {bash} {shlex.quote(os.path.join(lgp, 'bin', 'gpg-error-config'))} \"$@\"\n"
            )
        os.chmod(os.path.join(co, "bin", "gpg-error-config"), 0o755)

        # 2) libassuan-config wrapper: return correct flags (package .pc uses prefix=/).
        with open(os.path.join(co, "bin", "libassuan-config"), "w") as f:
            f.write(
                "#!/bin/sh\n"
                'case "$1" in\n'
                "  --version) echo 3.0.2 ;;\n"
                "  --api-version) echo 3 ;;\n"
                "  --host) echo aarch64-unknown-linux-ohos ;;\n"
                f"  --cflags) echo -I{os.path.join(las, 'include')} ;;\n"
                f"  --libs) echo -L{os.path.join(las, 'lib')} -lassuan "
                f"-L{os.path.join(lgp, 'lib')} -lgpg-error ;;\n"
                "  *) echo 3.0.2 ;;\n"
                "esac\n"
            )
        os.chmod(os.path.join(co, "bin", "libassuan-config"), 0o755)

        # 3) corrected gpg-error.pc (package .pc uses prefix=/ -> /lib, /include).
        pc_src = os.path.join(lgp, "lib", "pkgconfig", "gpg-error.pc")
        pc_dst = os.path.join(co, "lib", "pkgconfig", "gpg-error.pc")
        with open(pc_src, "r", encoding="utf-8") as f:
            text = f.read()
        text = text.replace("prefix=/", "prefix={}".format(lgp), 1)
        with open(pc_dst, "w", encoding="utf-8") as f:
            f.write(text)

        # 4) corrected .la files so libtool resolves dependency paths correctly.
        with open(os.path.join(co, "lib", "libgpg-error.la"), "w") as f:
            f.write(
                "# libgpg-error.la - a libtool library file\n"
                "# Generated by libtool (GNU libtool) 2.4.7\n"
                "# Fixed for OHOS: correct libdir/dependency_libs to conan package paths.\n"
                "dlname='libgpg-error.so.0'\n"
                "library_names='libgpg-error.so.0.39.3 libgpg-error.so.0 libgpg-error.so'\n"
                "old_library=''\n"
                "inherited_linker_flags=''\n"
                "dependency_libs=''\n"
                "weak_library_names=''\n"
                "current=39\nage=39\nrevision=3\n"
                "installed=yes\nshouldnotlink=no\n"
                "dlopen=''\ndlpreopen=''\n"
                "libdir='{}/lib'\n".format(lgp)
            )
        with open(os.path.join(co, "lib", "libassuan.la"), "w") as f:
            f.write(
                "# libassuan.la - a libtool library file\n"
                "# Generated by libtool (GNU libtool) 2.4.2\n"
                "# Fixed for OHOS: correct libdir/dependency_libs to conan package paths.\n"
                "dlname='libassuan.so.9'\n"
                "library_names='libassuan.so.9.0.2 libassuan.so.9 libassuan.so'\n"
                "old_library=''\n"
                "inherited_linker_flags=''\n"
                "dependency_libs=' -L{}/lib -lgpg-error -lpthread'\n".format(lgp) +
                "weak_library_names=''\n"
                "current=9\nage=0\nrevision=2\n"
                "installed=yes\nshouldnotlink=no\n"
                "dlopen=''\ndlpreopen=''\n"
                "libdir='{}/lib'\n".format(las)
            )

        # 6) gpgconf wrapper: GPGME resolves its crypto engines through
        # "gpgconf --list-components" / "--list-dirs". The relocatable gnupg
        # package is installed with --prefix=/, so those listings report paths
        # such as "//bin/gpg" and GPGME would look for an engine in the
        # device's read-only /bin. Rewrite the compiled-in prefix to the real
        # package directory so the engines resolve to files that exist.
        gnupg = self.dependencies.build["gnupg"].package_folder
        shim = os.path.join(co, "bin", "gpgconf")
        with open(shim, "w") as f:
            f.write(
                "#!/bin/sh\n"
                "tmp='{}'\n"
                "'{}/bin/gpgconf' \"$@\" >\"$tmp\"; rc=$?\n"
                "sed 's|://|:{}/|g' \"$tmp\"\n"
                "exit $rc\n".format(
                    os.path.join(co, "gpgconf.listing"), gnupg, gnupg
                )
            )
        os.chmod(shim, 0o755)
        return co

    def _build_env(self, co):
        """Environment for configure/make/install runs (applied on top of the
        default process env; conanbuild env is NOT applied)."""
        lgp = self.dependencies["libgpg-error"].package_folder
        las = self.dependencies["libassuan"].package_folder
        qt = self.dependencies["qtbase"].package_folder
        gnupg = self.dependencies.build["gnupg"].package_folder
        env = Environment()
        env.define("CONFIG_SHELL", shutil.which("bash") or "/data/service/hnp/bin/bash")
        # A device-side getcwd() simulation sets this. Keep it across the
        # conanbuild environment so install sees the same failure mode as CI.
        if os.environ.get("LD_PRELOAD"):
            env.define("LD_PRELOAD", os.environ["LD_PRELOAD"])
        env.define("TMPDIR", self.build_folder)
        # configure probes for gpg/gpgsm to decide whether to register the
        # upstream integration suites. Their binaries are build-only tools.
        # The config-overrides bin dir is prepended last so its gpgconf shim
        # shadows the packaged one; every other tool still comes from gnupg.
        env.prepend_path("PATH", os.path.join(gnupg, "bin"))
        env.prepend_path("PATH", os.path.join(co, "bin"))
        qt_pc = os.path.join(co, "qt-pkgconfig")
        os.makedirs(qt_pc, exist_ok=True)
        for filename in os.listdir(os.path.join(qt, "lib", "pkgconfig")):
            if filename.endswith(".pc"):
                source = os.path.join(qt, "lib", "pkgconfig", filename)
                with open(source, "r", encoding="utf-8") as stream:
                    lines = stream.readlines()
                with open(os.path.join(qt_pc, filename), "w", encoding="utf-8") as stream:
                    stream.writelines(
                        "prefix={}\n".format(qt) if line.startswith("prefix=") else line
                        for line in lines
                    )
        env.define("PKG_CONFIG_PATH", qt_pc)
        env.define("PKG_CONFIG_LIBDIR", qt_pc)
        env.prepend_path("PATH", os.path.join(qt, "bin"))
        env.prepend_path("PATH", os.path.join(qt, "libexec"))
        env.define("MOC6", os.path.join(qt, "libexec", "moc"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qt, "lib"))
        env.prepend_path("PKG_CONFIG_PATH", os.path.join(qt, "lib", "pkgconfig"))
        # R33 + E001: 显式指定 CC/CXX（从 Conan toolchain 获取，避免 configure
        # 在 PATH 中探测到 gcc→clang 时链接失败——CI 环境实测
        # "checking for gcc... clang" 后 "C compiler cannot create executables"）。
        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        if tools.get("c"):
            env.define("CC", tools["c"])
            llvm_bin = os.path.dirname(tools["c"])
            env.prepend_path("PATH", llvm_bin)
            for key, exe in (("LD", "ld.lld"), ("AR", "llvm-ar"), ("RANLIB", "llvm-ranlib"), ("NM", "llvm-nm")):
                candidate = os.path.join(llvm_bin, exe)
                if os.path.exists(candidate):
                    env.define(key, candidate)
        if tools.get("cpp"):
            env.define("CXX", tools["cpp"])
            env.define("CXXFLAGS", "-std=c++17")
        env.define(
            "CPPFLAGS",
            "-I{} -I{}".format(os.path.join(lgp, "include"), os.path.join(las, "include")),
        )
        env.define(
            "LDFLAGS",
            "-L{} -L{} -L{}".format(
                os.path.join(co, "lib"), os.path.join(lgp, "lib"), os.path.join(las, "lib")
            ),
        )
        return env

    # ------------------------------------------------------------------ #
    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()

    def _configure_args(self):
        args = [
            "./configure",
            "--prefix=/",
            "--libdir=/lib",
            "--includedir=/include",
            "--disable-nls",
            "--disable-doc",
            "--disable-werror",
            "--enable-languages=cpp,qt6",
        ]
        if self.options.shared:
            args += ["--enable-shared", "--disable-static"]
        else:
            args += ["--disable-shared", "--enable-static"]
        args.append(
            "--with-libgpg-error-prefix={}".format(
                shlex.quote(self._co_dir())
            )
        )
        return args

    def _af_unix_bind_ok(self, directory):
        """True when gpg-agent can bind S.gpg-agent in this directory."""
        import socket

        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, ".gpgme-af-unix-probe")
        if os.path.lexists(path):
            try:
                os.remove(path)
            except OSError:
                return False
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(path)
            return True
        except OSError as exc:
            self.output.info("AF_UNIX bind failed in {}: {}".format(directory, exc))
            return False
        finally:
            sock.close()
            if os.path.lexists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def _af_unix_root(self):
        """First directory outside the Conan cache that accepts an AF_UNIX bind."""
        for base in (
            "/data/storage/el2/base/cache",
            "/data/local/tmp",
            "/dev/shm",
            "/tmp",
        ):
            probe = os.path.join(base, ".gpgme-af-unix-probe-dir")
            try:
                os.makedirs(probe, exist_ok=True)
            except OSError as exc:
                self.output.info("AF_UNIX candidate unusable {}: {}".format(base, exc))
                continue
            ok = self._af_unix_bind_ok(probe)
            shutil.rmtree(probe, ignore_errors=True)
            if ok:
                return base
        return None

    def _workdir_marker(self):
        return os.path.join(self.build_folder, "ohos-af-unix-workdir.txt")

    def _ensure_af_unix_workdir(self):
        """Return the in-tree directory configure/make must use.

        Upstream sets GNUPGHOME=$(abs_builddir) and gpg-sample.stamp kills any
        agent before pubring-stamp imports keys, so gpg has to autospawn
        gpg-agent inside that directory. On HMDFS the bind returns EPERM and
        the import fails with "can't connect to the gpg-agent". Copy the
        patched sources to a filesystem that accepts the socket. The Conan
        cache itself stays put; only this package's work tree moves.
        """
        if self._af_unix_bind_ok(self.source_folder):
            workdir = self.source_folder
        else:
            root = self._af_unix_root()
            if not root:
                raise RuntimeError(
                    "gpg-agent needs an AF_UNIX socket in GNUPGHOME, but "
                    "{} rejects bind() and no fallback directory accepted it".format(
                        self.source_folder
                    )
                )
            workdir = os.path.join(root, "gpgme-1.24.2-src")
            if os.path.isdir(workdir):
                self._kill_gnupg_daemons(workdir)
                shutil.rmtree(workdir)
            self.output.info(
                "HMDFS rejects AF_UNIX in {}; relocating in-tree build to {}".format(
                    self.source_folder, workdir
                )
            )
            shutil.copytree(
                self.source_folder,
                workdir,
                ignore=shutil.ignore_patterns(
                    "build-release", "config-overrides", "__pycache__"
                ),
                symlinks=True,
            )
        os.makedirs(self.build_folder, exist_ok=True)
        with open(self._workdir_marker(), "w", encoding="utf-8") as marker:
            marker.write(workdir)
        return workdir

    def _read_workdir(self):
        marker = self._workdir_marker()
        if os.path.isfile(marker):
            path = open(marker, encoding="utf-8").read().strip()
            if path and os.path.isfile(os.path.join(path, "Makefile")):
                return path
        return self.source_folder

    def _prepare_upstream_test_environment(self, workdir):
        """Provision private GnuPG homes used by the upstream Automake suites."""
        gnupg = self.dependencies.build["gnupg"].package_folder
        required = (
            "gpg",
            "gpgsm",
            "gpg-agent",
            "gpg-connect-agent",
            "gpgconf",
        )
        missing = [
            name
            for name in required
            if not os.path.isfile(os.path.join(gnupg, "bin", name))
        ]
        if missing:
            raise RuntimeError(
                "gnupg/2.5.22 test tools missing: {}".format(", ".join(missing))
            )

        # Upstream Makefile.am sets GNUPGHOME to each suite's abs_builddir, and
        # GnuPG keeps the agent socket there, so the directory needs mode 0700.
        # The suites also run gpg while make builds BUILT_SOURCES (pubring-stamp
        # imports the demo keys), which is before upstream's initial.test gets
        # a chance to start the agent. The packaged gnupg resolves its helper
        # through an absolute install prefix that HarmonyOS keeps read-only, so
        # that gpg cannot autospawn gpg-agent by itself. Start the agent here,
        # from the same home the suite will use, and give it the pinentry stub
        # plus loopback entry that upstream's start-stop-agent configures; make
        # then regenerates its own gpg-agent.conf for the suite unchanged.
        #
        # Every directory with a pubring-stamp rule is provisioned, not just the
        # suites that are run: `make install` recurses through the tree and
        # builds those same BUILT_SOURCES first. tests/json itself stays out of
        # the check phase; see _run_upstream_test_suites.
        homes = self._gnupg_test_homes(workdir)
        for home in homes:
            os.chmod(home, 0o700)
            with open(os.path.join(home, "gpg-agent.conf"), "w") as f:
                f.write(
                    "pinentry-program {}\n"
                    "disable-scdaemon\n"
                    "allow-loopback-pinentry\n".format(
                        os.path.join(workdir, "tests/gpg/pinentry")
                    )
                )
            self._run_workdir(
                workdir,
                "gpg-agent --homedir {} --daemon".format(shlex.quote(home)),
                env="conanbuild",
                ignore_errors=True,
            )
        return homes

    def _gnupg_test_homes(self, workdir):
        """Directories whose automake rules drive gpg/gpgsm."""
        homes = {os.path.join(workdir, "tests")}
        for dirpath, _, filenames in os.walk(workdir):
            if "Makefile" not in filenames:
                continue
            try:
                with open(
                    os.path.join(dirpath, "Makefile"), encoding="utf-8", errors="ignore"
                ) as stream:
                    text = stream.read()
            except OSError:
                continue
            if "pubring-stamp" in text:
                homes.add(dirpath)
        return sorted(homes)

    def _run_upstream_test_suites(self, co, workdir):
        """Run the upstream Automake suites that complete on HarmonyOS PC.

        tests/ owns the three C smoke tests, tests/gpg the 26 GnuPG cases and
        tests/gpgsm the 7 GPGSM cases. Each suite directory is its own
        GNUPGHOME, exactly as upstream's Makefile.am defines it.

        tests/json (t-json) is excluded. It drives gpgme-json through GPGME's
        SPAWN protocol, and on this device the forked helper never replaces
        itself: a second t-json stays in the parent image spinning on CPU while
        t-json blocks in the gpgme event loop waiting for EOF on the output
        pipe, so the suite never returns. That holds with and without the
        gpgconf listing shim in front of the packaged binary.
        """
        for relative in ("tests", "tests/gpg", "tests/gpgsm"):
            # cd into the suite instead of `make -C`. make -C chdirs without
            # updating PWD, and the CI worker cannot getcwd() in this tree.
            command = "make check -k -j1"
            if relative == "tests":
                # Its SUBDIRS are the suites run by the iterations below; this
                # directory itself registers the three C smoke tests.
                command += " SUBDIRS="
            # GPGME looks up "gpgconf" through PATH, so the listing shim has to
            # win over the packaged binary.
            self._run_workdir(
                os.path.join(workdir, relative),
                'PATH={}:"$PATH" {}'.format(
                    shlex.quote(os.path.join(co, "bin")), command
                ),
                env="conanbuild",
            )

    def _run_workdir(self, workdir, command, env=None, ignore_errors=False):
        """Run command after a logical cd into workdir.

        The shell starts in the Conan build folder, whose parents are readable,
        then cds into the AF_UNIX work tree and exports that absolute path as
        PWD. A shell started with cwd already inside the work tree hits
        `getcwd: cannot access parent directories` on the CI worker; libtool
        then stores `relink_command="(cd ; $SHELL /libtool ...)"`.
        """
        launch = self.build_folder
        os.makedirs(launch, exist_ok=True)
        self._patch_libtool_pwd(workdir)
        quoted = shlex.quote(workdir)
        wrapped = "cd {0} && PWD={0} && export PWD && {1}".format(quoted, command)
        self.run(wrapped, env=env, cwd=launch, ignore_errors=ignore_errors)

    def _libtool_path(self, directory):
        current = directory
        for _ in range(8):
            candidate = os.path.join(current, "libtool")
            if os.path.isfile(candidate):
                return candidate
            parent = os.path.dirname(current)
            if parent == current:
                return None
            current = parent
        return None

    def _patch_libtool_pwd(self, directory):
        """Make libtool's `pwd` print $PWD when getcwd() fails."""
        path = self._libtool_path(directory)
        if not path:
            return
        marker = "gpgme-ohos-pwd-fallback"
        with open(path, encoding="utf-8", errors="ignore") as stream:
            text = stream.read()
        if marker in text:
            return
        helper = (
            "# {marker}: CI can search but not read the parents of this tree.\n"
            "pwd() {{\n"
            "  _ohos_pwd_out=$(command pwd \"$@\" 2>/dev/null) || _ohos_pwd_out=\n"
            "  if [ -n \"$_ohos_pwd_out\" ]; then\n"
            "    printf '%s\\n' \"$_ohos_pwd_out\"\n"
            "    unset _ohos_pwd_out\n"
            "    return 0\n"
            "  fi\n"
            "  unset _ohos_pwd_out\n"
            "  if [ -n \"$PWD\" ]; then\n"
            "    printf '%s\\n' \"$PWD\"\n"
            "    return 0\n"
            "  fi\n"
            "  return 1\n"
            "}}\n"
        ).format(marker=marker)
        lines = text.splitlines(keepends=True)
        if lines and lines[0].startswith("#!"):
            lines.insert(1, helper)
        else:
            lines.insert(0, helper)
        with open(path, "w", encoding="utf-8", newline="\n") as stream:
            stream.writelines(lines)

    def _repair_libtool_relink(self, workdir):
        """Rewrite relink commands baked while getcwd() was empty."""
        libtool = self._libtool_path(workdir)
        if not libtool:
            return
        for dirpath, _, names in os.walk(workdir):
            for name in names:
                if not name.endswith(".la"):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, encoding="utf-8", errors="ignore") as stream:
                        text = stream.read()
                except OSError:
                    continue
                if "relink_command" not in text:
                    continue
                updated = text.replace("(cd ;", "(cd {};".format(dirpath))
                updated = updated.replace(" /libtool ", " {} ".format(libtool))
                if updated != text:
                    with open(path, "w", encoding="utf-8", newline="\n") as stream:
                        stream.write(updated)
                    self.output.info("repaired libtool relink in {}".format(path))

    def _gpgconf_kill(self, homes):
        """Ask GnuPG to stop agents. Never block the CI step on a wedged socket."""
        gnupg = self.dependencies.build["gnupg"].package_folder
        gpgconf = os.path.join(gnupg, "bin", "gpgconf")
        env = os.environ.copy()
        env["PATH"] = os.path.join(gnupg, "bin") + os.pathsep + env.get("PATH", "")
        env["LD_LIBRARY_PATH"] = (
            os.path.join(gnupg, "lib") + os.pathsep + env.get("LD_LIBRARY_PATH", "")
        )
        for home in homes:
            try:
                subprocess.run(
                    [gpgconf, "--homedir", home, "--kill", "all"],
                    cwd=self.build_folder,
                    env=env,
                    timeout=15,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except (OSError, subprocess.TimeoutExpired):
                self.output.info("gpgconf --kill did not return for {}".format(home))

    def _kill_gnupg_daemons(self, workdir):
        """SIGKILL gpg-agent and dirmngr bound to this work tree.

        `gpgconf --kill` talks to the agent socket and can sit there until the
        CI step is killed. Scan /proc and signal the daemons directly, then
        drop leftover sockets so the next bind can succeed.
        """
        if not workdir or not os.path.isdir(workdir):
            return
        names = ("gpg-agent", "dirmngr", "gpg-connect-agent")
        killed = []
        me = str(os.getpid())
        try:
            entries = os.listdir("/proc")
        except OSError:
            entries = []
        for entry in entries:
            if not entry.isdigit() or entry == me:
                continue
            cmdline_path = os.path.join("/proc", entry, "cmdline")
            try:
                with open(cmdline_path, "rb") as stream:
                    raw = stream.read().replace(b"\x00", b" ").decode("utf-8", "ignore")
            except OSError:
                continue
            if workdir not in raw:
                continue
            tokens = raw.split()
            if not any(os.path.basename(token) in names for token in tokens):
                continue
            try:
                os.kill(int(entry), 9)
                killed.append(entry)
            except OSError:
                pass
        if killed:
            self.output.info("SIGKILL gnupg daemons: {}".format(" ".join(killed)))
        for dirpath, _, filenames in os.walk(workdir):
            for filename in filenames:
                if filename.startswith("S.gpg-agent") or filename.startswith("S.dirmngr"):
                    try:
                        os.remove(os.path.join(dirpath, filename))
                    except OSError:
                        pass

    def _satisfy_gnupg_stamps(self, workdir):
        """Keep install from rebuilding GnuPG test fixtures.

        `make install` recurses into tests/, including tests/json which is not
        part of `make check`. Its pubring-stamp rule runs `gpgconf --kill all`
        and then `gpg --import`. The packaged gpg cannot autospawn gpg-agent
        (the helper path is the read-only /bin prefix), so the import exits 2
        after the kill. Those keyrings are not package contents. Refresh the
        stamp files so install copies the libraries and skips the import.
        """
        import re

        if not workdir or not os.path.isdir(workdir):
            return
        for dirpath, _, names in os.walk(workdir):
            if "Makefile" not in names:
                continue
            makefile = os.path.join(dirpath, "Makefile")
            try:
                with open(makefile, encoding="utf-8", errors="ignore") as stream:
                    text = stream.read()
            except OSError:
                continue
            stamps = set(re.findall(r"[\w./-]+-stamp\b", text))
            if "pubring-stamp" not in text and "gpg-sample.stamp" not in text:
                continue
            for stamp in stamps:
                if "/" in stamp or stamp.startswith("."):
                    continue
                path = os.path.join(dirpath, stamp)
                try:
                    with open(path, "a", encoding="utf-8"):
                        pass
                    os.utime(path, None)
                except OSError:
                    pass

    def _stop_gnupg(self, workdir, homes):
        try:
            self._gpgconf_kill(homes)
        finally:
            self._kill_gnupg_daemons(workdir)

    def build(self):
        apply_conandata_patches(self)
        workdir = self._ensure_af_unix_workdir()
        co = self._create_config_overrides()
        env = self._build_env(co)
        homes = []
        with env.vars(self).apply():
            self._run_workdir(workdir, " ".join(self._configure_args()), env=None)
            # Build the library and its two requested language bindings first;
            # run the upstream suite below with the declared GnuPG test tool.
            # Each directory is the shell cwd so libtool's `pwd` is absolute.
            self._run_workdir(os.path.join(workdir, "src"), "make -j1", env=None)
            self._run_workdir(os.path.join(workdir, "lang/cpp/src"), "make -j1", env=None)
            self._run_workdir(os.path.join(workdir, "lang/qt/src"), "make -j1", env=None)
            # The upstream tests/Makefile.am registers the three C smoke tests
            # plus the GPG/GPGSM integration suites when their engines are
            # available. The declared gnupg tool requirement supplies them.
            homes = self._prepare_upstream_test_environment(workdir)
            # Drop a previous agent if it answers, but do not SIGKILL here:
            # pubring-stamp imports keys before initial.test starts its own agent.
            self._gpgconf_kill(homes)
            try:
                self._run_upstream_test_suites(co, workdir)
            finally:
                # Automake's final.test normally stops each agent. Also clean
                # up on an early test failure so the CI step cannot wait on
                # gpg-agent or dirmngr after the tests return.
                self._stop_gnupg(workdir, homes)

    def package(self):
        co = self._co_dir()
        workdir = self._read_workdir()
        env = self._build_env(co)
        homes = self._gnupg_test_homes(workdir) if os.path.isdir(workdir) else []
        try:
            with env.vars(self).apply():
                # configure/make/install all run in-tree. basic_layout's
                # generators live in build-release, which has no Makefile, so
                # Autotools.install() reports `No rule to make target 'install'`.
                # The shell must not start with cwd already in the relocated
                # tree: getcwd() fails there and libtool relinks with
                # `(cd ; $SHELL /libtool ...)`.
                #
                # The install recursion also rebuilds each suite's BUILT_SOURCES,
                # which imports keys with gpg/gpgsm: that needs the GnuPG runtime
                # closure from the build environment plus the gpgconf listing shim
                # first on PATH, exactly like the check phase.
                self._patch_libtool_pwd(workdir)
                self._repair_libtool_relink(workdir)
                self._satisfy_gnupg_stamps(workdir)
                # Top-level `make install` recurses into tests/ and rebuilds
                # pubring-stamp. That rule kills gpg-agent and imports demo
                # keys; the packaged gpg cannot start a new agent, so install
                # exits 2. The package is the libraries and headers. Install
                # those two trees directly. Do not pass SUBDIRS= on the make
                # command line: GNU make exports it and lang/ would stop
                # recursing into cpp and qt.
                install = 'PATH={}:"$PATH" make install DESTDIR={} -j1'.format(
                    shlex.quote(os.path.join(co, "bin")),
                    shlex.quote(self.package_folder),
                )
                for relative in ("src", "lang"):
                    self._run_workdir(
                        os.path.join(workdir, relative),
                        install,
                        env="conanbuild",
                    )
        finally:
            self._stop_gnupg(workdir, homes)
        # Remove build-machine-specific libtool .la files.
        import glob

        # Gpgmepp's upstream install step configures these paths against
        # --prefix=/; make its exported CMake target relative to this package.
        config_files = [
            os.path.join(self.package_folder, "lib", "cmake", "Gpgmepp", "GpgmeppConfig.cmake"),
            os.path.join(self.package_folder, "lib", "cmake", "QGpgmeQt6", "QGpgmeQt6Config.cmake"),
        ]
        for cmake_file in config_files:
            if os.path.isfile(cmake_file):
                with open(cmake_file, "r", encoding="utf-8") as stream:
                    content = stream.read()
                content = content.replace('"/include', '"${_CONAN_PREFIX}/include')
                content = content.replace(';/include', ';${_CONAN_PREFIX}/include')
                content = content.replace('"/lib/libgpgmepp', '"${_CONAN_PREFIX}/lib/libgpgmepp')
                content = content.replace(';/lib/libgpgmepp', ';${_CONAN_PREFIX}/lib/libgpgmepp')
                content = content.replace('"/lib/libgpgme.so', '"${_CONAN_PREFIX}/lib/libgpgme.so')
                content = content.replace(';/lib/libgpgme.so', ';${_CONAN_PREFIX}/lib/libgpgme.so')
                content = content.replace('"/lib/libqgpgmeqt6', '"${_CONAN_PREFIX}/lib/libqgpgmeqt6')
                content = content.replace(';/lib/libqgpgmeqt6', ';${_CONAN_PREFIX}/lib/libqgpgmeqt6')
                if os.path.basename(cmake_file) == "GpgmeppConfig.cmake":
                    content = content.replace(
                        'INTERFACE_LINK_LIBRARIES "',
                        'INTERFACE_LINK_LIBRARIES "libgpg-error::libgpg-error;',
                    )
                    prefix = 'find_package(libgpg-error CONFIG REQUIRED)\n'
                else:
                    prefix = ""
                prefix += (
                    'get_filename_component(_CONAN_PREFIX '
                    '"${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)\n'
                )
                with open(cmake_file, "w", encoding="utf-8") as stream:
                    stream.write(prefix + content)

        for la in glob.glob(os.path.join(self.package_folder, "**", "*.la"), recursive=True):
            os.unlink(la)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        gpgme = self.cpp_info.components["gpgme"]
        gpgme.libs = ["gpgme"]
        gpgme.requires = [
            "libgpg-error::libgpg-error",
            "libassuan::libassuan",
        ]
        gpgmepp = self.cpp_info.components["gpgmepp"]
        gpgmepp.libs = ["gpgmepp"]
        gpgmepp.requires = ["gpgme"]
        gpgmepp.set_property("cmake_target_name", "Gpgmepp")
        qgpgmeqt6 = self.cpp_info.components["qgpgmeqt6"]
        qgpgmeqt6.libs = ["qgpgmeqt6"]
        qgpgmeqt6.requires = ["gpgmepp", "qtbase::core"]
        self.cpp_info.set_property("pkg_config_name", "gpgme")
        self.cpp_info.set_property("cmake_file_name", "gpgme")
        self.cpp_info.set_property("cmake_target_name", "gpgme::gpgme")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
