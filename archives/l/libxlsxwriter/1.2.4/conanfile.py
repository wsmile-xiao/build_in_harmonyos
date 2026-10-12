#!/usr/bin/env python3
"""Conan recipe — libxlsxwriter 1.2.4 (cmake).

libxlsxwriter is a C library for creating Excel XLSX files. It needs zlib
(system dep, conan-provided) and vendors everything else it uses (minizip
ioapi/zip only, tmpfileplus, md5) statically into the library by default
(USE_SYSTEM_MINIZIP=OFF etc.).

Upstream tests, run for real during build():
  * unit      — test/unit: ctest.h framework, one binary (xlsxwriter_unit)
                aggregating 451 CTEST(suite, name) cases across 159 test*.c
                files. Run via a bash wrapper (OHOS mksh cannot exec the
                cross-built ELF directly).
  * functional — test/functional: 793 C executables each writing an .xlsx
                that is compared byte-for-byte (XML element-wise) against
                the checked-in golden files (test/functional/xlsx_files/,
                747 files) by the python unittest/pytest suite (799 test
                functions in 84 files). Requires python3+pytest on the
                build host — the comparison harness is pure-python
                (zipfile + re), the *executables under test* are OHOS
                aarch64 ELF run through the same bash wrapper.

The functional harness compares "got" vs "expected" by extracting the XML
elements of each file inside the zip archives, so it is a real golden-file
verification of the library output on OHOS.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get


class LibxlsxwriterConan(ConanFile):
    name = "libxlsxwriter"
    version = "1.2.4"
    description = "C library for creating Excel XLSX files"
    license = "BSD-2-Clause"
    homepage = "https://libxlsxwriter.github.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/*"

    def requirements(self):
        self.requires("zlib/1.3.1.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # OHOS cross helpers (libzip 1.11.4 playbook, proven on this repo)
    # ------------------------------------------------------------------
    def _ohos_toolchain(self):
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _llvm_ranlib(self, toolchain):
        sdk_bin = os.path.normpath(os.path.join(toolchain, "..", "..", "..", "llvm", "bin"))
        cand = os.path.join(sdk_bin, "llvm-ranlib")
        if os.path.isfile(cand):
            return ""
        return shutil.which("llvm-ranlib") or ""

    def _find_deps_preload(self):
        deps = [d.package_folder for _r, d in self.dependencies.items() if d.package_folder]
        if not deps:
            return ""
        path = os.path.join(self.build_folder, "ohos-find-deps.cmake")
        with open(path, "w", encoding="utf-8") as f:
            for d in deps:
                p = d.replace("\\", "/")
                f.write('list(APPEND CMAKE_FIND_ROOT_PATH "%s")\n' % p)
                f.write('list(APPEND CMAKE_PREFIX_PATH "%s")\n' % p)
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)\n")
        return path

    def _zlib_cache_defs(self):
        # upstream uses module-mode find_package(ZLIB 1.2.8 REQUIRED)
        # (FindZLIB.cmake), so pre-seed the cache variables with the conan
        # dependency's real paths to defeat FIND_ROOT_PATH=ONLY.
        z = self.dependencies["zlib"]
        zroot = z.package_folder.replace("\\", "/")
        libs = []
        for ld in z.cpp_info.libdirs:
            for pattern in ("libz.a", "libz.so*", "zlib.lib"):
                libs += sorted(glob.glob(os.path.join(ld, pattern)))
        zlib_lib = libs[0].replace("\\", "/") if libs else ""
        defs = []
        incs = z.cpp_info.includedirs
        if incs:
            defs.append('-DZLIB_INCLUDE_DIR="{}"'.format(incs[0].replace("\\", "/")))
        if zlib_lib:
            defs.append('-DZLIB_LIBRARY="{}"'.format(zlib_lib))
        defs.append('-DZLIB_ROOT="{}"'.format(zroot))
        return defs

    def _bash(self):
        return os.environ.get("CONFIG_SHELL") or next(
            (p for p in ("/data/service/hnp/bin/bash", "/bin/bash") if os.path.exists(p)),
            "bash")


    # ------------------------------------------------------------------
    def _run_functional_suite(self, bdir, bash):
        """Run the upstream functional suite: 793 C executables, each
        writing an .xlsx that the python harness compares element-wise
        against the checked-in golden files (747 .xlsx).

        The executables are OHOS ELF: os.system() inside the python
        harness uses /bin/sh (mksh) which cannot exec them, so we swap
        each executable for a bash shim that forwards to the real ELF.
        The python comparison side (zipfile + re) is pure-python and
        runs on the build host."""
        import shutil as _sh
        import subprocess
        fsrc = os.path.join(bdir, "test", "functional", "src")
        if not os.path.isdir(fsrc):
            raise Exception("functional src dir missing: %s" % fsrc)
        exes = sorted(e for e in os.listdir(fsrc)
                      if e.startswith("test_") and not e.endswith((".c", ".o", ".xlsx", ".elf", ".py")))
        if not exes:
            raise Exception("no functional executables found in %s" % fsrc)
        store = os.path.join(bdir, "test", "functional", "elf-store")
        os.makedirs(store, exist_ok=True)
        shimmed = 0
        for e in exes:
            p = os.path.join(fsrc, e)
            if os.path.isfile(p) and self._is_elf(p):
                _sh.move(p, os.path.join(store, e + ".elf"))
                with open(p, "w") as f:
                    f.write("#!%s\n" % bash)
                    f.write('exec "%s" "$@"\n' % os.path.join(store, e + ".elf"))
                os.chmod(p, 0o755)
                shimmed += 1
        self.output.info("functional executables: %d (%d bash-shimmed)" % (len(exes), shimmed))

        # 驱动器选择：优先 pytest（上游 add_test 口径）；构建机无 pytest 时
        # 回退 unittest discover（上游测试继承 unittest.TestCase，语义等价）。
        # 解释器用 sys.executable（配方进程自身 python）：CI worker 的 conanbuild
        # PATH 里可能没有 python3（FileNotFoundError 实证）。
        import sys as _sys
        import subprocess as _sp
        py = _sys.executable or "python3"
        has_pytest = _sp.run([py, "-c", "import pytest"], capture_output=True).returncode == 0
        if has_pytest:
            cmd = [py, "-m", "pytest", "test/functional", "-q", "--tb=short"]
        else:
            self.output.info("pytest unavailable on build host; falling back to unittest discovery")
            # 5 个测试文件顶层 import pytest（仅用 @pytest.mark.skipif 装饰器）。
            # unittest 回退路径下往 build 目录副本注入最小 stub（不改上游源码）。
            fdir = os.path.join(bdir, "test", "functional")
            # 直接改写 5 个测试文件的 import 行（最可靠——PYTHONPATH/stub
            # 在 CI 的 conanbuild 环境均被剥离或不入 sys.path，_FailedTest
            # 实锤两轮）：import pytest → 内联最小 mark 兼容层。
            import re as _re
            patched = 0
            for fn in os.listdir(fdir):
                if not (fn.startswith("test_") and fn.endswith(".py")):
                    continue
                fp = os.path.join(fdir, fn)
                with open(fp, "r") as f:
                    content = f.read()
                if "import pytest" in content:
                    content = content.replace(
                        "import pytest",
                        "# pytest stub inlined (unittest fallback): mark.skipif only\n"
                        "class _SkipIfMark:\n"
                        "    def skipif(self, cond, reason=None):\n"
                        "        def deco(fn):\n"
                        "            if cond:\n"
                        "                import unittest as _u\n"
                        "                def _sk(*a, **kw):\n"
                        "                    raise _u.SkipTest(reason or 'skipped')\n"
                        "                _sk.__name__ = fn.__name__\n"
                        "                return _sk\n"
                        "            return fn\n"
                        "        return deco\n"
                        "class _PytestStub:\n"
                        "    mark = _SkipIfMark()\n"
                        "pytest = _PytestStub()")
                    with open(fp, "w") as f:
                        f.write(content)
                    patched += 1
            self.output.info("inlined pytest stub into %d test files" % patched)
            cmd = [py, "-m", "unittest", "discover", "-s", "test/functional",
                   "-p", "test_*.py", "-v"]
        # CI 上 sys.executable 的 sys.path[0] 不一定是 cwd（_FailedTest
        # ModuleNotFoundError 'pytest' 实证——stub 写了但不在导入搜索路径）：
        # 显式 PYTHONPATH 注入 functional 目录（stub+base_test_class 都在）。
        env = dict(os.environ)
        fdir_abs = os.path.join(bdir, "test", "functional")
        env["PYTHONPATH"] = fdir_abs + (
            os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        # 全量透传输出（不吞 stdout）：CI 日志需展示失败用例明细
        r = subprocess.run(cmd, cwd=bdir, env=env, timeout=5400)
        if r.returncode != 0:
            raise Exception("libxlsxwriter functional tests failed (rc=%d)" % r.returncode)
        self.output.info("functional suite: PASSED")


    # ------------------------------------------------------------------
    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        src = self.source_folder
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder),
            "-DBUILD_SHARED_LIBS=OFF",
            "-DBUILD_EXAMPLES=OFF",
            "-DBUILD_FUZZERS=OFF",
            "-DBUILD_TESTS=ON",
            # OHOS toolchain 注入 -Wl,--gc-sections 会回收 ctest.h 测试注册段 .ctest
            # （static struct 无引用）→ unit 二进制只剩 sentinel、0 tests 注册。
            # 用 --no-gc-sections 覆盖（lld 后出现的 flag 生效），保住 .ctest 段。
            '-DCMAKE_EXE_LINKER_FLAGS="-Wl,--no-gc-sections"',
            "-DUSE_SYSTEM_MINIZIP=OFF",
            "-DUSE_STANDARD_TMPFILE=OFF",
            "-DUSE_NO_MD5=OFF",
            "-DIOAPI_NO_64=OFF",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        ]
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs.append('-DCMAKE_RANLIB="{}"'.format(_rl))
        _pre = self._find_deps_preload()
        if _pre:
            defs.append('-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="{}"'.format(_pre))
        defs += self._zlib_cache_defs()
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}" -- -j2'.format(bdir))

        self._run_upstream_tests(bdir)

    # ------------------------------------------------------------------
    def _run_upstream_tests(self, bdir):
        bash = self._bash()
        # --- 1) unit test binary (451 CTEST cases) ------------------
        unit_bin = os.path.join(bdir, "xlsxwriter_unit")
        if not os.path.isfile(unit_bin):
            raise Exception("unit test binary missing: %s" % unit_bin)
        # ctest.h test runner writes a test.log next to the binary and uses
        # /tmp paths only through tmpfileplus (respects TMPDIR), so run it
        # from the build dir. The binary is an OHOS ELF: exec via bash.
        ret = self.run('"%s" -c "cd %s && ./%s"' % (bash, bdir, os.path.basename(unit_bin)),
                       env="conanbuild", ignore_errors=True)
        if ret != 0:
            raise Exception("libxlsxwriter unit tests failed (rc=%d)" % ret)
        self.output.info("upstream unit tests (451 CTEST cases): PASSED")

        # --- 2) functional suite (793 exes x pytest golden compare) ----
        self._run_functional_suite(bdir, bash)

    # ------------------------------------------------------------------
    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        copy(self, "License.txt", src=self.source_folder, dst="licenses", keep_path=False)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # Static lib only by default: no .so/bin artifacts to sign, but keep
        # the machinery for shared builds (XPM requires signed ELF on OHOS).
        import glob as _g
        targets = _g.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += _g.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["xlsxwriter"]
        self.cpp_info.set_property("cmake_file_name", "xlsxwriter")
        self.cpp_info.set_property("cmake_target_name", "xlsxwriter::xlsxwriter")
        self.cpp_info.set_property("pkg_config_name", "xlsxwriter")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
