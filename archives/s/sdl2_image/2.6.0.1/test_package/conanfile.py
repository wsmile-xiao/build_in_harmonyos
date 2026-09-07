#!/usr/bin/env python3
"""Conan test_package for sdl2_image 2.6.0.1 (library).

Compile a small program linking libSDL2_image.a, call SDL_image APIs
(IMG_Init / IMG_Load_RW) and verify PNG/JPG/WEBP formats are wired and that a
grayscale+alpha PNG (color type 4, the AssaultCube font format) decodes
correctly via the libpng backend.
OHOS: the test executable must be ELF-signed (binary-sign-tool) before it
can run, otherwise it fails with Operation not permitted. Runtime shared
deps (libpng.so/libjpeg.so/libwebp.so) are provided by the conanrun env.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class Sdl2ImageTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _prepare_shared_mirror(self, pkg):
        """OHOS 容器禁止访问 conan 缓存内的 .so 符号链接。把包内实体 .so 复制到可写
        镜像目录并生成无版本实体别名，随后重定向该依赖的 libdirs/includedirs，
        使 CMakeDeps 的 find_library 命中实体文件。"""
        src = pkg.package_folder
        mirror = os.path.join(self.build_folder, "mirror_" + pkg.ref.name)
        libdir = os.path.join(mirror, "lib")
        incdir = os.path.join(mirror, "include")
        shutil.rmtree(mirror, ignore_errors=True)
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(incdir, exist_ok=True)
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
                    base = os.path.join(incdir, fn)
                    if not os.path.exists(base):
                        shutil.copy(fp, base)
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
                for k in range(len(parts)):
                    alias = base + ".so." + ".".join(parts[:len(parts) - k])
                    if not os.path.exists(os.path.join(libdir, alias)):
                        shutil.copy(os.path.join(libdir, fn), os.path.join(libdir, alias))
                alias = base + ".so"
                if not os.path.exists(os.path.join(libdir, alias)):
                    shutil.copy(os.path.join(libdir, fn), os.path.join(libdir, alias))
        _ci = pkg.cpp_info
        _ci.libdirs = [libdir]
        _incs = [incdir]
        if os.path.isdir(incdir):
            for sub in sorted(os.listdir(incdir)):
                subp = os.path.join(incdir, sub)
                if os.path.isdir(subp):
                    _incs.append(subp)
        _ci.includedirs = _incs

    def generate(self):
        # OHOS 符号链接限制：为 shared 依赖库准备实体镜像并重定向 libdirs/includedirs
        for dep in self.dependencies.values():
            if dep.ref.name in ("libpng", "libjpeg-turbo", "libwebp"):
                self._prepare_shared_mirror(dep)
        # 运行时 LD_LIBRARY_PATH 需包含镜像实体库（OHOS 符号链接限制）供 test 运行
        for dep in self.dependencies.values():
            if dep.ref.name in ("libpng", "libjpeg-turbo", "libwebp"):
                _lib = os.path.join(self.build_folder, "mirror_" + dep.ref.name, "lib")
                if os.path.isdir(_lib):
                    self.runenv_info.append_path("LD_LIBRARY_PATH", _lib)
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self, generator="Ninja")
        # OHOS /bin/sh execute-only：跳过 try-compile，避免 configure 失败
        tc.cache_variables["CMAKE_C_COMPILER_WORKS"] = "TRUE"
        # webp: SDL_image Findwebp.cmake 走模块，注入指向实体镜像的变量
        for dep in self.dependencies.values():
            if dep.ref.name == "libwebp":
                _ml = os.path.join(self.build_folder, "mirror_libwebp", "lib")
                _mi = os.path.join(self.build_folder, "mirror_libwebp", "include")
                if os.path.isfile(os.path.join(_ml, "libwebp.so")):
                    tc.cache_variables["webp_LIBRARY"] = os.path.join(_ml, "libwebp.so")
                    tc.cache_variables["webp_INCLUDE_PATH"] = _mi
                break
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._sign_test_binary()

    def _sign_test_binary(self):
        bindir = os.path.join(self.cpp.build.bindirs[0])
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in os.listdir(bindir):
            path = os.path.join(bindir, f)
            if not os.path.isfile(path) or not os.access(path, os.X_OK):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null'.format(oc=objcopy, f=path), ignore_errors=True)
            tmp = path + ".signed"
            self.run('{sg} sign -inFile "{f}" -outFile "{t}" -selfSign 1'.format(sg=signer, f=path, t=tmp))
            if os.path.exists(tmp):
                shutil.move(tmp, path)
            # binary-sign-tool output may lose the exec bit; restore it
            os.chmod(path, 0o755)

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_sdl2_image")
        assert os.path.isfile(test_bin), f"test binary not found: {test_bin}"
        # headless run: use SDL dummy video driver
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        # OHOS 符号链接限制：运行时动态加载器需从镜像目录加载实体库
        # (libpng16.so.16 / libwebp.so.7 / libsharpyuv.so.0 等)，故显式设 LD_LIBRARY_PATH
        libs = []
        for dep in self.dependencies.values():
            if dep.ref.name in ("libpng", "libjpeg-turbo", "libwebp"):
                _lib = os.path.join(self.build_folder, "mirror_" + dep.ref.name, "lib")
                if os.path.isdir(_lib):
                    libs.append(_lib)
        if libs:
            self.run("env LD_LIBRARY_PATH={ld} '{bin}'".format(ld=":".join(libs), bin=test_bin))
        else:
            self.run("'{bin}'".format(bin=test_bin))
