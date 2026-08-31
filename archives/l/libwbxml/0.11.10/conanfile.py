#!/usr/bin/env python3
"""Conan recipe — libwbxml 0.11.10 (CMake).

A library and tools to parse, encode and handle WBXML (WAP Binary XML)
documents. Upstream uses CMake; the core library depends only on expat.
The optional upstream unit tests (test/api/, CTest + check framework) are
built and executed in build() when the `check` dependency is available.

OHOS build follows the "self-discover ohos.toolchain + bare cmake" path:
CMakeToolchain under os=OHOS mis-maps CMAKE_SYSTEM_NAME and drops SONAME,
so we invoke cmake directly with the OHOS SDK toolchain file (or the
profile clang when no toolchain file is found — the clang is itself a
complete OHOS toolchain with bundled sysroot + lld + signing).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
import os
import glob
import subprocess

required_conan_version = ">=2.0"


class LibwbxmlConan(ConanFile):
    name = "libwbxml"
    version = "0.11.10"
    package_type = "library"

    description = "Library and tools to parse, encode and handle WBXML documents"
    homepage = "https://github.com/libwbxml/libwbxml"
    license = "LGPL-2.1-or-later"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "unit_test": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "unit_test": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("expat/2.8.2.1")

    def build_requirements(self):
        if self.options.unit_test:
            self.test_requires("check/0.15.2")

    def layout(self):
        from conan.tools.cmake import cmake_layout
        cmake_layout(self, src_folder=".")

    def export_sources(self):
        # Copy patches/ into the recipe export cache (export_sources_folder) so
        # apply_conandata_patches(self) in source() can resolve them at build
        # time. Without this, "conan create" exports conanfile.py + conandata.yml
        # but NOT the patch files, so source() raises FileNotFoundError on
        # "patches/0001-fix-ohos-test-runtime.patch". This must NOT be applied with a
        # manual "git apply" — the patch flows end-to-end through Conan export +
        # apply_conandata_patches. NOTE: export_sources_folder is only available
        # here, NOT in export() (set by _export_source, not _export_recipe).
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ── OHOS toolchain discovery ───────────────────────────────────────
    def _ohos_toolchain(self):
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain",
                           default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        self.output.info("ohos.toolchain.cmake not found, using profile compiler directly")
        return ""

    # ── SDK LLVM lib dir for lld (libxml2.so.16 bootstrap) ───────────
    def _sdk_llvm_lib_dir(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or os.environ.get("CC") or ""
        if cc and os.path.isabs(cc) and os.path.isfile(cc):
            lib_dir = os.path.join(os.path.dirname(os.path.dirname(cc)), "lib")
            if glob.glob(os.path.join(lib_dir, "libxml2.so*")):
                return lib_dir
        for root in ("/storage/Users/currentUser/usr/local", "/data/service/hnp/llvm"):
            if glob.glob(os.path.join(root, "lib", "libxml2.so*")):
                return os.path.join(root, "lib")
        return ""

    def _compiler_env(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        env = dict(os.environ)
        if compilers.get("c"):
            env["CC"] = compilers["c"]
        if compilers.get("cpp"):
            env["CXX"] = compilers["cpp"]
        cc = compilers.get("c") or env.get("CC") or ""
        if cc and os.path.isabs(cc):
            bindir = os.path.dirname(cc)
            for tool, name in (("AR", "llvm-ar"), ("RANLIB", "llvm-ranlib"),
                               ("OBJCOPY", "llvm-objcopy"), ("STRIP", "llvm-strip")):
                p = os.path.join(bindir, name)
                if os.path.isfile(p):
                    env[tool] = p
        llvm_lib = self._sdk_llvm_lib_dir()
        if llvm_lib:
            env["LD_LIBRARY_PATH"] = "{}:{}".format(
                llvm_lib, env.get("LD_LIBRARY_PATH", ""))
        return env

    def _dep_pkg(self, name):
        dep = self.dependencies.get(name)
        return dep.package_folder if dep else ""

    def _which(self, name):
        from shutil import which
        return which(name) or ""

    def build(self):
        # Patches applied once in source(); do not re-apply here — build
        # context has no export_sources_folder so apply_conandata_patches
        # would FileNotFoundError on patches/0001-fix-ohos-test-runtime.patch.
        toolchain = self._ohos_toolchain()
        bdir = os.path.join(self.build_folder, "build-ohos")
        os.makedirs(bdir, exist_ok=True)

        env = self._compiler_env()

        expat_pkg = self._dep_pkg("expat")
        check_pkg = self._dep_pkg("check")

        prefix_path = expat_pkg
        if check_pkg:
            prefix_path = "{};{}".format(expat_pkg, check_pkg)

        defs = [
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_INSTALL_PREFIX={}".format(self.package_folder),
            '-DCMAKE_PREFIX_PATH="{}"'.format(prefix_path),
            "-DBUILD_SHARED_LIBS={}".format("ON" if self.options.shared else "OFF"),
            "-DBUILD_STATIC_LIBS={}".format("OFF" if self.options.shared else "ON"),
            "-DENABLE_INSTALL_DOC=OFF",
            "-DLIB_SUFFIX=",
        ]
        if toolchain:
            defs.insert(0, '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain))
            defs.insert(1, "-DOHOS_ARCH=arm64-v8a")
        else:
            # Profile clang is a complete OHOS toolchain. Without a toolchain
            # file cmake leaves CMAKE_SHARED_LIBRARY_SONAME_C_FLAG empty, so
            # .so gets no DT_SONAME — linked binaries record the full relative
            # path in NEEDED (../src/libwbxml2.so) which musl treats as a
            # path name, not a soname, so LD_LIBRARY_PATH is ignored and
            # every test binary fails to start. Force the flag.
            defs += [
                '-DCMAKE_SHARED_LIBRARY_SONAME_C_FLAG="-Wl,-soname,"',
                '-DCMAKE_SHARED_MODULE_SONAME_C_FLAG="-Wl,-soname,"',
            ]

        # Upstream src/CMakeLists.txt reads classic FindExpat module vars.
        # The conan expat package only ships an imported target (config mode)
        # which does NOT populate those vars — so we set them explicitly.
        if expat_pkg:
            eincl = os.path.join(expat_pkg, "include")
            elib = os.path.join(expat_pkg, "lib")
            elib_so = os.path.join(elib, "libexpat.so")
            defs += [
                '-DEXPAT_INCLUDE_DIR="{}"'.format(eincl),
                '-DEXPAT_LIBRARY="{}"'.format(elib_so),
                '-DEXPAT_INCLUDE_DIRS="{}"'.format(eincl),
                '-DEXPAT_LIBRARY_DIRS="{}"'.format(elib),
                '-DEXPAT_LIBRARIES="expat"',
            ]

        _pc_bin = self._which("pkg-config")
        if _pc_bin:
            defs.append('-DPKG_CONFIG_EXECUTABLE="{}"'.format(_pc_bin))

        if self.options.unit_test and check_pkg:
            defs += ["-DENABLE_UNIT_TEST=ON"]
            cinc = os.path.join(check_pkg, "include")
            clib = os.path.join(check_pkg, "lib")
            defs += [
                '-DCHECK_INCLUDE_DIRS="{}"'.format(cinc),
                '-DCHECK_LIBRARIES="-L{} -lcheck -lm -lrt -lpthread -lsubunit"'.format(clib),
                '-DCHECK_LDFLAGS="-L{} -lcheck -lm -lrt -lpthread -lsubunit"'.format(clib),
            ]
        else:
            defs += ["-DENABLE_UNIT_TEST=OFF"]

        # Rewrite stale .pc files so PKG_CHECK_MODULES resolves to conan paths
        pc_dirs = []
        pc_stage = os.path.join(self.build_folder, "pc-stage")
        os.makedirs(pc_stage, exist_ok=True)
        for _name, _pkg in (("expat", expat_pkg), ("check", check_pkg)):
            if not _pkg:
                continue
            _src_pc = os.path.join(_pkg, "lib", "pkgconfig", "{}.pc".format(_name))
            if not os.path.isfile(_src_pc):
                continue
            with open(_src_pc, "r") as _f:
                _lines = _f.readlines()
            _lines = [l for l in _lines if not l.lstrip().startswith(
                ("prefix=", "exec_prefix=", "libdir=", "includedir="))]
            _content = "".join(_lines)
            _header = (
                "prefix={pkg}\n"
                "exec_prefix=${{prefix}}\n"
                "libdir={pkg}/lib\n"
                "includedir={pkg}/include\n"
            ).format(pkg=_pkg)
            _content = _header + _content
            _dst_pc = os.path.join(pc_stage, "{}.pc".format(_name))
            with open(_dst_pc, "w") as _f:
                _f.write(_content)
            pc_dirs.append(pc_stage)
        if pc_dirs:
            env["PKG_CONFIG_PATH"] = ":".join(pc_dirs + [env.get("PKG_CONFIG_PATH", "")])
            env["PKG_CONFIG_LIBDIR"] = pc_stage

        def _run(cmd):
            self.output.info("run: {}".format(cmd))
            subprocess.check_call(cmd, shell=True, env=env, cwd=self.build_folder)

        _run('cmake -B "{}" -S "{}" {}'.format(
            bdir, self.source_folder, " ".join(defs)))

        _run('cmake --build "{}" -j{}'.format(
            bdir, max(1, os.cpu_count() or 1)))

        # ── Upstream official tests (test/api + test/tools, CTest) ──────
        # test/api: 9 check-framework unit tests (core API).
        # test/tools: 220 document round-trip tests via launchTests.sh.
        # Both need LD_LIBRARY_PATH for relative NEEDED + libcheck/libexpat;
        # launchTests.sh resolves its own paths via ${_SCRIPT_DIR} (patch).
        if self.options.unit_test and check_pkg:
            test_libpath = [
                os.path.join(bdir, "src"),
                os.path.join(check_pkg, "lib"),
                os.path.join(expat_pkg, "lib"),
            ]
            test_env = dict(env)
            test_env["LD_LIBRARY_PATH"] = ":".join(
                test_libpath + [test_env.get("LD_LIBRARY_PATH", "")])
            # launchTests.sh calls xml2wbxml/wbxml2xml from PATH — must
            # include the build tools dir so the scripts find them.
            test_env["PATH"] = "{}:{}:{}".format(
                os.path.join(bdir, "tools"),
                os.path.join(bdir, "src"),
                test_env.get("PATH", ""))
            # ── Writable temp dir for the check framework IPC temp files ──
            # libcheck's check_msg.c:317 creates a temp file in TMPDIR (or
            # /tmp fallback) for fork/exec communication; on OHOS the
            # default /tmp may be absent or read-only, which makes all 9
            # API tests fail with "Unable to create temporary file for
            # communication". Give the suite a private writable dir under
            # the build folder and export TMPDIR/TMP/TEMP to it. launchTests.sh
            # also uses `mktemp -d -t` which honors TMPDIR for the 220 tools
            # tests. Do NOT set CK_FORK=no — keep upstream default fork mode.
            test_tmp = os.path.join(self.build_folder, ".test-tmp")
            os.makedirs(test_tmp, exist_ok=True)
            test_env["TMPDIR"] = test_tmp
            test_env["TMP"] = test_tmp
            test_env["TEMP"] = test_tmp
            self.output.info("run: ctest (LD_LIBRARY_PATH={}, TMPDIR={})".format(
                test_env["LD_LIBRARY_PATH"], test_tmp))
            # Run ALL 229 tests — do NOT skip, filter, or ignore_errors.
            r = subprocess.run(
                'ctest --test-dir "{}" --output-on-failure'.format(bdir),
                shell=True, env=test_env, cwd=self.build_folder,
                capture_output=True, text=True, timeout=900)
            # Print full ctest output so CI L1 gate can parse results.
            self.output.info(r.stdout[-4000:] if len(r.stdout) > 4000 else r.stdout)
            if r.stderr:
                self.output.info(r.stderr[-2000:])
            if r.returncode != 0:
                self.output.warning(
                    "ctest returned {} (some tests failed — see above)".format(
                        r.returncode))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(
            bdir, self.package_folder))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "GNU-LGPL", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                _p = os.path.join(bindir, name)
                if os.path.isfile(_p) and not os.path.islink(_p) and self._is_elf(_p):
                    targets.append(_p)
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found, skipping code signing")
            return
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # Upstream installs headers to include/libwbxml-<sover>.<age>/wbxml/*.h
        inc_root = os.path.join(self.package_folder, "include")
        wbxml_inc = inc_root
        for d in sorted(glob.glob(os.path.join(inc_root, "libwbxml-*"))):
            if os.path.isdir(os.path.join(d, "wbxml")):
                wbxml_inc = d
                break
        rel = os.path.relpath(wbxml_inc, self.package_folder)
        self.cpp_info.includedirs = [rel]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["wbxml2"]
        self.cpp_info.requires = ["expat::expat"]
