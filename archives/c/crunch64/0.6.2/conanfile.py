#!/usr/bin/env python3
"""Conan recipe for crunch64 0.6.2: Cargo, native HarmonyOS C static library."""
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import sysconfig

import certifi
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs, cross_building
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class Crunch64Conan(ConanFile):
    name = "crunch64"
    version = "0.6.2"
    description = "N64 Yaz0, Yay0, MIO0 and gzip compression, with a C API"
    license = "MIT"
    homepage = "https://github.com/decompals/crunch64"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        copy(self, "*.patch", src=os.path.join(self.recipe_folder, "patches"),
             dst=os.path.join(self.export_sources_folder, "patches"))

    def build_requirements(self):
        self.tool_requires("rust-toolchain/1.97.1")
        self.tool_requires("openssl/3.5.6.1.1")

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8" or cross_building(self):
            raise ConanInvalidConfiguration("Use native HarmonyOS armv8 build and host profiles")
        if str(self.settings.build_type) not in ("Debug", "Release"):
            raise ConanInvalidConfiguration("Supported build types: Debug, Release")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _cc(self):
        return self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")

    def _sign_copy(self, source, destination, sign_tool):
        destination.parent.mkdir(parents=True, exist_ok=True)
        process = subprocess.run(
            [sign_tool, "sign", "-inFile", str(source), "-outFile", str(destination), "-selfSign", "1"],
            capture_output=True, timeout=300)
        if process.returncode or not destination.is_file():
            raise ConanException("Cannot sign private Rust tool copy: " + process.stderr.decode(errors="replace"))
        destination.chmod(0o755)

    def _rust_environment(self):
        # Keep signing and Cargo's OpenSSL runtime private to this build.
        # Conan dependencies and system library directories remain immutable.
        rust = Path(self.dependencies.build["rust-toolchain"].package_folder)
        openssl = Path(self.dependencies.build["openssl"].package_folder)
        runtime = (Path(self.build_folder) / "rust-runtime").resolve()
        (runtime / "bin").mkdir(parents=True, exist_ok=True)
        (runtime / "lib").mkdir(exist_ok=True)
        cc = self._cc()
        sign_tool = shutil.which("binary-sign-tool")
        if not sign_tool:
            raise ConanInvalidConfiguration("HarmonyOS binary-sign-tool is required to prepare the Rust runtime")
        for name in ("crypto", "ssl"):
            libraries = list(openssl.rglob("lib" + name + ".a"))
            if len(libraries) != 1:
                raise ConanException("Expected one static OpenSSL archive for " + name)
            command = [cc, "-shared", "-Wl,-z,relro,-z,now", "-Wl,-soname,lib" + name + ".so",
                       "-Wl,--whole-archive", str(libraries[0]), "-Wl,--no-whole-archive", "-ldl", "-pthread"]
            if name == "ssl":
                command += ["-L" + str(runtime / "lib"), "-lcrypto"]
            command += ["-o", str(runtime / "lib" / ("lib" + name + ".so"))]
            self.run(shlex.join(command), env="conanbuild")
        for name in ("cargo", "rustc"):
            self._sign_copy(rust / "bin" / name, runtime / "bin" / name, sign_tool)
        drivers = list((rust / "lib").glob("librustc_driver*.so"))
        if len(drivers) != 1:
            raise ConanException("Expected one Rust compiler driver")
        self._sign_copy(drivers[0], runtime / "lib" / drivers[0].name, sign_tool)
        # Avoid loading an application's older libc++ before the system copy.
        libcxx = next((p for p in (Path("/system/lib64/libc++_shared.so"),
                                  Path("/usr/lib/libc++_shared.so")) if p.is_file()), None)
        if libcxx is None:
            raise ConanException("System libc++_shared.so is unavailable")
        self._sign_copy(libcxx, runtime / "lib/libc++_shared.so", sign_tool)
        rustlib = runtime / "lib/rustlib"
        if not rustlib.exists():
            rustlib.symlink_to(rust / "lib/rustlib", target_is_directory=True)
        cargo_home = Path(self.build_folder) / "cargo-home"
        cargo_home.mkdir(exist_ok=True)
        ca = certifi.where()
        (cargo_home / "config.toml").write_text(
            '[source.crates-io]\nreplace-with = "rsproxy-sparse"\n'
            '[source.rsproxy-sparse]\nregistry = "sparse+https://rsproxy.cn/index/"\n'
            '[net]\nretry = 3\n[http]\ntimeout = 120\ncainfo = ' + json.dumps(ca) + '\n', encoding="utf-8")
        tmp = Path(self.build_folder) / "tmp"
        tmp.mkdir(exist_ok=True)
        env = Environment()
        for key in ("CARGO_BUILD_TARGET", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "RUSTC_BOOTSTRAP",
                    "RUSTUP_TOOLCHAIN", "CARGO_ENCODED_RUSTFLAGS"):
            env.unset(key)
        env.define("RUSTC", str(runtime / "bin/rustc"))
        env.define("RUSTFLAGS", "-C linker=" + cc)
        env.define("CC", cc)
        env.define("CARGO_HOME", str(cargo_home))
        env.define("CARGO_TARGET_DIR", str(Path(self.build_folder) / "target"))
        env.define("CARGO_BUILD_JOBS", str(min(build_jobs(self), 2)))
        env.define("CARGO_HTTP_CAINFO", ca)
        env.define("TMPDIR", str(tmp))
        env.prepend_path("PATH", str(runtime / "bin"))
        env.prepend_path("LD_LIBRARY_PATH", str(runtime / "lib"))
        env.vars(self, scope=None).save_script("crunch64_rust")
        self.run(shlex.join([str(runtime / "bin/rustc"), "--version"]), env=["conanbuild", "crunch64_rust"])
        return str(runtime / "bin/cargo")

    def _logged_run(self, command, log_name):
        capture = io.StringIO()
        try:
            self.run(shlex.join(command), cwd=self.source_folder,
                     env=["conanbuild", "crunch64_rust"], stdout=capture, stderr=capture)
        finally:
            output = capture.getvalue()
            (Path(self.build_folder) / log_name).write_text(output, encoding="utf-8")
            self.output.info(output)
        return output

    def _test_python_bindings(self, cargo, mode):
        # Build the upstream extension only for testing. Use a separate target
        # directory so Python features cannot contaminate the packaged C archive.
        libname = sysconfig.get_config_var("LDLIBRARY")
        soname = sysconfig.get_config_var("INSTSONAME") or libname
        suffix = sysconfig.get_config_var("EXT_SUFFIX")
        if not libname or not suffix:
            raise ConanInvalidConfiguration("Native Python shared-library and extension ABI settings are required")
        # Relocated HNP installations retain the original build-time LIBDIR.
        # Search this interpreter's runtime roots first, including versioned
        # libraries when the unversioned development symlink is not installed.
        executable = Path(sys.executable).resolve()
        roots = (sys.base_prefix, sys.base_exec_prefix, str(executable.parent.parent),
                 sysconfig.get_config_var("base"), sysconfig.get_config_var("platbase"))
        directories = [Path(root) / lib for root in roots if root for lib in ("lib", "lib64")]
        directories += [Path(value) for key in ("LIBDIR", "LIBPL")
                        if (value := sysconfig.get_config_var(key))]
        candidates = list(dict.fromkeys(directory / name for directory in directories
                                        for name in (soname, libname)))
        libpython = next((path for path in candidates if path.is_file()), None)
        self.output.info("Native Python runtime: " + json.dumps({
            "executable": str(executable), "base_prefix": sys.base_prefix,
            "configured_libdir": sysconfig.get_config_var("LIBDIR"),
            "library": str(libpython) if libpython else None}))
        if libpython is None:
            raise ConanInvalidConfiguration("Native Python shared library is missing; checked: " +
                                            ", ".join(map(str, candidates)))
        # E212: HNP Python cannot dlopen an extension under the Conan user cache.
        # Run the same interpreter and libpython from signed build-private copies.
        # Never alter the installed interpreter, libraries, or security policy.
        runtime = Path(self.build_folder) / "python-runtime"
        python = runtime / "bin/python3"
        private_libpython = runtime / "lib" / soname
        sign_tool = shutil.which("binary-sign-tool")
        self._sign_copy(executable, python, sign_tool)
        self._sign_copy(libpython, private_libpython, sign_tool)
        target = Path(self.build_folder) / "python-target"
        python_path = Path(self.build_folder) / "python-test"
        package = python_path / "crunch64"
        copy(self, "*.py", src=os.path.join(self.source_folder, "lib/crunch64"), dst=str(package))
        env = Environment()
        clear_keys = ("PYO3_CONFIG_FILE", "PYO3_CROSS", "PYO3_NO_PYTHON", "PYO3_PRINT_CONFIG",
                      "PYO3_CROSS_LIB_DIR", "PYO3_CROSS_PYTHON_VERSION", "PYO3_CROSS_PYTHON_IMPLEMENTATION")
        env.define("PYO3_PYTHON", str(python))
        env.define("PYTHONHOME", sys.base_prefix)
        env.prepend_path("LD_LIBRARY_PATH", str(private_libpython.parent))
        env.define("PYTHONPATH", str(python_path))
        env.define("PYTHONNOUSERSITE", "1")
        env.define("PYTHONDONTWRITEBYTECODE", "1")
        env.define("PYTHONOPTIMIZE", "0")
        # OHOS does not resolve these symbols from the interpreter implicitly.
        # Link the test-only extension to this interpreter's actual libpython.
        command = [cargo, "rustc", "--locked", "-p", "crunch64", "--lib",
                   "--features", "python_bindings", "--crate-type", "cdylib",
                   "--target-dir", str(target)] + mode + [
                       "--", "-C", "link-arg=" + str(private_libpython),
                       "-C", "link-arg=-Wl,-rpath," + str(private_libpython.parent)]
        with env.vars(self, scope=None).apply():
            # Conan EnvVars.apply() represents unset values as empty strings;
            # PyO3 treats an empty PYO3_CONFIG_FILE as a real (invalid) path.
            # Remove the keys; apply() restores the complete environment on exit.
            for key in clear_keys:
                os.environ.pop(key, None)
            self._logged_run(command, "upstream-python-build.log")
            profile = "release" if mode else "debug"
            extension = package / ("crunch64" + suffix)
            if extension.exists():
                extension.unlink()
            self._sign_copy(target / profile / "libcrunch64.so", extension, sign_tool)
            # Reject an unrelated preinstalled module even if it has the same version.
            probe = ("import pathlib,sys,crunch64,crunch64.crunch64 as native; "
                     "assert crunch64.__version__ == '0.6.2'; "
                     "assert pathlib.Path(native.__file__).resolve() == pathlib.Path(sys.argv[1]).resolve(); "
                     "assert pathlib.Path(sys.executable).resolve() == pathlib.Path(sys.argv[2]).resolve(); "
                     "assert sys.version == sys.argv[4], 'Private Python runtime version mismatch'; "
                     # HMDFS exposes a different physical prefix in /proc/self/maps.
                     "lib_suffix = '/' + '/'.join(pathlib.Path(sys.argv[3]).parts[-6:]); "
                     "assert any(line.rstrip().endswith(lib_suffix) "
                     "for line in pathlib.Path('/proc/self/maps').read_text().splitlines()); "
                     "print('Verified private Python:', sys.executable); "
                     "print('Verified upstream Python extension:', native.__file__)")
            self._logged_run([str(python), "-s", "-c", probe, str(extension), str(python), str(private_libpython),
                              sys.version],
                             "upstream-python-import.log")
            output = self._logged_run([str(python), "-s", str(Path(self.source_folder) / "python_bindings/tests.py")],
                                      "upstream-python.log")
        comparisons = output.count("Validating:")
        if comparisons != 97 or "All tests passed" not in output:
            raise ConanException("Expected all 97 unmodified upstream Python fixture comparisons")
        return comparisons

    def build(self):
        apply_conandata_patches(self)
        cargo = self._rust_environment()
        mode = ["--release"] if str(self.settings.build_type) == "Release" else []
        self.run(shlex.join([cargo, "rustc", "--locked", "-p", "crunch64", "--lib",
                             "--features", "std,c_bindings", "--crate-type", "staticlib"] + mode),
                 cwd=self.source_folder, env=["conanbuild", "crunch64_rust"])
        # Tests are mandatory; --all-targets avoids rustdoc and includes the CLI's
        # test target. No upstream source or fixture is edited or excluded.
        command = [cargo, "test", "--locked", "--workspace", "--all-targets", "--features", "std,c_bindings"] + mode
        output = self._logged_run(command, "upstream-rust.log")
        results = re.findall(r"test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;", output)
        passed = sum(int(p) for p, _, _ in results)
        if passed != 161 or any(int(f) or int(i) for _, f, i in results):
            raise ConanException("Expected all 161 registered upstream Rust tests, with no failures or skips")
        executable = str(Path(self.build_folder) / "upstream-c-tests")
        self.run(shlex.join([self._cc(), "-std=c11", "-O2", "-Wall", "-Wextra", "-Wshadow", "-Werror",
                             "-I" + str(Path(self.source_folder) / "c_bindings/include"),
                             str(Path(self.source_folder) / "c_bindings/tests.c"), str(self._archive()),
                             "-lpthread", "-ldl", "-lm", "-o", executable]), env="conanbuild")
        c_output = self._logged_run([executable], "upstream-c.log")
        comparisons = c_output.count("validating data:")
        if comparisons != 97 or "All tests passed" not in c_output:
            raise ConanException("Expected all 97 upstream C fixture comparisons")
        python_comparisons = self._test_python_bindings(cargo, mode)
        total = passed + comparisons + python_comparisons
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "passed", "framework": "cargo-test + upstream C/Python fixtures",
            "command": shlex.join(command) + "; upstream-c-tests; python_bindings/tests.py", "discovered": total,
            "executed": total, "passed": total, "failed": 0, "skipped": 0}))

    def _archive(self):
        mode = "release" if str(self.settings.build_type) == "Release" else "debug"
        return Path(self.build_folder) / "target" / mode / "libcrunch64.a"

    def package(self):
        if not self._archive().is_file():
            raise ConanException("Missing libcrunch64.a")
        copy(self, "libcrunch64.a", src=str(self._archive().parent), dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "c_bindings/include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["crunch64"]
        self.cpp_info.system_libs = ["pthread", "dl", "m"]
        self.cpp_info.set_property("cmake_file_name", "crunch64")
        self.cpp_info.set_property("cmake_target_name", "crunch64::crunch64")
        self.cpp_info.set_property("pkg_config_name", "crunch64")
