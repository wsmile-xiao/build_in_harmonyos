#!/usr/bin/env python3
"""Conan recipe for Rakudo 2025.11 on HarmonyOS PC."""

import os
import stat
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
    save,
)
from conan.tools.layout import basic_layout


class RakudoConan(ConanFile):
    name = "rakudo"
    version = "2025.11"
    description = "Rakudo compiler for the Raku programming language"
    license = "Artistic-2.0"
    homepage = "https://rakudo.org/"
    url = "https://github.com/rakudo/rakudo"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("moarvm/2025.11", run=True)
        self.requires("nqp/2025.11", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _stage_folder(self):
        return os.path.join(self.build_folder, "rakudo-stage")

    def _sdk_tool_env(self):
        if self.settings.os != "OHOS":
            return ""
        sdk_llvm_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/lib"
        )
        return f'LD_LIBRARY_PATH="{sdk_llvm_lib}:$LD_LIBRARY_PATH" '

    def _make_stage_writable(self, stage):
        for root, directories, files in os.walk(stage):
            for path in [root, *(
                os.path.join(root, name) for name in (*directories, *files)
            )]:
                try:
                    mode = os.stat(path).st_mode
                    os.chmod(path, mode | stat.S_IWUSR | stat.S_IWGRP)
                except OSError:
                    pass

    def _normalize_package_permissions(self, package_folder):
        for root, directories, files in os.walk(package_folder):
            for name in directories:
                path = os.path.join(root, name)
                if not os.path.islink(path):
                    os.chmod(path, 0o755)
            for name in files:
                path = os.path.join(root, name)
                if not os.path.islink(path):
                    mode = os.stat(path).st_mode
                    os.chmod(path, 0o755 if mode & stat.S_IXUSR else 0o644)

    def _moar_make_args(self):
        moar = self.dependencies["moarvm"].package_folder
        include_root = os.path.join(moar, "include")
        include_dirs = [
            include_root,
            *(
                os.path.join(include_root, name)
                for name in ("moar", "libuv", "libtommath", "dyncall", "mimalloc")
            ),
        ]
        include_flags = " ".join(f'-I"{path}"' for path in include_dirs)
        library_flags = f'-L"{os.path.join(moar, "lib")}"'
        return (
            f'M_MOAR_INC_PATHS="{include_flags}" '
            f'M_LDFLAGS="{library_flags}" '
            'M_LDLIBS="-lmoar"'
        )

    def build(self):
        apply_conandata_patches(self)
        stage = self._stage_folder()
        for dependency in ("moarvm", "nqp"):
            copy(
                self,
                "*",
                src=self.dependencies[dependency].package_folder,
                dst=stage,
            )
        self._make_stage_writable(stage)
        nqp = os.path.join(stage, "bin", "nqp")
        real_nqp = os.path.join(stage, "bin", "nqp-real")
        os.replace(nqp, real_nqp)
        overrides = {
            "moar::prefix": stage,
            "moar::bindir": os.path.join(stage, "bin"),
            "moar::libdir": os.path.join(stage, "lib"),
            "moar::mastdir": os.path.join(stage, "share", "nqp", "lib", "MAST"),
            "nqp::prefix": stage,
            "nqp::libdir": os.path.join(stage, "share", "nqp", "lib"),
        }
        save(
            self,
            nqp,
            "#!/usr/bin/env python3\n"
            "import os, subprocess, sys\n"
            f"REAL_NQP = {real_nqp!r}\n"
            f"OVERRIDES = {overrides!r}\n"
            "if '--show-config' in sys.argv[1:]:\n"
            "    result = subprocess.run([REAL_NQP, *sys.argv[1:]], check=True, "
            "text=True, capture_output=True)\n"
            "    for line in result.stdout.splitlines():\n"
            "        key, separator, value = line.partition('=')\n"
            "        print(f'{key}={OVERRIDES.get(key, value)}' if separator else line)\n"
            "else:\n"
            "    os.execv(REAL_NQP, [REAL_NQP, *sys.argv[1:]])\n",
        )
        os.chmod(nqp, 0o755)
        self.run(
            "perl Configure.pl --backends=moar --relocatable "
            f'--prefix="{stage}" --with-nqp="{nqp}"',
            cwd=self.source_folder,
            env=["conanbuild", "conanrun"],
        )
        os.replace(real_nqp, nqp)
        make_args = self._moar_make_args()
        tool_env = self._sdk_tool_env()
        self.run(
            f"{tool_env}MVM_JIT_DISABLE=1 make -j1 {make_args}",
            cwd=self.source_folder,
            env=["conanbuild", "conanrun"],
        )
        if self.settings.os == "OHOS":
            install_parent = "/data/storage/el2/base/cache"
        else:
            install_parent = os.environ.get("TMPDIR", tempfile.gettempdir())
        os.makedirs(install_parent, exist_ok=True)
        install_root = tempfile.mkdtemp(prefix="rakudo-install-", dir=install_parent)
        self.run(
            f'{tool_env}MVM_JIT_DISABLE=1 make install DESTDIR="{install_root}" {make_args}',
            cwd=self.source_folder,
            env=["conanbuild", "conanrun"],
        )
        installed_stage = os.path.join(install_root, stage.lstrip(os.sep))
        copy(self, "*", src=installed_stage, dst=stage)
        self._make_stage_writable(stage)
        core_repository = os.path.join(stage, "share", "perl6", "core")
        moar_bin = os.path.join(self.dependencies["moarvm"].package_folder, "bin")
        self.run(
            f'{tool_env}MVM_JIT_DISABLE=1 make m-all {make_args}',
            cwd=self.source_folder,
            env=["conanbuild", "conanrun"],
        )
        test_root = tempfile.mkdtemp(prefix="rakudo-test-", dir=install_parent)
        copy(self, "*", src=self.source_folder, dst=test_root)
        build_runner = os.path.join(test_root, "rakudo-m")
        test_bin = os.path.join(test_root, "bin")
        os.makedirs(test_bin, exist_ok=True)
        os.replace(build_runner, build_runner + "-build")
        installed_runner = os.path.join(stage, "bin", "rakudo-m")
        copy(self, "rakudo-m", src=os.path.dirname(installed_runner), dst=test_bin)
        os.symlink(os.path.join(test_bin, "rakudo-m"), build_runner)
        os.symlink(os.path.join(stage, "share"), os.path.join(test_root, "share"))
        test_moar = os.path.join(test_root, "moar")
        copy(self, "moar", src=moar_bin, dst=test_root)
        os.chmod(test_moar, 0o755)
        test_tools = "/data/service/hnp/bin:" if self.settings.os == "OHOS" else ""
        self.run(
            f'{tool_env}PATH="{test_root}:{moar_bin}:{test_tools}$PATH" '
            f'TMPDIR="{test_root}" '
            f'RAKULIB="inst#{core_repository}" '
            f"MVM_JIT_DISABLE=1 make test {make_args}",
            cwd=test_root,
            env=["conanbuild", "conanrun"],
        )

    def package(self):
        copy(self, "*", src=self._stage_folder(), dst=self.package_folder)
        self._normalize_package_permissions(self.package_folder)
        rmdir(self, os.path.join(self.package_folder, "include"))
        rmdir(self, os.path.join(self.package_folder, "share", "pkgconfig"))
        for pattern in ("*-debug*", "*-gdb*", "*-lldb*", "*-valgrind*"):
            rm(self, pattern, self.package_folder, recursive=True)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.define("MVM_JIT_DISABLE", "1")
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.define("MVM_JIT_DISABLE", "1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Rakudo MoarVM backend supports Linux and OHOS")
        if str(self.settings.arch) not in ("armv8", "x86_64"):
            raise ConanInvalidConfiguration("Rakudo recipe supports armv8 and x86_64")
