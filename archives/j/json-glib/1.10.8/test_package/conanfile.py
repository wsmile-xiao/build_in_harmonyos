import os
import filecmp
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps


class JsonGlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        if not pkg_config:
            raise ConanInvalidConfiguration("pkg-config is required")

        pkg_env = os.environ.copy()
        existing_path = pkg_env.get("PKG_CONFIG_PATH")
        pkg_env["PKG_CONFIG_PATH"] = os.pathsep.join(
            value for value in (self.generators_folder, existing_path) if value
        )
        query = subprocess.run(
            [pkg_config, "--cflags", "--libs", "json-glib-1.0"],
            env=pkg_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if query.returncode:
            raise ConanException(
                "pkg-config failed for json-glib-1.0: " + query.stderr.strip()
            )

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c")
        if not cc or not os.path.isfile(cc):
            raise ConanInvalidConfiguration(
                "C compiler missing from tools.build:compiler_executables"
            )
        sysroot = self.conf.get("tools.build:sysroot")
        if cross_building(self) and not sysroot:
            raise ConanInvalidConfiguration("tools.build:sysroot is required")

        output = self._consumer_executable(require_exists=False)
        os.makedirs(os.path.dirname(output), exist_ok=True)
        command = [cc]
        command.extend(
            self.conf.get("tools.build:cflags", default=[], check_type=list)
        )
        if sysroot:
            command.append(f"--sysroot={sysroot}")
        command.extend(
            [os.path.join(self.source_folder, "test_json_glib.c"), "-o", output]
        )
        command.extend(shlex.split(query.stdout, posix=True))
        command.extend(
            self.conf.get("tools.build:exelinkflags", default=[], check_type=list)
        )
        if str(self.settings.os) == "OHOS" and can_run(self):
            runtime_dirs = self._runtime_library_paths()
            runtime_dir = self._stage_runtime_libraries(output, runtime_dirs)
            if not runtime_dir:
                raise ConanInvalidConfiguration(
                    "consumer runtime library closure is empty"
                )
            # Keep a loader-visible, origin-relative copy beside the consumer;
            # the absolute cache path remains a host-side fallback/readback.
            runtime_rpath = f"$ORIGIN/runtime:{runtime_dir}"
            command.append(
                f"-Wl,--disable-new-dtags,-rpath,{runtime_rpath}"
            )
        self.output.info(
            "Consumer compile command: " + subprocess.list2cmdline(command)
        )
        compile_result = subprocess.run(
            command,
            env=self._host_tool_environment(cc),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if compile_result.stdout:
            self.output.info(compile_result.stdout.rstrip())
        if compile_result.stderr:
            self.output.info(compile_result.stderr.rstrip())
        if compile_result.returncode:
            raise ConanException(
                f"consumer compile failed with RC {compile_result.returncode}"
            )
        if str(self.settings.os) == "OHOS" and can_run(self):
            readelf = os.path.join(os.path.dirname(cc), "llvm-readelf")
            if not os.path.isfile(readelf):
                raise ConanInvalidConfiguration(
                    f"llvm-readelf is missing: {readelf}"
                )
            dynamic = subprocess.run(
                [readelf, "-d", output],
                env=self._host_tool_environment(readelf),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if dynamic.returncode:
                raise ConanException(
                    "consumer dynamic-section readback failed: "
                    + dynamic.stderr.strip()
                )
            rpath_lines = [
                line.strip() for line in dynamic.stdout.splitlines()
                if "(RPATH)" in line
            ]
            needed_lines = [
                line.strip() for line in dynamic.stdout.splitlines()
                if "(NEEDED)" in line
            ]
            if (
                len(rpath_lines) != 1
                or "(RUNPATH)" in dynamic.stdout
                or "$ORIGIN/runtime" not in rpath_lines[0]
                or runtime_dir not in rpath_lines[0]
                or not any(
                    "libjson-glib-1.0.so.0" in line for line in needed_lines
                )
            ):
                raise ConanInvalidConfiguration(
                    "consumer DT_RPATH/DT_NEEDED do not bind the runtime library closure"
                )
            self.output.info("JSON_GLIB_CONSUMER_RPATH=" + rpath_lines[0])

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile and link consumer passed")
            return

        executable = self._consumer_executable()
        runtime_paths = self._runtime_library_paths()
        # Re-stage at the execution boundary because Conan may recreate the
        # test build folder between build() and test().
        staged_runtime_dir = self._stage_runtime_libraries(
            executable, runtime_paths
        )
        if not staged_runtime_dir:
            raise ConanInvalidConfiguration(
                "consumer runtime library closure is empty"
            )
        runtime_paths = [staged_runtime_dir] + runtime_paths
        runtime_path = os.pathsep.join(runtime_paths)
        self.output.info("JSON_GLIB_RUNTIME_PATHS=" + runtime_path)
        for name in os.listdir(staged_runtime_dir):
            target = os.path.join(staged_runtime_dir, name)
            if os.path.isfile(target) and not os.path.islink(target):
                self._sign_elf(target)
                if str(self.settings.os) == "OHOS":
                    os.chmod(target, os.stat(target).st_mode | 0o111)
        self._sign_elf(executable)
        os.chmod(executable, 0o755)
        command = f'"{executable}"'
        if runtime_path and str(self.settings.os) in ("Linux", "OHOS"):
            command = (
                f"export LD_LIBRARY_PATH={shlex.quote(runtime_path)}"
                f" && {command}"
            )
        self.run(command, env="conanrun")

    def _host_tool_environment(self, executable):
        env = os.environ.copy()
        if str(self.settings.os) != "OHOS":
            return env

        tool_dir = os.path.dirname(os.path.abspath(executable))
        sdk_dirs = []
        for dirname in ("lib", "lib64"):
            candidate = os.path.abspath(os.path.join(tool_dir, os.pardir, dirname))
            if os.path.isdir(candidate):
                sdk_dirs.append(candidate)
        if sdk_dirs:
            existing = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                sdk_dirs + ([existing] if existing else [])
            )
        return env

    def _sign_elf(self, path):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 与被 exec 的可执行文件都带代码签名（E2176）。
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            return
        if self._elf_has_codesign(path, objcopy):
            self.run('{oc} --remove-section .codesign "{f}"'.format(oc=objcopy, f=path))
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=path))

    def _elf_has_codesign(self, path, objcopy):
        readelf = os.path.join(os.path.dirname(objcopy), "llvm-readelf")
        result = None
        if os.path.isfile(readelf):
            result = subprocess.run(
                [readelf, "-S", path],
                env=self._host_tool_environment(readelf),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        if result is not None and result.returncode == 0:
            return any(".codesign" in line for line in result.stdout.splitlines())
        with open(path, "rb") as handle:
            return b".codesign\x00" in handle.read()

    def _stage_runtime_libraries(self, output, runtime_dirs):
        if not runtime_dirs:
            return ""

        runtime_dir = os.path.join(os.path.dirname(output), "runtime")
        os.makedirs(runtime_dir, exist_ok=True)
        staged = []
        for libdir in runtime_dirs:
            for name in os.listdir(libdir):
                if ".so" not in name:
                    continue
                source = os.path.join(libdir, name)
                if not os.path.isfile(source):
                    continue
                target = os.path.join(runtime_dir, name)
                source_is_link = os.path.islink(source)
                source_target = os.path.realpath(source) if source_is_link else None
                if source_is_link and not os.path.isfile(source_target):
                    raise ConanInvalidConfiguration(
                        f"runtime library alias target is missing: {name}"
                    )
                if os.path.lexists(target):
                    if source_is_link:
                        matches = (
                            os.path.islink(target)
                            and os.path.realpath(target)
                            == os.path.join(
                                runtime_dir, os.path.basename(source_target)
                            )
                        )
                    else:
                        matches = (
                            os.path.isfile(target)
                            and not os.path.islink(target)
                            and filecmp.cmp(source, target, shallow=False)
                        )
                    if not matches:
                        raise ConanInvalidConfiguration(
                            f"runtime library collision: {name}"
                        )
                    staged.append(name)
                    continue
                if source_is_link:
                    try:
                        os.symlink(os.path.basename(source_target), target)
                    except OSError as exc:
                        raise ConanInvalidConfiguration(
                            f"cannot preserve runtime library alias: {name}"
                        ) from exc
                else:
                    shutil.copyfile(source, target)
                    shutil.copymode(source, target)
                staged.append(name)

        invalid = []
        for name in sorted(set(staged)):
            target = os.path.join(runtime_dir, name)
            if str(self.settings.os) == "OHOS" and not os.path.islink(target):
                os.chmod(target, os.stat(target).st_mode | 0o111)
            mode = os.stat(target).st_mode
            valid = (
                os.path.isfile(target)
                and os.path.getsize(target) > 0
                and bool(mode & 0o444)
                and (
                    str(self.settings.os) != "OHOS"
                    or bool(mode & 0o111)
                )
            )
            if os.path.islink(target):
                valid = valid and os.path.dirname(os.path.realpath(target)) == runtime_dir
            if not valid:
                invalid.append(name)
        if invalid:
            raise ConanInvalidConfiguration(
                "staged runtime libraries are not valid loader entries: "
                + ",".join(invalid)
            )
        self.output.info(
            "JSON_GLIB_STAGED_RUNTIME_METHOD="
            + "preserved-loader-alias"
        )
        self.output.info(
            "JSON_GLIB_STAGED_RUNTIME="
            + ",".join(
                f"{name}:{os.path.getsize(os.path.join(runtime_dir, name))}"
                for name in sorted(set(staged))
            )
        )
        if not any(
            name.startswith("libjson-glib-1.0.so") for name in set(staged)
        ):
            raise ConanInvalidConfiguration(
                "staged runtime library closure is missing libjson-glib-1.0.so"
            )
        return runtime_dir
    def _runtime_library_paths(self):
        tested = self.dependencies[self.tested_reference_str]
        dependency_items = [(None, tested)]
        dependency_items.extend(
            (requirement, dependency)
            for requirement, dependency in self.dependencies.items()
            if dependency is not tested
        )
        paths = []
        seen = set()
        for requirement, dependency in dependency_items:
            if requirement is not None and (requirement.build or requirement.test):
                continue
            package_folder = dependency.package_folder
            if not package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs or []:
                libdir = os.fspath(libdir)
                if not os.path.isabs(libdir):
                    libdir = os.path.join(package_folder, libdir)
                libdir = os.path.abspath(libdir)
                if not os.path.isdir(libdir):
                    continue
                identity = os.path.normcase(os.path.normpath(libdir))
                if identity in seen:
                    continue
                seen.add(identity)
                paths.append(libdir)
        return paths

    def _consumer_executable(self, require_exists=True):
        build_folder = os.path.realpath(self.build_folder)
        bindir = self.cpp.build.bindirs[0]
        if not os.path.isabs(bindir):
            bindir = os.path.join(build_folder, bindir)
        executable_name = (
            "test_json_glib.exe"
            if self.settings.os == "Windows"
            else "test_json_glib"
        )
        executable = os.path.realpath(os.path.join(bindir, executable_name))
        if os.path.commonpath((build_folder, executable)) != build_folder:
            raise ConanInvalidConfiguration(
                "consumer executable resolves outside the Conan build folder"
            )
        if require_exists and not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                f"consumer executable is missing: {executable}"
            )
        return executable
