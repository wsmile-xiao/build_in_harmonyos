import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv

required_conan_version = ">=2.0"


class SysrepoTest(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # Same E092 mapping as the main recipe: the consumer build configures
        # with the same OHOS profile and would hit the missing
        # Platform/HarmonyOS CMake module without it.
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()
        # conanrun env: LD_LIBRARY_PATH across every dependency libdir so the
        # musl loader resolves libsysrepo.so.7 (and libyang.so.3) at test
        # time; the build-tree consumer binary carries no RPATH.
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._sign_ohos_elf(self._find_consumer_bin("test_sysrepo"))
        ctest_dir = self._ctest_dir()
        # sysrepo enumerates its SHM directory at connect time; on OHOS
        # /dev/shm is a write-only virtual directory (opendir -> EACCES), so
        # point SYSREPO_SHM_DIR at a private, listable directory instead.
        shm_dir = os.path.join(ctest_dir, "sysrepo-shm")
        os.makedirs(shm_dir, exist_ok=True)
        # Internal YANG modules come from the baked YANG_MODULE_PATH
        # directory (see the main recipe); only a private repository and SHM
        # directory are needed here.
        shm_dir = os.path.join(ctest_dir, "sysrepo-shm")
        os.makedirs(shm_dir, exist_ok=True)
        repo_dir = os.path.join(ctest_dir, "sysrepo-repo")
        shutil.rmtree(repo_dir, ignore_errors=True)
        os.makedirs(repo_dir, exist_ok=True)
        loader_env = Environment()
        loader_env.define("SYSREPO_SHM_DIR", shm_dir)
        loader_env.define("SYSREPO_REPOSITORY_PATH", repo_dir)
        # Run ctest through self.run(env=None): the applied runtime env
        # (LD_LIBRARY_PATH, SYSREPO_*) is inherited from os.environ, while a
        # conanbuild-wrapped run would drop it before the musl loader sees
        # it (same as archives/l/libyang/3.13.6).
        with VirtualRunEnv(self).vars().apply(), loader_env.vars(self).apply():
            self.run(
                "ctest --output-on-failure --no-tests=error",
                cwd=ctest_dir,
                env=None,
            )

    def _ctest_dir(self):
        # Do not assume cmake_layout binary dir == self.build_folder: locate
        # the dir owning CTestTestfile.cmake that actually registers tests
        # (same drift class as archives/l/libyang/3.13.6).
        base = self.build_folder or "."
        try:
            for dirpath, _, filenames in os.walk(base):
                if "CTestTestfile.cmake" not in filenames:
                    continue
                with open(
                    os.path.join(dirpath, "CTestTestfile.cmake"),
                    encoding="utf-8",
                    errors="replace",
                ) as fh:
                    if "add_test" in fh.read():
                        return dirpath
        except OSError:
            pass
        return base

    def _find_consumer_bin(self, name):
        primary = os.path.join(self.cpp.build.bindir, name)
        if os.path.isfile(primary):
            return primary
        # Layout-agnostic fallback: search the whole build tree.
        base = self.build_folder or "."
        try:
            for dirpath, _, filenames in os.walk(base):
                if name in filenames:
                    candidate = os.path.join(dirpath, name)
                    if os.path.isfile(candidate):
                        return candidate
        except OSError:
            pass
        return primary

    def _sign_ohos_elf(self, path):
        # OHOS requires a .codesign section for executed ELF binaries (same
        # hardening as archives/l/libyang/3.13.6/test_package).
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = f"{path}.signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed consumer has invalid .codesign: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)
