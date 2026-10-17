#!/usr/bin/env python3
"""Conan recipe — libcoverart 1.0.0 (CMake).

C/C++ client library for the MusicBrainz Cover Art Archive.
Upstream tag: release-1.0.0 (2012-10-09).
"""
import glob
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, replace_in_file
from conan.tools.layout import basic_layout


class LibcoverartConan(ConanFile):
    name = "libcoverart"
    version = "1.0.0"
    description = "C/C++ client library for the MusicBrainz Cover Art Archive"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/metabrainz/libcoverart"
    url = "https://github.com/metabrainz/libcoverart"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # Static by default: neon/0.34.0 only ships a non-PIC static archive, so a
    # shared libcoverart would fail to link (aarch64 relocation errors).
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "conandata.yml"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("neon/0.34.0")
        # Repo-unique jansson (same upstream v2.15.1 tarball, zero
        # tool_requires): bare 2.15.1 exists on both remotes and preflight
        # checks conancenter first, where the CCI recipe's tool_requires
        # pulls cmake/4.4.x with no OHOS source entry (KeyError: 'OHOS').
        self.requires("jansson/2.15.1.1")
        # libxml2 is needed to build the make-c-interface code generator
        # (src/CMakeLists.txt links it into the host tool).
        self.requires("libxml2/2.15.3.1")
        # Transitive closure via neon (requires zlib/1.3.1 + expat/2.8.2):
        # both bare versions exist on conancenter and resolve to CCI
        # recipes with cmake tool edges. Override to the repo-unique
        # revisions (same upstream sources, zero tool_requires) so the
        # whole graph stays on the in-repo OHOS recipes.
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("expat/2.8.2.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 本配方走 NDK ohos.toolchain + 裸 cmake（见 _ohos_toolchain），不
        # 使用 CMakeToolchain：后者生成的 CMAKE_SYSTEM_NAME=HarmonyOS 在
        # 真机 cmake 4.4.3 下无平台模块（"System is unknown to cmake"），
        # Linux 别名亦无法通过编译器识别（第 3 轮同指纹，需换策略）。
        # readonly_tmp: 真机 /tmp 只读，cmake/编译器子进程须走任务级可写
        # 目录。HMBS 已注入 TMPDIR，这里再经 Environment 落盘脚本确保
        # conanbuild 环境内同样可见。
        from conan.tools.env import Environment
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP") or "")
        if not (tmpdir and os.path.isdir(tmpdir)):
            tmpdir = os.path.join(self.build_folder, "hmbs-tmp")
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except Exception:
                pass
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.vars(self).save_script("hmbs_tmpdir")

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（同 libxml2/2.15.3.1 在仓
        # 先例；不依赖 profile host 段 user_toolchain）。找不到时返回 None，
        # 由 build() 降级到 SDK 无关的备用工具链（见 _fallback_toolchain），
        # 不再抛硬错误：预检 worker 的 SDK 挂载路径与 CI 可能不同。
        import glob
        try:
            ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain",
                               default=[], check_type=list)
        except Exception:
            ut = []
        cands = list(ut or [])
        for envkey in ("OHOS_NDK_HOME", "OHOS_SDK_HOME", "OHOS_SDK_ROOT",
                       "OhosSdkHome"):
            base = os.environ.get(envkey, "")
            if base:
                cands.append(os.path.join(
                    base, "build/cmake/ohos.toolchain.cmake"))
                cands.append(os.path.join(
                    base, "ohos/native/build/cmake/ohos.toolchain.cmake"))
                cands.append(os.path.join(
                    base, "native/build/cmake/ohos.toolchain.cmake"))
        for cand in cands:
            if cand and os.path.isfile(cand):
                return cand
        patterns = [
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/"
            "ohos.toolchain.cmake",
            "/data/service/hnp/ohos-sdk*/*/ohos/native/build/cmake/"
            "ohos.toolchain.cmake",
            "/data/service/hnp/*/ohos/native/build/cmake/"
            "ohos.toolchain.cmake",
            "/opt/ohos-sdk*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/opt/ohos*/ohos/native/build/cmake/ohos.toolchain.cmake",
        ]
        for pat in patterns:
            try:
                globbed = sorted(glob.glob(pat))
            except Exception:
                continue
            if globbed:
                return globbed[-1]
        return None

    def _conf_compiler(self, key):
        # 权威编译器来源：profile [conf] tools.build:compiler_executables
        #（同 libcello/2.1.0 在仓先例）；PATH 回退仅作兜底。
        import shutil
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict)
        except Exception:
            exes = {}
        if isinstance(exes, dict):
            val = exes.get(key) or exes.get("c") or exes.get("cpp")
            if val and os.path.isfile(str(val)):
                return str(val)
        fallbacks = {"c": ("clang",), "cpp": ("clang++", "clang", "c++")}
        for prog in fallbacks.get(key, ("clang",)):
            found = shutil.which(prog)
            if found:
                return found
        return "/data/service/hnp/bin/clang" if key == "c" else \
            "/data/service/hnp/bin/clang++"

    def _fallback_toolchain(self):
        # SDK 无关的备用工具链：真机 cmake 4.4.3 无 Platform/HarmonyOS 模块，
        # 且 conan_toolchain 的编译器调用缺目标三元组/sysroot（前两轮同指纹）。
        # 用 Linux 别名 + STATIC_LIBRARY try-compile（同 lapack/3.12.1 在仓
        # 先例）绕开编译器识别链接；编译器取自 profile conf，与 test_package
        # 的 _cxx() 同源。只在 _ohos_toolchain() 返回 None 时使用。
        cc = self._conf_compiler("c")
        cxx = self._conf_compiler("cpp")
        import shutil as _sh
        _ar_cands = []
        try:
            _sib = os.path.join(os.path.dirname(os.path.realpath(cc)),
                                "llvm-ar")
            if _sib:
                _ar_cands.append(_sib)
        except Exception:
            pass
        for _extra in ("/data/service/hnp/bin/llvm-ar",
                       _sh.which("llvm-ar") or "",
                       _sh.which("ar") or ""):
            if _extra:
                _ar_cands.append(_extra)
        ar_line = ""
        ranlib_line = ""
        try:
            for _c in _ar_cands:
                if _c and os.path.isfile(_c):
                    ar_line = 'set(CMAKE_AR "%s")\n' % _c.replace("\\", "/")
                    break
            _rl_cands = ["/data/service/hnp/bin/llvm-ranlib",
                         _sh.which("llvm-ranlib") or "",
                         _sh.which("ranlib") or ""]
            try:
                _sib_rl = os.path.join(
                    os.path.dirname(os.path.realpath(cc)), "llvm-ranlib")
                _rl_cands.insert(0, _sib_rl)
            except Exception:
                pass
            for _c in _rl_cands:
                if _c and os.path.isfile(_c):
                    ranlib_line = ('set(CMAKE_RANLIB "%s")\n'
                                   % _c.replace("\\", "/"))
                    break
        except Exception:
            pass
        path = os.path.join(self.build_folder, "hmbs-fallback-toolchain.cmake")
        try:
            os.makedirs(self.build_folder, exist_ok=True)
        except Exception:
            pass
        content = (
            'set(CMAKE_SYSTEM_NAME Linux)\n'
            'set(CMAKE_SYSTEM_PROCESSOR aarch64)\n'
            'set(CMAKE_C_COMPILER "%s")\n'
            'set(CMAKE_CXX_COMPILER "%s")\n'
            '%s'
            '%s'
            'set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)\n'
            'set(CMAKE_POLICY_VERSION_MINIMUM 3.5)\n'
        ) % (cc.replace("\\", "/"), cxx.replace("\\", "/"), ar_line,
             ranlib_line)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        self.output.info("using SDK-free fallback toolchain: %s" % path)
        return path

    def _ohos_llvm_bin(self, toolchain):
        # E012/E429: ohos.toolchain.cmake 把 CMAKE_AR/RANLIB 指向 SDK
        # native/llvm/bin 下的 bare 名或绝对路径，但该目录缺 llvm-ranlib
        #（部分 SDK 亦缺 llvm-ar 的 PATH 可见性），静态库归档即报
        # "Error running link command: no such file or directory"
        #（box2d/crunch-dxtc/googletest/draco 在仓先例）。从 toolchain
        # 路径推导 <ndk>/llvm/bin，落空时 glob 通用 SDK 路径。
        import glob as _glob
        if toolchain:
            try:
                ndk_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(str(toolchain))))
                llvm_bin = os.path.join(ndk_root, "llvm", "bin")
                if os.path.isdir(llvm_bin):
                    return llvm_bin
            except Exception:
                pass
        for base in ("/data/service/hnp/ohos-sdk.org",):
            pat = os.path.join(base, "*", "ohos", "native", "llvm", "bin")
            try:
                matches = sorted(_glob.glob(pat))
            except Exception:
                continue
            if matches:
                return matches[-1]
        return None

    def _archiver_defs(self, toolchain):
        # 用绝对路径覆盖 CMAKE_AR/RANLIB，并覆写 CREATE_STATIC_LIBRARY
        # 规则为 "<ar> rcs <TARGET> <OBJECTS>"：即使 RANLIB 缺失也能单步
        # 归档（crunch-dxtc/googlexml 同法；ohos.toolchain 的 FORCE 值会被
        # 规则覆盖兜底）。候选顺序：SDK llvm/bin → hnp 预置 → PATH。
        import shutil as _sh
        llvm_bin = self._ohos_llvm_bin(toolchain)
        ar_cands = []
        if llvm_bin:
            ar_cands.append(os.path.join(llvm_bin, "llvm-ar"))
        for extra in ("/data/service/hnp/bin/llvm-ar",
                      _sh.which("llvm-ar") or "",
                      _sh.which("ar") or ""):
            if extra:
                ar_cands.append(extra)
        ar = next((q for q in ar_cands if q and os.path.isfile(q)), "")
        if not ar:
            self.output.info(
                "llvm-ar/ar not found, keep toolchain default CMAKE_AR")
            return []
        rl_cands = []
        if llvm_bin:
            rl_cands.append(os.path.join(llvm_bin, "llvm-ranlib"))
        for extra in ("/data/service/hnp/bin/llvm-ranlib",
                      _sh.which("llvm-ranlib") or "",
                      _sh.which("ranlib") or ""):
            if extra:
                rl_cands.append(extra)
        ranlib = next((q for q in rl_cands if q and os.path.isfile(q)), "")
        self.output.info("Using archiver: %s%s" % (
            ar, (" ranlib=%s" % ranlib) if ranlib else " (no ranlib)"))
        defs = ['"-DCMAKE_AR:FILEPATH=%s"' % ar.replace("\\", "/"),
                '"-DCMAKE_C_CREATE_STATIC_LIBRARY=%s rcs <TARGET> <OBJECTS>"'
                % ar.replace("\\", "/"),
                '"-DCMAKE_CXX_CREATE_STATIC_LIBRARY=%s rcs <TARGET> <OBJECTS>"'
                % ar.replace("\\", "/")]
        if ranlib:
            defs.append('"-DCMAKE_RANLIB:FILEPATH=%s"'
                        % ranlib.replace("\\", "/"))
        else:
            # SDK 缺 ranlib 时显式禁用，避免默认规则调用不存在的二进制。
            defs.append('"-DCMAKE_RANLIB=:"')
        return defs

    def _cmake_bin(self):
        # HMBS 注入优先，其次 conf，最后 PATH（hmbs 已前置工具目录）。
        import shutil
        for cand in (os.environ.get("HMBS_CMAKE"),
                     (self.conf.get("user.hmbs:cmake_path", default=None)
                      if hasattr(self, "conf") else None)):
            if cand and os.path.isfile(str(cand)):
                return str(cand)
        return shutil.which("cmake") or "cmake"

    def _dep_cmake_defs(self):
        # 上游 FindNeon/FindJansson 先探 pkg-config 再回退 /usr；在干净
        # worker 上永不命中，故把 Conan 包路径显式 pin 为 cache 变量。
        neon = self.dependencies["neon"]
        jansson = self.dependencies["jansson"]
        libxml2 = self.dependencies["libxml2"]
        return " ".join([
            '-DNEON_INCLUDE_DIR="%s"' % self._inc_dir(
                neon.package_folder, "neon"),
            '-DNEON_LIBRARIES="%s"' % self._pick_lib(
                neon.package_folder, "neon"),
            '-DJANSSON_INCLUDE_DIR="%s"' % os.path.join(
                jansson.package_folder, "include").replace("\\", "/"),
            '-DJANSSON_LIBRARIES="%s"' % self._pick_lib(
                jansson.package_folder, "jansson"),
            '-DLIBXML2_INCLUDE_DIR="%s"' % os.path.join(
                libxml2.package_folder, "include",
                "libxml2").replace("\\", "/"),
            '-DLIBXML2_LIBRARY="%s"' % self._pick_lib(
                libxml2.package_folder, "xml2"),
            '-DCMAKE_POLICY_VERSION_MINIMUM="3.5"',
            '-DBUILD_SHARED_LIBS="%s"' % ("ON" if self.options.shared
                                          else "OFF"),
        ])

    @staticmethod
    def _pick_lib(package_folder, base):
        """Return the concrete library file (static preferred, shared fallback).

        Static-first: the default build is static (neon ships non-PIC
        static only) and static test consumers avoid the musl runtime
        loader path (LD_LIBRARY_PATH gaps / unsigned .so) that broke
        test_package with `Error loading shared library libcoverart.so.0`.
        """
        cands = sorted(glob.glob(os.path.join(
            package_folder, "lib", "lib%s.a" % base)))
        cands += sorted(glob.glob(os.path.join(
            package_folder, "lib", "lib%s.so*" % base)))
        if not cands:
            raise ConanException(
                "lib%s not found under %s/lib" % (base, package_folder))
        return cands[0].replace("\\", "/")

    @staticmethod
    def _inc_dir(package_folder, sub):
        """Return include/<sub> when present, else plain include/."""
        p = os.path.join(package_folder, "include", sub)
        if os.path.isdir(p):
            return p.replace("\\", "/")
        return os.path.join(package_folder, "include").replace("\\", "/")

    def _build_native_import(self, cmake):
        # 上游 src/CMakeLists 以 CMAKE_CROSSCOMPILING 决定生成器策略：交叉
        # 时 INCLUDE(${IMPORT_EXECUTABLES})（缺省为 IMPORTFILE-NOTFOUND），
        # 非交叉时原生构建 make-c-interface 并 EXPORT 到 ImportExecutables
        # .cmake。本机构建（NDK 工具链 OHOS 系统名 / 备用链）会落入交叉分支，
        # 故先做一次无工具链的原生配置、只构建 make-c-interface 目标，产出
        # 的 ImportExecutables.cmake 供主构建经 -DIMPORT_EXECUTABLES 导入。
        # 生成器仅由 xmlParser.* 自举（不链接 neon/jansson），原生二进制在
        # 同机 aarch64 上可直接执行；FIND_PACKAGE 仍需依赖 pin，故复用。
        ndir = os.path.join(self.build_folder, "native-gen")
        cc = self._conf_compiler("c")
        cxx = self._conf_compiler("cpp")
        ndefs = " ".join([
            '"-DCMAKE_C_COMPILER=%s"' % cc.replace("\\", "/"),
            '"-DCMAKE_CXX_COMPILER=%s"' % cxx.replace("\\", "/"),
            '"-DCMAKE_BUILD_TYPE=Release"',
            self._dep_cmake_defs(),
        ])
        self.run('%s -B "%s" -S "%s" %s' % (
            cmake, ndir, self.source_folder, ndefs))
        self.run('%s --build "%s" --target make-c-interface' % (cmake, ndir))
        exp = os.path.join(ndir, "ImportExecutables.cmake")
        if not os.path.isfile(exp):
            raise ConanException(
                "native ImportExecutables.cmake not generated at %s" % exp)
        self.output.info("native generator export: %s" % exp)
        return exp

    def build(self):
        # conan buildenv 隔离下子进程可能看不到外部 TMPDIR，进程级兜底。
        _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP"))
        if not (_tmp and os.path.isdir(_tmp)):
            _tmp = os.path.join(self.build_folder, "hmbs-tmp")
            try:
                os.makedirs(_tmp, exist_ok=True)
            except Exception:
                pass
            os.environ["TMPDIR"] = _tmp
            os.environ["TMP"] = _tmp
            os.environ["TEMP"] = _tmp
        self._portability_fixes()
        # NDK ohos.toolchain 优先（自带目标三元组/sysroot 与平台模块）；
        # 缺失时降级到 SDK 无关备用工具链（Linux 别名 + STATIC try-compile），
        # 不再抛 InvalidConfiguration（上一轮硬报错导致 compile 门失败）。
        cmake = self._cmake_bin()
        toolchain = self._ohos_toolchain()
        extra_defs = []
        if toolchain:
            self.output.info("using NDK toolchain: %s" % toolchain)
            extra_defs.append('"-DOHOS_ARCH=arm64-v8a"')
        else:
            toolchain = self._fallback_toolchain()
        # E012/E429 归档器覆盖（CI #48596）：静态库链接报
        # "Error running link command: no such file or directory" 时用
        # 绝对路径 llvm-ar/ranlib + CREATE_STATIC_LIBRARY 规则覆盖。
        try:
            extra_defs.extend(self._archiver_defs(toolchain))
        except Exception as _e:
            self.output.warning("archiver probe failed: %s" % _e)
        bdir = os.path.join(self.build_folder, "build-ohos")
        import_exe = self._build_native_import(cmake)
        # 上游根 CMakeLists 在 configure 期把 CMAKE_INSTALL_PREFIX 展开为
        # 绝对路径并 CACHE FORCE 到 EXEC/LIB/INCLUDE_INSTALL_DIR，后续
        # `cmake --install --prefix` 无法覆盖已展开的绝对 DESTINATION，
        # 导致 package() 越界写 /usr/local/include/coverart。本次把
        # package_folder 直接作为 configure 期前缀 baking 进缓存。
        pkg = self.package_folder.replace("\\", "/")
        defs = " ".join([
            '-DCMAKE_TOOLCHAIN_FILE="%s"' % toolchain,
            '"-DCMAKE_BUILD_TYPE=%s"' % self.settings.build_type,
            '"-DCMAKE_INSTALL_PREFIX=%s"' % pkg,
            '"-DEXEC_INSTALL_PREFIX=%s"' % pkg,
            '"-DBIN_INSTALL_DIR=%s/bin"' % pkg,
            '"-DLIB_INSTALL_DIR=%s/lib"' % pkg,
            '"-DINCLUDE_INSTALL_DIR=%s/include"' % pkg,
            self._dep_cmake_defs(),
            '"-DIMPORT_EXECUTABLES=%s"' % import_exe.replace("\\", "/"),
        ] + extra_defs)
        self.run('%s -B "%s" -S "%s" %s' % (
            cmake, bdir, self.source_folder, defs))
        self.run('%s --build "%s"' % (cmake, bdir))
        self._run_upstream_offline_test()

    def _portability_fixes(self):
        # 1. Upstream pins cmake_minimum_required(VERSION 2.6), which modern
        #    CMake (>= 4.0) rejects outright. 3.5 is the lowest version a
        #    current CMake still accepts; no build logic changes.
        replace_in_file(self,
                         os.path.join(self.source_folder, "CMakeLists.txt"),
                         "cmake_minimum_required(VERSION 2.6)",
                         "cmake_minimum_required(VERSION 3.5)")
        # 2. Upstream adds -Werror everywhere. 2012-era code trips new
        #    warnings under clang 15, turning them into hard errors, so drop
        #    -Werror while keeping -Wall -Wextra.
        for sub in ("src/CMakeLists.txt",
                    "tests/CMakeLists.txt",
                    "examples/CMakeLists.txt"):
            replace_in_file(self,
                             os.path.join(self.source_folder, sub),
                             "-Wall -Werror -Wextra -pedantic-errors",
                             "-Wall -Wextra")
        # 3. Upstream DEPENDS on the literal glob `*.inc`; modern CMake
        #    (>= 3.x strict makefile generator) emits it as a literal file
        #    target `src/*.inc` with no rule (`No rule to make target
        #    'src/*.inc'`). Expand to the 5 explicit .inc files verified in
        #    the release-1.0.0 tag; no build logic change.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src/CMakeLists.txt"),
            "DEPENDS make-c-interface cinterface.xml *.inc",
            "DEPENDS make-c-interface cinterface.xml "
            "c-int-coverart-defines.inc c-int-coverart-source.inc "
            "c-int-imagedata-defines.inc c-int-imagedata-source.inc "
            "c-int-source-funcs.inc")
        # 4. Root INSTALL references the generated `caa_c.h` via the
        #    source-relative path `include/coverart/caa_c.h`, but the file is
        #    generated into the binary tree (`<binary>/include/coverart/`
        #    via src/CMakeLists copy_if_different). In-source builds hide
        #    this; out-of-source (conan) install then fails with
        #    `file INSTALL cannot find .../b/include/coverart/caa_c.h`.
        #    Point INSTALL at the binary-tree file; no test logic change.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "INSTALL(FILES ${headers} include/coverart/caa_c.h",
            "INSTALL(FILES ${headers} "
            "${CMAKE_CURRENT_BINARY_DIR}/include/coverart/caa_c.h")
        # 5. Upstream hardcodes `ADD_LIBRARY(coverart SHARED ...)` in
        #    src/CMakeLists.txt, ignoring BUILD_SHARED_LIBS, so the
        #    package always installs libcoverart.so(.0) even with
        #    shared=False. The musl loader on the real machine then
        #    fails test consumers with `Error loading shared library
        #    libcoverart.so.0` + every symbol `not found`. Drop the
        #    hardcoded SHARED keyword so BUILD_SHARED_LIBS (pinned in
        #    _dep_cmake_defs) controls the artefact; default static
        #    links fully at build time (also consistent with neon's
        #    non-PIC static archive). No source logic change.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src/CMakeLists.txt"),
            "ADD_LIBRARY(coverart SHARED",
            "ADD_LIBRARY(coverart")

    def _run_upstream_offline_test(self):
        """Run upstream tests/ctest and emit the HMBS evidence marker.

        Upstream ships two hand-rolled test programs and registers none of
        them with CTest, so cmake.test() would fail with "No tests were
        found". tests/ctest exercises the C API fully offline
        (new/get_version/delete, exit 0); tests/cctest needs public-internet
        access to the Cover Art Archive and is therefore built but not gated
        (see notes.md for the audit).
        """
        exe_path = None
        for root, _dirs, files in os.walk(self.build_folder):
            if "ctest" in files:
                cand = os.path.join(root, "ctest")
                if os.path.isfile(cand):
                    exe_path = cand
                    break
        if exe_path is None:
            raise ConanException(
                "upstream test executable 'ctest' not found in build tree")
        log_path = os.path.join(self.build_folder, "upstream_ctest.log")
        self.run('"%s" > "%s" 2>&1' % (exe_path, log_path),
                 env="conanrun", ignore_errors=True)
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            out = f.read()
        self.output.info("upstream tests/ctest output:\n" + out.strip())
        # Falsification gate: the binary must print the exact version string.
        # An empty/wrong output (e.g. fixture or build mix-up) fails the build.
        passed = "Version: 'libcoverart-v1.0.0'" in out
        marker = {
            "status": "passed" if passed else "failed",
            "framework": "custom",
            "command": "./tests/ctest (offline C-API: new/get_version/delete)",
            "discovered": 1,
            "executed": 1,
            "passed": 1 if passed else 0,
            "failed": 0 if passed else 1,
            "skipped": 0,
        }
        self._emit_hmbs_upstream_marker(marker)
        if not passed:
            raise ConanException(
                "upstream tests/ctest did not print the expected version line")

    def _emit_hmbs_upstream_marker(self, marker):
        line = ("HMBS_UPSTREAM_TEST_RESULT="
                + json.dumps(marker, separators=(",", ":")))
        # Dual channel: print() reaches stdout directly, output.info reaches
        # the Conan log. Both land in the preflight log for the HMBS parser.
        print(line, flush=True)
        self.output.info(line)
        # Persist to the build folder so package() can stage it into the
        # package res/ dir for cache-hit re-emission from test_package.
        try:
            build_dir = self.build_folder
            if build_dir:
                with open(os.path.join(
                        build_dir, "hmbs_upstream_test_result.json"),
                        "w", encoding="utf-8") as f:
                    json.dump(marker, f)
                with open(os.path.join(
                        build_dir, "hmbs_upstream_test_result.txt"),
                        "w", encoding="utf-8") as f:
                    f.write(line + "\n")
        except Exception as exc:
            self.output.warning("Could not persist upstream marker: %s" % exc)

    def _stage_upstream_marker(self):
        # Stage the build-time upstream marker into package res/ so
        # test_package can re-emit the real result on cache-hit runs
        # where build() is skipped. Missing file: warn only, never forge.
        try:
            src = os.path.join(self.build_folder,
                               "hmbs_upstream_test_result.json")
            if os.path.isfile(src):
                res_dir = os.path.join(self.package_folder, "res")
                os.makedirs(res_dir, exist_ok=True)
                shutil.copy2(src, os.path.join(
                    res_dir, "hmbs_upstream_test_result.json"))
                txt = os.path.join(self.build_folder,
                                   "hmbs_upstream_test_result.txt")
                if os.path.isfile(txt):
                    shutil.copy2(txt, os.path.join(
                        res_dir, "hmbs_upstream_test_result.txt"))
            else:
                self.output.warning(
                    "Upstream marker persistence file not found in build "
                    "folder; cache-hit runs will rely on package res from "
                    "a previous build.")
        except Exception as exc:
            self.output.warning("Could not stage upstream marker: %s" % exc)

    def package(self):
        # 安装前缀已在 configure 期 baking 进 LIB/INCLUDE_INSTALL_DIR
        #（见 build()），此处直接 install，不再用 --prefix 覆盖（对上游
        # 绝对 DESTINATION 无效，反而掩盖问题）。
        cmake = self._cmake_bin()
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('%s --install "%s"' % (cmake, bdir))
        self._sign_shared_libs()
        self._stage_upstream_marker()

    def _sign_shared_libs(self):
        # OHOS .so 自签为 best-effort：预检 worker 与 CI 的签名工具路径
        # 可能不同（本轮真机缺 /data/service/hnp/bin/binary-sign-tool，
        # Error 127），缺工具时告警跳过、不让 package() 失败；有工具时
        # 才剥旧 .codesign 段后自签（同 libxml2/2.15.3.1 意图）。默认静态
        # 构建下无 .so，本方法直接返回。
        import glob
        import shutil
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"),
                         recursive=True)
        sos = [s for s in sos if not os.path.islink(s)]
        if not sos:
            return
        signer = (shutil.which("binary-sign-tool")
                  or os.environ.get("HMBS_SIGN_TOOL") or "")
        for cand in (signer, "/data/service/hnp/bin/binary-sign-tool",
                     "/storage/Users/currentUser/usr/local/bin/binary-sign-tool"):
            if cand and os.path.isfile(cand):
                signer = cand
                break
        else:
            signer = ""
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; skipping .so self-sign")
            return
        objcopy = shutil.which("llvm-objcopy")
        for cand in (objcopy, "/data/service/hnp/bin/llvm-objcopy"):
            if cand and os.path.isfile(cand):
                objcopy = cand
                break
        for so in sos:
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null'
                         ' || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                     .format(sg=signer, f=so))

    def package_info(self):
        # release-1.0.0 builds a single library `coverart` (C++ core + C API
        # in one target, see src/CMakeLists ADD_LIBRARY(coverart SHARED ...));
        # there is no separate `coverartcc` (verified via upstream file list:
        # only libcoverart.so + libcoverart.pc are installed).
        self.cpp_info.libs = ["coverart"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
