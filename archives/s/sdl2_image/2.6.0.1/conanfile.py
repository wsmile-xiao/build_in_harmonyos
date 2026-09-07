#!/usr/bin/env python3
"""Conan recipe - sdl2_image 2.6.0.1 (SDL_image image loading library).

CMake build system, C. Requires sdl2/2.30.10.1 (mandatory) plus
libpng/1.6.58, libjpeg-turbo/3.2.0 and libwebp/1.6.0 (format support).
OHOS adaptation notes (AssaultCube / PC 赛道二专用小版本):
  - 采用 libpng 后端（SDL2IMAGE_BACKEND_STB=OFF + SDL2IMAGE_PNG=ON）以正确解码
    AssaultCube 字体的「灰度+alpha」PNG；libpng 能原生解码 color type 4（LA）。
  - JPEG 走 libjpeg-turbo（SDL2IMAGE_JPG=ON），WebP 走 libwebp（SDL2IMAGE_WEBP=ON）。
  - 禁用 libtiff（SDL2IMAGE_TIF=OFF）：OHOS 上 libtiff 无预编译二进制且依赖
    zstd 链（E 系列），裁剪掉以避免构建失败。
  - 依赖 sdl2/2.30.10.1（含 0006 EGL 回退补丁，OHOS 上 libEGL 无
    eglQueryDevicesEXT 时回退 eglGetDisplay(EGL_DEFAULT_DISPLAY)）。
  - Static library (BUILD_SHARED_LIBS=OFF); SDL2IMAGE_DEPS_SHARED=OFF
    (direct linking, no dlopen); SDL2IMAGE_VENDORED=OFF (release tarball
    has no external/ submodule content).
  - E092: CMake does not know HarmonyOS; use CMAKE_SYSTEM_NAME=Linux with
    CMAKE_SYSTEM_PROCESSOR=aarch64; CMake 4.x needs CMAKE_POLICY_VERSION_MINIMUM.
  - SDL2 lookup: upstream sdl_find_sdl2 tries config mode then the private
    FindSDL2 module - inject SDL2_INCLUDE_DIR/SDL2_LIBRARY so the module
    mode works (same approach as sdl2_mixer 2.8.1).
  - PNG/JPG: upstream uses find_package(PNG)/find_package(JPEG)
    (PNG::PNG / JPEG::JPEG targets); override cmake_file_name and
    cmake_target_name in CMakeDeps so the config mode resolves to the
    Conan-provided libpng / libjpeg-turbo.
  - WEBP uses upstream cmake/Findwebp.cmake (module mode); CMAKE_PREFIX_PATH
    points at the libwebp package.
  - libpng/libjpeg-turbo/libwebp currently only have shared binaries;
    SDL2_image links their .so directly. Link-time -L/-rpath-link resolve
    transitive NEEDED; runtime lookup via conanrun env.
  - Upstream test: ctest single test testimage (test/CMakeLists.txt add_test),
    SDL_VIDEODRIVER=dummy preset by TESTS_ENVIRONMENT; official CI env
    REQUIRE_LOAD_* (AVIF/JXL/TIF disabled here, matching the official Autotools
    CI scope); test binary must be ELF-signed on OHOS.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

import glob
import os
import shutil

class Sdl2ImageConan(ConanFile):
    name = "sdl2_image"
    version = "2.6.0.1"
    description = "SDL_image - image loading library (many formats) for SDL2"
    license = "Zlib"
    homepage = "https://github.com/libsdl-org/SDL_image"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10.1")
        self.requires("libpng/1.6.58")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libwebp/1.6.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _prepare_shared_mirror(self, pkg):
        """OHOS 容器禁止 stat/unlink conan 缓存内的 .so 符号链接，导致 CMakeDeps /
        find_library 无法访问库。把包内可访问的实体 .so 复制到可写镜像目录，并生成
        去版本化的实体别名（保留 SONAME / find_library 需要的名字），随后重定向该
        依赖的 libdirs/includedirs。这样 CMakeDeps 的 find_library 与运行时动态加载
        都能命中实体文件。"""
        src = pkg.package_folder
        mirror = os.path.join(self.build_folder, "mirror_" + pkg.ref.name)
        libdir = os.path.join(mirror, "lib")
        incdir = os.path.join(mirror, "include")
        shutil.rmtree(mirror, ignore_errors=True)
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(incdir, exist_ok=True)
        # 只复制实体文件（HMDFS 不跟踪符号链接，符号链接不可访问，os.stat 会失败）。
        # 头文件既保留目录结构，也平铺到 include 根，便于 find_package 命中 png.h 等。
        si = os.path.join(src, "include")
        if os.path.isdir(si):
            for dp, dn, fns in os.walk(si):
                for fn in fns:
                    fp = os.path.join(dp, fn)
                    try:
                        st = os.stat(fp)
                    except OSError:
                        continue
                    if st.st_mode & 0o170000 != 0o100000:
                        continue
                    rel = os.path.relpath(fp, si)
                    dst = os.path.join(incdir, rel)
                    os.makedirs(os.path.dirname(dst) or incdir, exist_ok=True)
                    shutil.copy(fp, dst)
                    # 平铺到 include 根（确保 png.h / webp 头文件路径可用）
                    base = os.path.join(incdir, fn)
                    if not os.path.exists(base):
                        shutil.copy(fp, base)

        # 实体 .so 复制 + 去版本化别名（libfoo.so.A.B.C -> libfoo.so.A / libfoo.so）
        sl = os.path.join(src, "lib")
        if os.path.isdir(sl):
            entities = []
            for fn in os.listdir(sl):
                fp = os.path.join(sl, fn)
                try:
                    if os.stat(fp).st_mode & 0o170000 == 0o100000:
                        entities.append((fp, fn))
                except OSError:
                    continue
            for fp, fn in entities:
                shutil.copy(fp, os.path.join(libdir, fn))
            for _, fn in entities:
                base, sep, rest = fn.partition(".so")
                if not sep or not rest:
                    continue
                ver = rest[1:]
                if not ver:
                    continue
                parts = ver.split(".")
                # 生成 libfoo.so.A.B.C / .A.B / .A（版本化实体名）
                for k in range(len(parts)):
                    alias = base + ".so." + ".".join(parts[:len(parts) - k])
                    if not os.path.exists(os.path.join(libdir, alias)):
                        shutil.copy(os.path.join(libdir, fn), os.path.join(libdir, alias))
                # 生成无版本 libfoo.so（find_library 最常用名）
                alias = base + ".so"
                if not os.path.exists(os.path.join(libdir, alias)):
                    shutil.copy(os.path.join(libdir, fn), os.path.join(libdir, alias))

        # 重定向 libdirs / includedirs 到镜像；子目录 include（如 libpng16/ webp/）一并加入
        _ci = pkg.cpp_info
        _ci.libdirs = [libdir]
        _incs = [incdir]
        if os.path.isdir(incdir):
            for sub in sorted(os.listdir(incdir)):
                subp = os.path.join(incdir, sub)
                if os.path.isdir(subp):
                    _incs.append(subp)
        _ci.includedirs = _incs
        self.output.info("shared mirror for %s -> %s\n  incs=%s" % (pkg.ref.name, libdir, _incs))

    def generate(self):
        # OHOS 容器禁止访问 conan 缓存内的 .so 符号链接：为 shared 依赖库准备
        # 实体镜像并重定向其 libdirs/includedirs，使 CMakeDeps / find_library 可找到。
        for _pkg in ("libpng", "libjpeg-turbo", "libwebp"):
            _dep = self.dependencies.get(_pkg)
            if _dep and _dep.package_folder:
                self._prepare_shared_mirror(_dep)

        deps = CMakeDeps(self)
        # Upstream links PNG::PNG / JPEG::JPEG; Conan recipes expose
        # libpng::libpng / libjpeg-turbo::libjpeg-turbo. Align both name
        # and config file so find_package(PNG)/find_package(JPEG) work.
        deps.set_property("libpng", "cmake_file_name", "PNG")
        deps.set_property("libpng", "cmake_target_name", "PNG::PNG")
        deps.set_property("libjpeg-turbo", "cmake_file_name", "JPEG")
        deps.set_property("libjpeg-turbo", "cmake_target_name", "JPEG::JPEG")
        deps.generate()

        # 用 Ninja：OHOS 容器 /bin/sh 为 execute-only，GNU make 会因 stat /bin/sh 失败；
        # Ninja 直接 exec /bin/sh 并不做该检查，且 conan 对 ninja 不追加 `-- -jN`。
        tc = CMakeToolchain(self, generator="Ninja")
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # OHOS 容器 /bin/sh 为 execute-only，CMake 试编译(用 make//bin/sh)会
        # Permission denied；标记编译器已可用以跳过 try-compile，避免 configure 失败。
        tc.cache_variables["CMAKE_C_COMPILER_WORKS"] = "TRUE"

        # SDL2: injected find variables used when sdl_find_sdl2 falls back to
        # the private FindSDL2 module
        sdl2 = self.dependencies["sdl2"]
        if sdl2.package_folder:
            tc.cache_variables["SDL2_INCLUDE_DIR"] = os.path.join(sdl2.package_folder, "include/SDL2")
            tc.cache_variables["SDL2_LIBRARY"] = os.path.join(sdl2.package_folder, "lib/libSDL2.a")

        # webp: SDL_image 用自带 Findwebp.cmake（模块），find_library 找不到符号链接库，
        # 注入指向实体镜像的变量，使 find_package(webp) 命中（libwebp.so 实体 + include）。
        _webp = self.dependencies.get("libwebp")
        if _webp and _webp.package_folder:
            _ml = os.path.join(self.build_folder, "mirror_libwebp", "lib")
            _mi = os.path.join(self.build_folder, "mirror_libwebp", "include")
            if os.path.isfile(os.path.join(_ml, "libwebp.so")):
                tc.cache_variables["webp_LIBRARY"] = os.path.join(_ml, "libwebp.so")
                tc.cache_variables["webp_INCLUDE_PATH"] = _mi

        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["SDL2IMAGE_INSTALL"] = "ON"
        tc.variables["SDL2IMAGE_DEPS_SHARED"] = "OFF"
        tc.variables["SDL2IMAGE_VENDORED"] = "OFF"
        tc.variables["SDL2IMAGE_SAMPLES"] = "OFF"
        tc.variables["SDL2IMAGE_TESTS"] = "ON"
        tc.variables["SDL2IMAGE_TESTS_INSTALL"] = "OFF"
        tc.variables["SDL2IMAGE_TIF"] = "OFF"
        tc.variables["SDL2IMAGE_WEBP"] = "ON"
        tc.variables["SDL2IMAGE_PNG"] = "ON"
        tc.variables["SDL2IMAGE_JPG"] = "ON"
        tc.variables["SDL2IMAGE_AVIF"] = "OFF"
        tc.variables["SDL2IMAGE_JXL"] = "OFF"
        tc.variables["SDL2IMAGE_BACKEND_STB"] = "OFF"
        tc.generate()

        # Shared .so transitive deps (libpng.so/libjpeg.so/libwebp.so -> zlib):
        # -L + -rpath-link resolve NEEDED at link time
        libdirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                for ld in dep.cpp_info.libdirs:
                    if ld and os.path.isdir(ld) and ld not in libdirs:
                        libdirs.append(ld)
        if libdirs:
            flags = " ".join("-L{0} -Wl,-rpath-link,{0}".format(d) for d in libdirs)
            tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = flags
            tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = flags

        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # OHOS /bin/sh execute-only，GNU make 默认 SHELL=/bin/sh 无法执行；Ninja 无此问题。
        cmake.build(cli_args=["--parallel", "1"])

        # testimage is an executable ELF; OHOS requires code signing before run
        for tb in glob.glob(os.path.join(self.build_folder, "**", "testimage"), recursive=True):
            if os.path.isfile(tb):
                self._sign_elf(tb)

        # Upstream official test: ctest single test testimage.
        # SDL_VIDEODRIVER=dummy + SDL_TEST_SRCDIR/SDL_TEST_BUILDDIR are preset by
        # TESTS_ENVIRONMENT in test/CMakeLists.txt; add the official CI
        # REQUIRE_LOAD_* assertion env (AVIF/JXL/TIF not built here -> 0).
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_AVIF"] = "0"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_BMP"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_CUR"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_GIF"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_ICO"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_JPG"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_JXL"] = "0"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_LBM"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_PCX"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_PNG"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_PNM"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_QOI"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_SVG"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_TGA"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_TIF"] = "0"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_WEBP"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_XPM"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_LOAD_XV"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_SAVE_JPG"] = "1"
        os.environ["SDL_IMAGE_TEST_REQUIRE_SAVE_PNG"] = "1"
        # OHOS 符号链接限制：testimage 运行时需从实体镜像加载 libpng/libwebp 共享库。
        # 显式把镜像 libdir 加入 LD_LIBRARY_PATH（不依赖 conanrun 是否已含镜像路径）。
        _mldirs = [
            os.path.join(self.build_folder, "mirror_libpng", "lib"),
            os.path.join(self.build_folder, "mirror_libjpeg-turbo", "lib"),
            os.path.join(self.build_folder, "mirror_libwebp", "lib"),
        ]
        _mldirs = [d for d in _mldirs if os.path.isdir(d)]
        if _mldirs:
            _old = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = ":".join(_mldirs) + (":" + _old if _old else "")
        self.run("ctest --output-on-failure", cwd=self.build_folder,
                 env=["conanbuild", "conanrun"])

    def _sign_elf(self, path):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null'.format(oc=objcopy, f=path), ignore_errors=True)
        tmp = path + ".signed"
        self.run('{sg} sign -inFile "{f}" -outFile "{t}" -selfSign 1'.format(sg=signer, f=path, t=tmp))
        if os.path.exists(tmp):
            shutil.move(tmp, path)
        os.chmod(path, 0o755)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["SDL2_image"]
        # Static lib transitively needs SDL2 and the directly linked shared libs
        self.cpp_info.requires = ["sdl2::sdl2", "libpng::libpng", "libjpeg-turbo::libjpeg-turbo", "libwebp::libwebp"]
        # Upstream installs headers into include/SDL2/; SDL_image.h does
        # #include "SDL.h", so consumers need include/SDL2 on the path
        self.cpp_info.includedirs = ["include/SDL2", "include"]
        sdl2 = self.dependencies["sdl2"]
        if sdl2.package_folder:
            self.cpp_info.includedirs.append(os.path.join(sdl2.package_folder, "include/SDL2"))
