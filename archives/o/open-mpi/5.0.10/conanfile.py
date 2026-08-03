from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, rm, rmdir, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import shutil
import signal
import stat
import tarfile
import tempfile
from pathlib import Path


class OpenMpiConan(ConanFile):
    name = "open-mpi"
    version = "5.0.10"
    description = "High performance Message Passing Interface implementation"
    license = "BSD-3-Clause"
    homepage = "https://www.open-mpi.org"
    url = "https://github.com/open-mpi/ompi"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("open-mpi/5.0.10 is packaged only for OHOS")
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("open-mpi/5.0.10 supports only OHOS armv8")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @staticmethod
    def _enable_ohos_in_config_sub(content):
        """Support both the 2021 and 2023 GNU config.sub layouts."""
        if "ohos*)" not in content:
            content = content.replace(
                "musl* | newlib* | relibc* | uclibc*)",
                "musl* | newlib* | relibc* | uclibc* | ohos*)",
            )
        if "linux-ohos*" not in content:
            content = content.replace(
                "linux-uclibc*- | linux-mlibc*- )",
                "linux-uclibc*- | linux-mlibc*- | linux-ohos*- )",
            ).replace(
                "linux-uclibc* )", "linux-uclibc* | linux-ohos* )"
            )
        return content

    def generate(self):
        # OHOS creates setgid directories for `mktemp -d`, but the sandbox
        # rejects writes inside them.  Autoconf's mkdir fallback is writable.
        wrapper_dir = Path(self.build_folder) / ".ohos_mktemp"
        wrapper_dir.mkdir(exist_ok=True, parents=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text("#!/bin/sh\nexit 1\n")
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
            "--enable-mpi-fortran=no",
            "--enable-mpi-cxx=no",
            "--with-hwloc=internal",
            "--with-libevent=internal",
            "--with-pmix=internal",
            "--with-prrte=internal",
            "--with-libltdl=no",
            "--disable-wrapper-rpath",
            "--disable-wrapper-runpath",
        ])
        if self.options.get_safe("fPIC", True):
            tc.configure_args.append("--with-pic")
        tc.generate()

        self.output.info("Created mktemp fallback for OHOS config.status")

    def build(self):
        # OHOS CI wraps `conan create` stdout in a `tee` pipeline. When tee
        # stalls (sandbox pipe-buffer pressure), ANY stdout write from conan's
        # own Python process (self.output.info, load(), save(), autotools
        # subprocess stdout relay) raises SIGPIPE; conan's Python inherits
        # SIGPIPE's default action (terminate) and is silently killed mid-build
        # — proven by R25-R28 all dying right after `Updated embedded libevent
        # config.sub` with no configure ever starting. Ignore SIGPIPE for the
        # ENTIRE build() span so conan survives transient pipe closures at
        # every point (config.sub patching, autoreconf, configure, make). The
        # inner finally below restores it before package() runs.
        import signal as _sig
        previous_sigpipe = _sig.signal(_sig.SIGPIPE, _sig.SIG_IGN)
        updated_scripts = 0
        checked_scripts = 0
        seen_scripts = set()
        for directory, _, filenames in os.walk(self.source_folder, followlinks=True):
            if "config.sub" not in filenames:
                continue
            config_sub = os.path.join(directory, "config.sub")
            real_config_sub = os.path.realpath(config_sub)
            if real_config_sub in seen_scripts:
                continue
            seen_scripts.add(real_config_sub)
            checked_scripts += 1
            content = load(self, config_sub)
            updated = self._enable_ohos_in_config_sub(content)
            if updated == content:
                continue
            save(self, config_sub, updated)
            updated_scripts += 1
            self.output.info(f"Enabled linux-ohos in {config_sub}")

        primary_config_sub = os.path.join(self.source_folder, "config", "config.sub")
        primary_content = load(self, primary_config_sub)
        if "ohos*)" not in primary_content or "linux-ohos*" not in primary_content:
            raise ConanInvalidConfiguration("Failed to update Open MPI config.sub for linux-ohos")
        self.output.info(
            f"Checked {checked_scripts} bundled config.sub scripts; "
            f"updated {updated_scripts} for OHOS"
        )

        # Some 3rd-party deps (libevent, hwloc) are stored as nested tarballs
        # expanded by the main configure script into build-release/. Their
        # bundled config.sub would reject the OHOS triplet. Patch each input
        # archive's config.sub in-place before configure runs.
        for nested_name, nested_top, nested_cs_rel in [
            ("libevent-2.1.12-stable-ompi", "libevent-2.1.12-stable-ompi", "build-aux/config.sub"),
            ("hwloc-2.7.1", "hwloc-2.7.1", "config/config.sub"),
        ]:
            nested_archive = os.path.join(
                self.source_folder, "3rd-party", f"{nested_name}.tar.gz"
            )
            if not os.path.isfile(nested_archive):
                raise ConanInvalidConfiguration(f"Missing embedded {nested_name} tarball")
            with tempfile.TemporaryDirectory(dir=self.build_folder) as temporary_dir:
                with tarfile.open(nested_archive, "r:gz") as archive:
                    archive.extractall(temporary_dir)
                nested_root = os.path.join(temporary_dir, nested_top)
                nested_config_sub = os.path.join(nested_root, nested_cs_rel)
                nested_content = load(self, nested_config_sub)
                nested_updated = self._enable_ohos_in_config_sub(nested_content)
                if "ohos*)" not in nested_updated or "linux-ohos*" not in nested_updated:
                    raise ConanInvalidConfiguration(
                        f"Failed to update embedded {nested_name} config.sub for OHOS"
                    )
                save(self, nested_config_sub, nested_updated)
                replacement_archive = os.path.join(temporary_dir, f"{nested_name}-ohos.tar.gz")
                with tarfile.open(replacement_archive, "w:gz") as archive:
                    archive.add(nested_root, arcname=nested_top)
                shutil.move(replacement_archive, nested_archive)
            self.output.info(f"Updated embedded {nested_name} config.sub for OHOS")
        apply_conandata_patches(self)

        # OHOS CI wraps `conan create` stdout in a `tee` pipeline. When tee
        # stalls (sandbox pipe-buffer pressure), configure's printf to fd 6
        # raises SIGPIPE; autotools traps signal 13 and exits 1, killing the
        # whole configure. Drop 13 from the trapped-signal list so configure
        # survives transient SIGPIPE from the build host's pipe wrapper.
        patched_traps = 0
        for directory, _, filenames in os.walk(self.source_folder, followlinks=True):
            if "configure" not in filenames:
                continue
            cfg = os.path.join(directory, "configure")
            content = load(self, cfg)
            if "for ac_signal in 1 2 13 15; do" not in content:
                continue
            save(self, cfg, content.replace(
                "for ac_signal in 1 2 13 15; do",
                "for ac_signal in 1 2 15; do",
            ))
            patched_traps += 1
            self.output.info(f"Dropped SIGPIPE trap in {cfg}")
        if patched_traps == 0:
            raise ConanInvalidConfiguration("Failed to drop SIGPIPE trap in any configure script")
        self.output.info(f"Dropped SIGPIPE trap in {patched_traps} configure scripts for OHOS")

        wrapper_dir = Path(self.build_folder) / ".ohos_mktemp"
        if not (wrapper_dir / "mktemp").is_file():
            raise ConanInvalidConfiguration("OHOS mktemp fallback was not created")
        previous_path = os.environ.get("PATH", "")
        previous_pthread_size = os.environ.get("ac_cv_sizeof_pthread_t")
        os.environ["PATH"] = f"{wrapper_dir}{os.pathsep}{previous_path}"
        # libevent's AC_CHECK_SIZEOF would otherwise wait on an un-runnable
        # target probe. pthread_t is a pointer-sized type on OHOS aarch64.
        os.environ["ac_cv_sizeof_pthread_t"] = "8"
        self.output.info(f"Prepended mktemp fallback to PATH: {wrapper_dir}")
        self.output.info("Set ac_cv_sizeof_pthread_t=8 for OHOS aarch64")
        # OHOS CI wraps conan's stdout in a `tee` pipeline. When tee stalls
        # (sandbox pipe-buffer pressure) the write end raises SIGPIPE. Conan's
        # own Python process inherits SIGPIPE's default action (terminate), so
        # after configure exits, conan is killed before make() runs — Makefile
        # and config.status are never generated. Ignore SIGPIPE around the
        # configure+make span so conan survives transient pipe closures.
        marker = os.path.join(self.build_folder, "build_phase.marker")
        try:
            # autotools.configure() -> conanfile.run() raises ConanException on
            # SIGPIPE-damaged stdout write to the tee pipe (long configure),
            # even though configure itself succeeded (config.log ends with
            # `configure: exit 0`). conan is silently killed before writing
            # config.status/Makefile. Bypass autotools.configure() entirely:
            # monkey-patch self.run to capture the command Autotools would run,
            # then execute it via subprocess with stdout to a log file (no
            # pipe, no SIGPIPE) — same strategy as the autotools.make() bypass.
            import subprocess
            def run_logged(command, log_file, environment, phase):
                """Keep the CI worker alive while preserving full command output."""
                with open(log_file, "a") as log:
                    process = subprocess.Popen(
                        command,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        cwd=self.build_folder,
                        env=environment,
                    )
                    while process.poll() is None:
                        try:
                            process.wait(timeout=60)
                        except subprocess.TimeoutExpired:
                            self.output.info(f"{phase} still running (CI heartbeat)")
                return process.returncode

            configure_log_path = os.path.join(self.package_metadata_folder, "configure.stdout.log")
            configure_env = dict(os.environ)
            configure_env["PWD"] = self.build_folder
            autotools = Autotools(self)
            captured_cmd = None
            def _capture_run(cmd, **kw):
                nonlocal captured_cmd
                captured_cmd = cmd
            original_run = self.run
            self.run = _capture_run
            try:
                autotools.configure()
            finally:
                self.run = original_run
            if captured_cmd is None:
                raise ConanInvalidConfiguration("failed to capture configure command from autotools.configure()")
            configure_shell = os.environ.get("CONFIG_SHELL", "bash")
            open(configure_log_path, "w").close()
            configure_rc = run_logged(
                [configure_shell, "-c", captured_cmd], configure_log_path,
                configure_env, "configure",
            )
            if configure_rc != 0:
                with open(configure_log_path, "r") as fh:
                    tail_lines = fh.readlines()[-30:]
                tail_str = "".join(tail_lines)
                raise ConanInvalidConfiguration(
                    f"configure failed with exit code {configure_rc}; tail of {configure_log_path}:\n{tail_str}"
                )
            self.output.info("configure completed via subprocess (bypass autotools.configure)")
            with open(marker + ".configure_done", "w") as fh:
                fh.write("ok")
            # autotools.configure()'s monkey-patch capture (self.run swap)
            # may have re-installed SIGPIPE's default action during the swap
            # restore. Re-assert SIG_IGN before the make span so conan survives
            # SIGPIPE noise on the tee pipe during long make output.
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
            # autotools.make() -> conanfile.run() raises ConanException on
            # SIGPIPE-damaged stdout write to the tee pipe (long make install),
            # even though make itself succeeded (.o artifacts, clean
            # `make[1]: Leaving directory` in conan log). conan's
            # conanfile_exception_formatter wraps that into a new ConanException
            # which conanfile-level try/except can't fully suppress. Bypass
            # autotools.make() entirely and call `make -j1` via subprocess with
            # stdout to a log file (no pipe, no SIGPIPE) so conan's run()
            # SIGPIPE detection never triggers.
            import subprocess
            # Write make log to package_metadata_folder (survives conan's
            # build-folder cleanup) so we can diagnose real make errors.
            make_log_path = os.path.join(self.package_metadata_folder, "make.stdout.log")
            # OHOS sandbox denies getcwd() on certain paths; make's per-command
            # subshells (bash -c) call getcwd() to init $PWD and emit thousands
            # of `chdir/pwd/shell-init: error retrieving current directory`
            # warnings to stderr, which makes make return exit code 2 even
            # though every CC/CCLD compiled cleanly. Set PWD env so bash
            # subshells init $PWD from env without calling getcwd().
            make_env = dict(os.environ)
            make_env["PWD"] = self.build_folder
            open(make_log_path, "w").close()
            make_rc = run_logged(
                ["make", "-j1", "-C", self.build_folder], make_log_path,
                make_env, "make -j1",
            )
            if make_rc != 0:
                # Surface the last 30 lines of make log in the error so the
                # real make error (compile/link failure) is visible directly.
                with open(make_log_path, "r") as fh:
                    tail_lines = fh.readlines()[-30:]
                tail_str = "".join(tail_lines)
                raise ConanInvalidConfiguration(
                    f"make -j1 failed with exit code {make_rc}; tail of {make_log_path}:\n{tail_str}"
                )
            self.output.info("make -j1 completed via subprocess (bypass autotools.make)")
            with open(marker + ".make_done", "w") as fh:
                fh.write("ok")
            check_rc = run_logged(
                ["make", "-j1", "-C", self.build_folder, "check"], make_log_path,
                make_env, "make check",
            )
            if check_rc != 0:
                with open(make_log_path, "r") as fh:
                    tail_str = "".join(fh.readlines()[-30:])
                raise ConanInvalidConfiguration(
                    f"make check failed with exit code {check_rc}; "
                    f"tail of {make_log_path}:\n{tail_str}"
                )
            self.output.info("make check completed")
        finally:
            signal.signal(signal.SIGPIPE, previous_sigpipe)
            os.environ["PATH"] = previous_path
            if previous_pthread_size is None:
                os.environ.pop("ac_cv_sizeof_pthread_t", None)
            else:
                os.environ["ac_cv_sizeof_pthread_t"] = previous_pthread_size

    def package(self):
        # OHOS sandbox denies mkfifo in conan's home (the parallel jobserver
        # of `make install -j20` does so to coordinate workers), which makes
        # conan return non-zero even though every file installs fine. Force
        # -j1 in install's args so Autotools skips the parallel jobserver
        # (build_jobs() only adds -jN when no -j is already passed).
        previous_nproc = os.environ.pop("CONAN_CPU_USE", None)
        previous_makeflags = os.environ.pop("MAKEFLAGS", None)
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        if previous_nproc is not None:
            os.environ["CONAN_CPU_USE"] = previous_nproc
        if previous_makeflags is not None:
            os.environ["MAKEFLAGS"] = previous_makeflags
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        rm(self, "*.la", self.package_folder, recursive=True)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["mpi"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "MPI")
        self.cpp_info.set_property("cmake_target_name", "MPI::MPI_C")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.define_path("OPAL_PREFIX", self.package_folder)
