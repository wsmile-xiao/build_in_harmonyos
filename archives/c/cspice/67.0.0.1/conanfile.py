#!/usr/bin/env python3
"""Conan recipe — cspice 67.0.0.1 (cmake)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
import os
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches


class CspiceConan(ConanFile):
    name = "cspice"
    version = "67.0.0.1"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # CSPICE 本体单独取：NAIF 的 .tar.Z 是 Unix compress，conan 的 get() 不认，
        # 用 cmake -E tar 解（libarchive 支持 compress）。
        import os
        from conan.tools.files import download
        arc = os.path.join(self.source_folder, "cspice.tar.Z")
        try:
            # retry=0：NAIF 官方源在本环境不可达，减少无谓重试等待，尽快回退镜像
            download(self, self.conan_data["cspice_src"]["url"], arc,
                     sha256=self.conan_data["cspice_src"]["sha256"], retry=0)
        except BaseException as exc:
            # NAIF 官方源不可达时的 fallback：GitHub 上完整镜像的 N0067 源码
            # （conandata.yml cspice_src_mirror，与官方 N0067 同源，仅下载兜底）。
            # 注意：conan 的 download() 失败会 raise SystemExit（BaseException），
            # 必须用 BaseException 才能捕获并回退镜像。
            self.output.warning("NAIF 官方源下载失败（%s），回退 GitHub N0067 镜像" % exc)
            arc = os.path.join(self.source_folder, "cspice-mirror.tar.gz")
            download(self, self.conan_data["cspice_src_mirror"]["url"], arc,
                     sha256=self.conan_data["cspice_src_mirror"]["sha256"], retry=0)
        # `.tar.Z` 是 Unix compress(LZW)：conan 的 get() 不认；设备的 gzip 也解不了
        # （busybox/toybox 的 gzip 常缺 LZW）。CMake 内置 libarchive 支持 compress，
        # 故用 `cmake -E tar` 解，比依赖某个具体解压工具更稳。
        self.run('cd "%s" && cmake -E tar xf %s' % (self.source_folder, os.path.basename(arc)))
        os.remove(arc)
        # 官方包解出 cspice/，镜像包解出 cspice-master/，统一解析实际目录
        import glob as _glob
        _cands = [os.path.join(self.source_folder, "cspice"),
                  os.path.join(self.source_folder, "cspice-master")]
        self._cspice_src_dir = next((c for c in _cands if os.path.isdir(c)), None)
        if not self._cspice_src_dir:
            raise ConanInvalidConfiguration("无法定位 CSPICE 源码目录")

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain ② 环境 OHOS_NDK_HOME
        # ③ glob 设备/CI 的 SDK 布局），不依赖 CI profile host 段。
        import glob
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
        # OHOS SDK 的 llvm/bin 下**只有 llvm-ar，没有 llvm-ranlib**，而 ohos.toolchain.cmake
        # 仍把 CMAKE_RANLIB 指过去。cmake 造静态库是 `<AR> qc ... && <RANLIB> <lib>`，
        # 于是 .o 全编得动、一造 .a 就 ENOENT，且报错**不说是哪个程序**找不到：
        #   Error running link command: no such file or directory
        # 实证：OpenCV 4.12.0、SuiteSparse 7.8.3。返回 "" 表示不覆盖（SDK 自带就用它的）。
        import shutil
        sdk_bin = os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        cand = os.path.normpath(os.path.join(sdk_bin, "llvm-ranlib"))
        if os.path.isfile(cand):
            return ""                            # SDK 有就不用管
        return shutil.which("llvm-ranlib") or ""

    def _find_deps_preload(self):
        # 让依赖能被 find_package 找到。**不能靠 -DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH**：
        # ohos.toolchain 用普通 set()（非 CACHE）设了 ONLY，普通变量盖得住命令行 cache 变量，
        # 实测加了照样失败。CMAKE_PROJECT_TOP_LEVEL_INCLUDES 在 toolchain 之后、project() 之后、
        # 第一个 find_package 之前执行，这时改才压得住。
        #
        # 只给了顶层 <Pkg>_DIR 是不够的——依赖自己的 config 里还会做**嵌套 find_package**，
        # 那一层没人给得了 _DIR（实证：coal ← boost，BoostConfig.cmake 内部找 boost_headers
        # 失败，而 boost_headers-config.cmake 就在同一个 lib/cmake 下）。
        # 无依赖时返回 ""，不写这个文件——避免给纯粹无依赖的包放宽 find 语义。
        import os
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

    def build(self):
        # glfw/libjpeg-turbo/zstd/libxml2 同法：自发现 ohos.toolchain + 裸 cmake，绕开 conan_toolchain——
        # os=OHOS 下它把 CMAKE_SYSTEM_NAME 映射成 cmake 不认的值（ML-0035：System is unknown to cmake）。
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        src = os.path.join(self.source_folder, "")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",           # ohos.toolchain 64 位默认装 lib64/，须改回 lib
            # **configure 期就要给 INSTALL_PREFIX**，不能只靠 `cmake --install --prefix`：
            # GNUInstallDirs 的 CMAKE_INSTALL_FULL_*（如 FULL_MANDIR）是在 configure 期
            # 按当时的 prefix 算成**绝对路径**写进 install 规则的，`--prefix` 覆盖不到它。
            # brotli 实测：man 页 install 规则指向 /usr/local/share/man/man1，
            # 设备上报 "file cannot create directory ... Maybe need administrative privileges"。
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder),
            "-DBUILD_SHARED_LIBS=ON",
        ]
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs.append('-DCMAKE_RANLIB="{}"'.format(_rl))
        _pre = self._find_deps_preload()
        if _pre:
            defs.append('-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="{}"'.format(_pre))
        defs.append("-DCSPICE_PATCH_SOURCE=ON")
        defs.append("-DBUILD_SHARED_LIBS=ON")
        defs.append("-DCMAKE_POLICY_VERSION_MINIMUM=3.5")
        defs.append("-DBUILD_TESTING=ON")   # 使能上游 test_cspice（wrapper 自带的冒烟测试）
        # 依赖接线（find_package/find_library/pkg-config）须按需在此手工补 -D（见 SKILL「cmake 库依赖库」）：
        #   find_package(X CONFIG) → -DX_DIR=self.dependencies["x"].package_folder+"/lib/cmake/x"
        #   find_library/find_path → 预设目标库的 find 缓存变量为依赖真实路径（绕交叉链 FIND_ROOT_PATH=ONLY）
        # 喂本地源码，绕开上游的 FetchContent（设备联网慢且不可靠）：
        # 上游 CMakeLists 判 `if(DEFINED ENV{CSPICE_SRC})` 就不下载。
        import os as _os
        cspice_src = getattr(self, "_cspice_src_dir", None)
        if not cspice_src:
            # conan 复用缓存 source 目录时不会重新执行 source()，_cspice_src_dir 属性缺失，
            # 必须在 build() 内独立解析实际解压目录（官方包 cspice/ 或镜像包 cspice-master/）。
            for _cand in (os.path.join(self.source_folder, "cspice"),
                          os.path.join(self.source_folder, "cspice-master")):
                if os.path.isdir(_cand):
                    cspice_src = _cand
                    break
        if not cspice_src:
            raise ConanInvalidConfiguration("无法定位 CSPICE 源码目录（source_folder=%s）" % self.source_folder)
        _os.environ["CSPICE_SRC"] = cspice_src
        self.output.info("CSPICE_SRC=%s" % cspice_src)
        # wrapper 的 CSPICE::cspice target 的 BUILD_INTERFACE include 只含生成目录
        # （cspice_flavor.h），test_cspice.c 的 `#include <SpiceUsr.h>` 因此找不到头文件。
        # 显式把 CSPICE 源码 include/cspice 目录加入 C_FLAGS 搜索路径。
        _spice_inc = _os.path.join(cspice_src, "include", "cspice")
        if _os.path.isdir(_spice_inc):
            defs.append('-DCMAKE_C_FLAGS="-I{}"'.format(_spice_inc))
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}"'.format(bdir))
        # ── 上游测试（先签名测试二进制与构建树 .so，再运行；E077/E083）──
        self._sign_build_artifacts(bdir)
        ldpath = os.pathsep.join(filter(None, [
            os.path.join(bdir, "lib"),
            os.path.join(bdir, "src"),
        ]))
        old = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ldpath + (os.pathsep + old if old else "")
        self.run('ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(bdir))

    def _sign_build_artifacts(self, bdir):
        """签名构建树内的测试可执行文件与 .so，否则 OHOS 上 ctest 报 Operation not permitted（E077）。"""
        import glob
        targets = glob.glob(os.path.join(bdir, "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(bdir, "**", "*.so.*"), recursive=True)
        for _d in ("bin", "src", "tests", "c/tests"):
            _td = os.path.join(bdir, _d)
            if os.path.isdir(_td):
                for name in os.listdir(_td):
                    p = os.path.join(_td, name)
                    if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                        targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._flatten_cspice_headers()
        self._sign_binaries()

    def _flatten_cspice_headers(self):
        """整理头文件层级：wrapper 把 cspice/include/cspice/*.h 装成
        include/cspice/cspice/*.h（双层），而 CSPICE 消费惯用法是 `#include <SpiceUsr.h>`
        （其内部还会 include SpiceZpr.h 等同级头）。统一上移为 include/cspice/*.h。"""
        import shutil as _sh
        inc = os.path.join(self.package_folder, "include")
        outer = os.path.join(inc, "cspice")
        inner = os.path.join(outer, "cspice")
        if not os.path.isdir(inner):
            return
        for name in os.listdir(inner):
            src = os.path.join(inner, name)
            dst = os.path.join(outer, name)
            if os.path.isdir(src):
                if os.path.isdir(dst):
                    _sh.rmtree(dst)
                _sh.move(src, dst)
            elif os.path.isfile(src):
                if os.path.exists(dst):
                    os.remove(dst)
                _sh.move(src, dst)
        _sh.rmtree(inner)

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted（cmake/SDK-toolchain 产的自签无效，且 conan install 复制会破坏链接器自签）。
        # ① lib/ 的 .so  ② bin/ 的 ELF 可执行文件（llvm-config/xxx CLI 等）——产可执行文件的包必须签 bin。
        import glob, os
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        explicit_libs = ['cspice']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        # 上游把头装在 `include/cspice/` 下（install(DIRECTORY .. DESTINATION include/cspice)），
        # 但 CSPICE 的惯用法是 `#include <SpiceUsr.h>`（其内部还会 include SpiceZpr.h 等同级头）。
        # 故 includedirs 必须指到那一层，否则**任何消费方**都报 SpiceUsr.h not found。
        # 同类修法本会话在 urdfdom_headers / urdfdom 上也用过。
        self.cpp_info.includedirs = ["include/cspice"]
        self.cpp_info.set_property("cmake_file_name", "cspice")
        self.cpp_info.set_property("cmake_target_name", "cspice::cspice")
        pkg = "" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        import os
        for _env in []:
            _k, _v = _env.split("=", 1)
            self.runenv_info.define_path(_k, os.path.join(self.package_folder, _v))

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
