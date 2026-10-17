import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class LibvipsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv keeps env="conanrun" meaningful for the ctest / shell-test
    # runs below (LD_LIBRARY_PATH from the shared glib deps in the chain).
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        self._set_ohos_tmpdir()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        self._set_ohos_tmpdir()
        # The OHOS CI worker only execs OHOS-signed ELF files, and only from
        # exec-allowed paths (the conan cache p/ tree is not one).  Mirror the
        # packaged CLI tools into the build folder, sign the copies, and put
        # that directory on PATH so the vendored shell tests can launch vips,
        # vipsheader and vipsthumbnail.
        self._prepare_cli_tools()
        # ctest wires the six-check consumer smoke test plus the C-based upstream
        # tests 'descriptors' and 'connections' (see CMakeLists.txt).  The
        # locally-built test executables need an OHOS exec signature first.
        self._sign_built_tests()
        self.run("ctest --output-on-failure", env="conanrun")
        # The remaining vendored upstream tests drive the packaged vips CLI
        # tools and the compiled C helpers.  Fail fast with a clear message if
        # those tools cannot be launched on the worker (rather than a confusing
        # mid-script failure).
        self._smoke_vips_cli()
        # Vendored upstream shell tests, rewritten self-sufficient (see
        # upstream/test_{token,cli,seq,threading}.sh). They are executed through
        # bash: on OHOS /system/bin/sh (mksh) is not a reliable ELF launcher.
        self._prepare_seed_image()
        self._run_vendored_shell_tests()

    # -- CLI tool provisioning -------------------------------------------

    def _prepare_cli_tools(self):
        try:
            dep = self.dependencies["libvips"]
        except KeyError:
            return
        if not dep.package_folder:
            return
        pkg_bin = os.path.join(dep.package_folder, "bin")
        if not os.path.isdir(pkg_bin):
            return
        if str(self.settings.os) != "OHOS":
            self._prepend_to_path(pkg_bin)
            return
        # Mirror bin/ + libvips.so into the exec-allowed build folder, keeping
        # the Meson-installed $ORIGIN/../lib layout so the tools still resolve
        # libvips.so, then sign the copies.
        rundir = os.path.join(self.build_folder, "pkg")
        dest_bin = os.path.join(rundir, "bin")
        dest_lib = os.path.join(rundir, "lib")
        os.makedirs(dest_bin, exist_ok=True)
        os.makedirs(dest_lib, exist_ok=True)
        copied = []
        for name in ("vips", "vipsheader", "vipsthumbnail"):
            src = os.path.join(pkg_bin, name)
            if os.path.isfile(src):
                dst = os.path.join(dest_bin, name)
                shutil.copy2(src, dst)
                copied.append(dst)
        pkg_lib = os.path.join(dep.package_folder, "lib")
        if os.path.isdir(pkg_lib):
            for entry in os.listdir(pkg_lib):
                if entry.startswith("libvips.so"):
                    shutil.copy2(os.path.join(pkg_lib, entry),
                                 os.path.join(dest_lib, entry))
        self._ohos_sign(copied)
        self._prepend_to_path(dest_bin)

    def _smoke_vips_cli(self):
        self.output.info("Smoke: packaged vips CLI --version")
        self.run("vips --version", env="conanrun")

    def _prepend_to_path(self, directory):
        if not os.path.isdir(directory):
            return
        path = os.environ.get("PATH", "")
        os.environ["PATH"] = directory + (os.pathsep + path if path else "")

    # -- OHOS exec signing (mirrors libevent test_package) ---------------

    def _sign_built_tests(self):
        # The C helpers built by this test_package's CMake project.
        self._ohos_sign(self._built_test_executables())

    def _built_test_executables(self):
        names = ("test_vips", "test_descriptors", "test_connections", "test_token")
        dirs = [self.build_folder]
        bt = self.settings.get_safe("build_type")
        if bt:
            dirs.append(os.path.join(self.build_folder, bt))
        found = []
        for directory in dirs:
            for name in names:
                path = os.path.join(directory, name)
                if os.path.isfile(path) and path not in found:
                    found.append(path)
        return found

    def _ohos_sign(self, paths):
        if str(self.settings.os) != "OHOS":
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException(
                "OHOS exec signing requires llvm-objcopy and binary-sign-tool "
                "next to the configured C compiler")
        for path in paths:
            if not os.path.isfile(path):
                continue
            temporary = f"{path}.signing"
            original_mode = os.stat(path).st_mode
            try:
                shutil.copy2(path, temporary)
                self.run(self._shell_join(
                    [objcopy, "--remove-section", ".codesign", temporary]),
                    env="conanrun")
                self.run(self._shell_join(
                    [signer, "sign", "-inFile", temporary, "-outFile",
                     temporary, "-selfSign", "1"]),
                    env="conanrun")
                os.chmod(temporary, original_mode)
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c", "") or compilers.get("cpp", "")
        compiler_dir = os.path.dirname(compiler) if compiler else ""
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    def _shell_join(self, arguments):
        arguments = [str(argument) for argument in arguments]
        if self.settings.os == "Windows":
            return subprocess.list2cmdline(arguments)
        return shlex.join(arguments)

    # -- vendored upstream shell tests -----------------------------------

    def _bash(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        if bash:
            return bash
        if str(self.settings.os) == "OHOS":
            return "/data/service/hnp/bin/bash"
        return "bash"

    def _run_vendored_shell_tests(self):
        bash = self._bash()
        upstream = os.path.join(self.recipe_folder, "upstream")
        # Vendored upstream shell tests, rewritten self-sufficient.  Each maps to
        # one Meson-registered upstream test (test/meson.build):
        #   'token'      -> test_token.sh  (byte-for-byte; it runs ./test_token,
        #                  so it must run from the CMake build folder below)
        #   'cli'        -> test_cli.sh
        #   'seq'        -> test_seq.sh
        #   'threading'  -> test_threading.sh
        for script in ("test_token.sh", "test_cli.sh", "test_seq.sh", "test_threading.sh"):
            path = os.path.join(upstream, script)
            if not os.path.isfile(path):
                self.output.warning(f"vendored shell test missing: {path}")
                continue
            cwd = self._token_build_dir() if script == "test_token.sh" else None
            self.output.info(f"Running vendored upstream shell test: {script}")
            rc = self.run(f'"{bash}" "{path}"', env="conanrun", ignore_errors=True, cwd=cwd)
            if rc == 0:
                self.output.info(f"PASS: {script}")
            elif rc == 77:
                self.output.info(f"SKIP: {script} (exit 77, feature not configured)")
            else:
                raise ConanException(f"{script} failed with exit code {rc}")

    def _token_build_dir(self):
        # test_token.sh invokes './test_token' from its cwd (byte-for-byte
        # upstream), so run it from the directory holding the CMake-built
        # executable.  Single-config generators (Ninja, used on OHOS) place it in
        # the build root; multi-config generators put it under a per-configuration
        # subfolder.
        for cand in (self.build_folder,
                     os.path.join(self.build_folder, str(self.settings.build_type))):
            if os.path.isfile(os.path.join(cand, "test_token")):
                return cand
        self.output.warning("vendored test_token executable not found under the build "
                            "folder; running test_token.sh from the build root")
        return self.build_folder

    # -- seed image -------------------------------------------------------

    def _prepare_seed_image(self):
        # The vendored upstream shell tests need a seed whose geometry is
        # exactly 290x442: test_cli.sh keeps the upstream thumbnail-size
        # assertions, which are derived from that geometry (e.g. -s 100 ->
        # 66x100, -s "2000<" -> 1312x2000).  Upstream draws this seed from the
        # test-suite/images git submodule; here we synthesise an equivalent
        # black RGB PNG at build time with the packaged vips CLI.  (The CI
        # pre-flight applies the PR as a git patch and GitCode's pull/<n>.diff
        # endpoint cannot carry new binary files, so a committed seed would
        # have to be base64 text - instead the seed is generated at runtime,
        # keeping the PR diff small.)  Point variables.sh at it via TEST_IMAGE.
        seed = os.path.join(self.build_folder, "sample.png")
        if not os.path.isfile(seed):
            self.run('vips black "%s" 290 442 --bands 3' % seed,
                     env="conanrun")
        os.environ["TEST_IMAGE"] = seed

    # -- misc --------------------------------------------------------------

    def _set_ohos_tmpdir(self):
        if str(self.settings.os) != "OHOS":
            return
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
