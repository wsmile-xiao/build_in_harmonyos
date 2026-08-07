#!/usr/bin/env python3
"""Conan recipe — synfig 1.5.5 (CMake, CLI-only: synfig renderer from synfig-core)

Builds ETL + synfig-core from the official v1.5.5 tag archive; synfig-studio is
disabled (-DWITH_STUDIO=OFF).  Produces:
  - bin/synfig            the command-line renderer  (R38 -> commands.json)
  - libsynfig             the core animation library (static by default)

OHOS specifics handled here (same pattern as geos/libxml2/libjpeg-turbo):
  - self-discovered ohos.toolchain.cmake (bypasses conan_toolchain, ML-0035)
  - dep package folders injected via CMAKE_PROJECT_TOP_LEVEL_INCLUDES (E092)
  - PKG_CONFIG_PATH from VirtualBuildEnv so pkg_check_modules finds every .pc
  - C++17 forced (E130: OHOS libc++ headers require C++17)
  - CMAKE_POLICY_VERSION_MINIMUM=3.5 for cmake 4.x (E103/E187)
  - installed ELF binaries re-signed with binary-sign-tool (E077/E135)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class SynfigConan(ConanFile):
    name = "synfig"
    version = "1.5.5"
    description = "Synfig command-line renderer (synfig-core) for HarmonyOS PC"
    license = "GPL-2.0-or-later"
    homepage = "https://www.synfig.org/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    generators = "VirtualBuildEnv", "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # W0 已核实：conan 制品仓（ohpcd）包名以 conanfile.py 的 name 字段为准——
        # libsigc（非 libsigc++，cmd-pkgs install.sh 的系统包名才是 libsigc++）。
        # 版本裁决（定案，勿回退）：glibmm 2.84.0 提供 glibmm-2.68.pc（需 sigc++-3.0），
        # 不符合 synfig；synfig-core/src/CMakeLists.txt 探测 glibmm-2.4.pc，依赖必须用
        # glibmm 2.66.x（最后提供 glibmm-2.4.pc 的 2.4 ABI 线，本地 conan 缓存已构建 os=OHOS）。
        self.requires("glibmm/2.66.9")      # 提供 glibmm-2.4.pc（依赖项：随 PR 从源码构建，无 channel 与制品仓格式一致）
        # 版本裁决：synfig 1.5.5 探测旧 pc 名 libxml++-2.6（synfig-core/src/CMakeLists.txt:
        # pkg_check_modules(XMLPP REQUIRED IMPORTED_TARGET libxml++-2.6)），只能配旧 2.x API
        # 包 libxmlpp/2.42.3（2.x 线官方最新，GNOME 无 2.46 线）；5.x 不满足。
        self.requires("libxmlpp/2.42.3")   # 提供 libxml++-2.6.pc（依赖项：随 PR 从源码构建，无 channel 与制品仓格式一致）
        self.requires("libsigc/2.10.8")     # conan 包名 libsigc；glibmm 依赖 sigc++-2.0
        self.requires("cairo/1.18.4")       # 自带 pixman/libpng/freetype/fontconfig/zlib 传递依赖
        self.requires("freetype/2.14.3")
        # force=True：本仓 cairo/1.18.4 的 cache 配方（旧 revision）钉的是 fontconfig/2.18.1，
        # 而 2.18.1 的 libfontconfig.so DT_NEEDED 烤了 conan cache 绝对路径（本仓已修复为 2.18.1.1）。
        # force 让本包的直接依赖压过 cairo 传递的旧 pin（见 pinocchio 同款模式）；
        # 两者上游都是 fontconfig 2.18.x，.1.1 只是本仓打包修复后缀，ABI/.so 名不变。
        self.requires("fontconfig/2.18.1.1", force=True)  # .1 = 修复 DT_NEEDED 烤 conan cache 绝对路径的干净版
        self.requires("fftw/3.3.10.1")      # 提供 fftw3.pc
        self.requires("zlib/1.3.1.1")
        self.requires("libpng/1.6.58")
        self.requires("libjpeg-turbo/3.2.0")
        # synfig-core/src/CMakeLists.txt REQUIRED 探测：fribidi / harfbuzz
        self.requires("harfbuzz/14.2.0")
        self.requires("fribidi/1.0.16")
        # libxml2 由 libxmlpp 的 conan 依赖链提供（libxmlpp requires libxml2/2.15.3，
        # PkgConfigDeps 生成 libxml-2.0.pc），不再依赖 cmd-pkgs 系统 prefix。
        # pango 仅被 synfig-studio（GUI，WITH_STUDIO=OFF 已关闭）使用，CLI-only
        # 构建（synfig-core）上游 CMake 无 pango 探测，故无需系统依赖。

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"]["synfig"], strip_root=True)
        # ETL 结构结论：官方 v1.5.5 tag 归档（GitHub "Source code (tar.gz)"）内含 ETL/，
        # 顶层 CMakeLists 会一起构建，无需单独适配 ETL。
        # 兜底：若改用 release 的 synfig-1.5.5.tar.gz（可能不含 ETL），则把
        # ETL-1.5.5.tar.gz 覆盖到 <src>/ETL（synfig-core 以 ../ETL 引用它）。
        etl_dir = os.path.join(self.source_folder, "ETL")
        if not os.path.isfile(os.path.join(etl_dir, "CMakeLists.txt")):
            etl = self.conan_data.get("sources", {}).get("etl")
            if etl:
                get(self, **etl, destination=etl_dir, strip_root=True)

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain
        # ② 环境 OHOS_NDK_HOME ③ glob 设备/CI 的 SDK 布局），不依赖 CI profile host 段。
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else [])
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        import glob
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if g:
            return g[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _llvm_ranlib(self, toolchain):
        # OHOS SDK 的 llvm/bin 常只有 llvm-ar 没有 llvm-ranlib，而 ohos.toolchain.cmake
        # 仍把 CMAKE_RANLIB 指过去，造 .a 时报 "Error running link command: no such file
        # or directory" 且不说明缺哪个程序。返回 "" 表示 SDK 自带就不用管。
        import shutil
        sdk_bin = os.path.normpath(os.path.join(toolchain, "..", "..", "..", "llvm", "bin"))
        if os.path.isfile(os.path.join(sdk_bin, "llvm-ranlib")):
            return ""
        return shutil.which("llvm-ranlib") or ""

    def _find_deps_preload(self):
        # 让 find_package/find_library 能找到 conan 依赖包。ohos.toolchain 用普通 set()
        # 设 CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY，命令行 -D cache 变量压不住；只能靠
        # CMAKE_PROJECT_TOP_LEVEL_INCLUDES（toolchain 之后、project() 之后、第一个
        # find_package 之前执行）改。无依赖时返回 "" 不写文件。
        deps = [d.package_folder for _r, d in self.dependencies.items() if d.package_folder]
        if not deps:
            return ""
        path = os.path.join(self.build_folder, "ohos-find-deps.cmake")
        with open(path, "w", encoding="utf-8") as f:
            for p in deps:
                p = p.replace("\\", "/")
                f.write('list(APPEND CMAKE_FIND_ROOT_PATH "%s")\n' % p)
                f.write('list(APPEND CMAKE_PREFIX_PATH "%s")\n' % p)
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)\n")
        return path

    def _project_src(self):
        # 顶层工程（ETL + synfig-core + studio）优先；无顶层 CMakeLists 则回退到
        # synfig-core 子目录（synfig-core 自会 add_subdirectory(../ETL)）。
        src = self.source_folder
        if os.path.isfile(os.path.join(src, "synfig-core", "CMakeLists.txt")):
            if os.path.isfile(os.path.join(src, "CMakeLists.txt")):
                return src
            return os.path.join(src, "synfig-core")
        return src

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        bdir = os.path.join(self.build_folder, "build-ohos")
        src = self._project_src()
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",       # ohos.toolchain 64 位默认装 lib64/，须改回 lib
            "-DBUILD_SHARED_LIBS=OFF",          # 静态 libsynfig：CLI 工具优先，免 .so 签名 / dlopen 风险
            "-DCMAKE_CXX_STANDARD=17",          # E130：OHOS libc++ 头文件要求 C++17
            "-DCMAKE_CXX_STANDARD_REQUIRED=ON",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",  # E103/E187：cmake 4.x 向后兼容
            # ---- CLI-only：关 studio 与可选渲染/依赖后端，缩小依赖面 ----
            "-DWITH_STUDIO=OFF",
            "-DWITH_OPENEXR=OFF", "-DENABLE_OPENEXR=OFF",
            "-DWITH_MAGICKPP=OFF", "-DENABLE_MAGICKPP=OFF",
            "-DWITH_FFMPEG=OFF", "-DENABLE_FFMPEG=OFF",
            "-DWITH_JACK=OFF",
            "-DWITH_SDL=OFF",
            "-DWITH_DLOPEN=OFF",
            "-DENABLE_TESTS=ON",     # 上游 synfig-core/test 注册 add_test（test_synfig_*），CI 门禁要求 build() 执行 ctest
        ]
        rl = self._llvm_ranlib(toolchain)
        if rl:
            defs.append('-DCMAKE_RANLIB="{}"'.format(rl))
        pre = self._find_deps_preload()
        if pre:
            defs.append('-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="{}"'.format(pre))
        # pkg-config 查找路径必须**显式聚合**：依赖配方的 package_info 用 pkg_config_name
        # 属性（PkgConfigDeps 语义），VirtualBuildEnv 不会自动把依赖 lib/pkgconfig 拼进
        # PKG_CONFIG_PATH。这里把 PkgConfigDeps 生成的 .pc（prefix 已重写为包实际安装目录）、
        # 各依赖包 lib/pkgconfig 依次前置，pkg_check_modules(glibmm-2.4 / libxml++-2.6 /
        # cairo / fftw3 / sigc++-2.0 / glib-2.0) 才能命中。
        # 系统依赖已移除：libxml2 由 libxmlpp 的 conan 依赖链提供（PkgConfigDeps 生成
        # libxml-2.0.pc），pango 仅 studio 使用（WITH_STUDIO=OFF 已关闭）。
        pc_dirs = []
        if os.path.isdir(self.generators_folder):
            pc_dirs.append(self.generators_folder)
        for _r, d in self.dependencies.items():
            if d.package_folder:
                pc = os.path.join(d.package_folder, "lib", "pkgconfig")
                if os.path.isdir(pc):
                    pc_dirs.append(pc)
        pc_path = ":".join(pc_dirs)
        self.run(
            'PKG_CONFIG_PATH="{pc}" cmake -B "{b}" -S "{s}" {d}'.format(
                pc=pc_path, b=bdir, s=src, d=" ".join(defs)),
            env="conanbuild")
        self.run('cmake --build "{}"'.format(bdir), env="conanbuild")
        # 上游官方测试（ctest，test_synfig_* 由 -DENABLE_TESTS=ON 注册）：CI 门禁要求
        # build() 执行 make check/ctest。交叉构建（build=Linux / host=OHOS）时构建机
        # 不能 exec aarch64 二进制 → 跳过；原生 OHOS/HarmonyOS 时执行 ctest。
        if cross_building(self):
            self.output.info(
                "cross-building: skip ctest (OHOS binaries not runnable on build host)"
            )
        else:
            self.run(
                'ctest --test-dir "{}" --output-on-failure'.format(bdir),
                env="conanbuild")

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC：被 exec 的可执行文件与 dlopen 的 .so 都要代码签名（cmake/SDK 自签
        # 无效，conan install 复制也会破坏链接器自签）→ 剥 .codesign + binary-sign-tool
        # -selfSign 重签。静态构建时主要签 bin/synfig；shared 时 lib/ 的 .so 一并签。
        import glob
        import shutil
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        if not targets:
            return
        # objcopy 回退搜索（对齐 glibmm/libxmlpp）：固定路径 → PATH → 编译器同目录。
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates_objcopy if p and os.path.isfile(p)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            # 对齐 glibmm/libxmlpp：交叉编译 Docker/SDK worker 无 binary-sign-tool，
            # 跳过签名并 warning（否则 package() 因命令不存在而失败）。
            self.output.warning("binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        for f in targets:
            if os.path.islink(f):  # 只签真实 ELF，跳版本化 .so 的软链
                continue
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["synfig"]
        self.cpp_info.bindirs = ["bin"]          # R38：CLI 工具，bin/ 暴露给 conanrun PATH
        self.cpp_info.set_property("cmake_file_name", "synfig")
        self.cpp_info.set_property("cmake_target_name", "synfig::synfig")
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个 stem。
        import glob
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        return os.path.splitext(os.path.basename(pcs[0]))[0] if pcs else ""
