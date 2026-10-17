#!/usr/bin/env python3
"""Conan recipe — sdl3 3.4.8 (CMake).

SDL3 is the Simple DirectMedia Layer 3, a cross-platform multimedia library.
HarmonyOS platform adaptation patches are included.

The package defaults to a shared library: sdl2-compat (the SDL2 compatibility
layer built on SDL3) resolves libSDL3.so.0 with dlopen() at runtime, and a
shared build is SDL3's canonical distribution form.

The Wayland video backend is enabled by default (`-o sdl3/*:wayland=False` turns
it off): Wayland is the display protocol on HarmonyOS PC. Enabling it requires
the recipe to self-sign the wayland-scanner copy, to generate the egl.pc that
the OHOS sysroot does not ship, and to inject the dependency .pc/include paths
— see _build_env() and _wayland_scanner().
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

_SIGN_TOOL = "/data/service/hnp/bin/binary-sign-tool"
_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"


class Sdl3Conan(ConanFile):
    name = "sdl3"
    version = "3.4.8"
    description = "Simple DirectMedia Layer 3 - cross-platform multimedia library"
    license = "MIT"
    homepage = "https://www.libsdl.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    # Wayland 是 HarmonyOS PC 的显示协议，默认开启；关闭仅用于对照构建。
    options = {"wayland": [True, False]}
    default_options = {"wayland": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if not self.options.wayland:
            return
        # OHOS PC 的显示协议是 Wayland：wayland 提供 wayland-client/-cursor/-egl
        # 与构建期 wayland-scanner；libxkbcommon 提供键盘映射。
        self.requires("wayland/1.24.0")
        self.requires("libxkbcommon/1.13.1")
        # wayland-client.pc 的 Requires 链引用 libffi，libxml2 是 wayland-scanner
        # 的运行时依赖。纯传递依赖会被 conan 标记为 Skipped binaries 不落盘，
        # pkg-config 解析 .pc 与执行 scanner 都会失败（hyprpicker 同款处理），
        # 故提升为直接 requires。
        self.requires("libffi/3.4.4")
        self.requires("libxml2/2.15.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── 构建期工具：签名后的 wayland-scanner（E077）─────────────────────
    def _sign_elf(self, path):
        """用设备自带签名工具自签名 ELF；返回 True 表示签名成功。

        OHOS 的安全机制拒绝执行未签名二进制（E077），而 conan 缓存中的
        构建期工具是未签名的；先清掉可能存在的旧签名段再重签。
        """
        if not (os.path.isfile(_SIGN_TOOL) and os.path.isfile(_OBJCOPY)):
            return False
        signed = path + ".signed"
        subprocess.run([_OBJCOPY, "--remove-section", ".codesign", path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        proc = subprocess.run(
            [_SIGN_TOOL, "sign", "-inFile", path, "-outFile", signed,
             "-selfSign", "1"],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if proc.returncode != 0 or not os.path.isfile(signed):
            return False
        os.replace(signed, path)
        os.chmod(path, 0o755)
        return True

    def _wayland_scanner(self):
        """返回可用于构建的 wayland-scanner；OHOS 上返回签名副本。"""
        dep = self.dependencies.get("wayland")
        src = None
        if dep and dep.package_folder:
            candidate = os.path.join(dep.package_folder, "bin", "wayland-scanner")
            if os.path.isfile(candidate):
                src = candidate
        if src is None:
            self.output.warning("sdl3: wayland 包内未找到 wayland-scanner")
            return None
        if self.settings.os != "OHOS":
            return src
        # 不改动依赖包目录，复制到生成目录后签名
        target_dir = os.path.join(self.generators_folder, "wayland-scanner-bin")
        os.makedirs(target_dir, exist_ok=True)
        target = os.path.join(target_dir, "wayland-scanner")
        shutil.copy2(src, target)
        if self._sign_elf(target):
            self.output.info(f"sdl3: wayland-scanner 已自签名 -> {target}")
            return target
        self.output.warning("sdl3: wayland-scanner 签名失败，回退未签名副本")
        return src

    def _ohos_sysroot(self):
        """定位 OHOS sysroot（用于补齐 SDK 缺失的 egl.pc）。"""
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        cc = compilers.get("c")
        if cc:
            real = os.path.realpath(shutil.which(cc) or cc)
            # <sdk>/ohos/native/llvm/bin/clang -> <sdk>/ohos/native/sysroot
            native = os.path.dirname(os.path.dirname(os.path.dirname(real)))
            candidate = os.path.join(native, "sysroot")
            if os.path.isdir(os.path.join(candidate, "usr", "include", "EGL")):
                return candidate
        env_sysroot = os.environ.get("OHOS_SYSROOT")
        if env_sysroot and os.path.isdir(env_sysroot):
            return env_sysroot
        return None

    def _ensure_egl_pc(self):
        """OHOS SDK 的 sysroot 只有 EGL 头文件与 libEGL.so，没有 egl.pc。

        SDL3 的 Wayland 探测是 pkg_check_modules 一次性检查
        「wayland-client>=1.18 wayland-egl wayland-cursor egl xkbcommon>=0.5.0」，
        缺 egl.pc 会让整个 Wayland 后端被判为不可用。按 sysroot 实际布局生成
        最小 egl.pc，返回其目录供 PKG_CONFIG_PATH 使用。
        """
        sysroot = self._ohos_sysroot()
        if not sysroot:
            self.output.warning("sdl3: 未定位到 OHOS sysroot，跳过 egl.pc 补齐")
            return None
        shim_dir = os.path.join(self.generators_folder, "shim-pkgconfig")
        os.makedirs(shim_dir, exist_ok=True)
        libdir = os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos")
        if not os.path.isdir(libdir):
            libdir = os.path.join(sysroot, "usr", "lib")
        content = (
            "# OHOS SDK sysroot 未提供 egl.pc，由配方按实际布局生成\n"
            "Name: egl\n"
            "Description: EGL client library (OHOS SDK sysroot)\n"
            "Version: 1.5\n"
            f"Libs: -L{libdir} -lEGL\n"
            f"Cflags: -I{os.path.join(sysroot, 'usr', 'include')}\n"
        )
        path = os.path.join(shim_dir, "egl.pc")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        self.output.info(f"sdl3: 生成 {path}（SDK 未提供 egl.pc）")
        return shim_dir

    def _pkgconfig_overlay(self, pc_pairs):
        """把依赖包 .pc 的 prefix 改写为包内真实路径，返回覆写目录。

        wayland/libxkbcommon 等包内的 .pc 保留了上游原样的 `prefix=/`，pkg-config
        因而产出 `-I//include`、`-L//lib` 这类无效路径。编译期只是多一个无效 -I，
        但 CMake 在 generate 阶段校验 PkgConfig::* imported target 的
        INTERFACE_INCLUDE_DIRECTORIES 时会直接报错（`includes non-existent path
        "//include"`）而 configure 失败。这里把 .pc 复制到覆写目录、把 prefix=
        指向依赖包根，覆写目录排在 PKG_CONFIG_PATH 最前，依赖包目录本身不动。
        """
        overlay = os.path.join(self.generators_folder, "shim-pkgconfig", "overlay")
        os.makedirs(overlay, exist_ok=True)
        for folder, pc_dir in pc_pairs:
            for name in sorted(os.listdir(pc_dir)):
                if not name.endswith(".pc"):
                    continue
                with open(os.path.join(pc_dir, name), "r",
                          encoding="utf-8", errors="replace") as fh:
                    lines = fh.readlines()
                with open(os.path.join(overlay, name), "w",
                          encoding="utf-8", newline="\n") as fh:
                    for line in lines:
                        if line.startswith("prefix="):
                            line = f"prefix={folder}\n"
                        fh.write(line)
        self.output.info(f"sdl3: 依赖 .pc 已改写 prefix -> {overlay}")
        return overlay

    def _build_env(self):
        """构建期环境：依赖包 .pc 路径 + scanner 运行期库路径。

        conan 的 CMake 工具链只把 generators 目录塞进 PKG_CONFIG_PATH，并不包含
        依赖包的 .pc 目录；SDL3 用 pkg_check_modules 探测 wayland/xkbcommon，因此
        必须在 configure/build 时显式应用本环境（lite-xl 配方同款写法）。
        """
        env = Environment()
        pc_paths, lib_paths, pc_pairs = [], [], []
        if self.settings.os == "OHOS":
            shim_dir = self._ensure_egl_pc()
            if shim_dir:
                pc_paths.append(shim_dir)
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            pc_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pc_dir):
                pc_pairs.append((dep.package_folder, pc_dir))
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                lib_paths.append(lib_dir)
        if pc_pairs:
            # 只挂覆写目录：依赖包原始 .pc 的 prefix=/ 会让 CMake 校验失败
            pc_paths.insert(0, self._pkgconfig_overlay(pc_pairs))
        if pc_paths:
            env.define("PKG_CONFIG_PATH", os.pathsep.join(pc_paths))
        # wayland-scanner 动态链接 libxml2 等依赖库，运行期需要库搜索路径；
        # 系统默认路径里另有版本不匹配的 libxml2，必须先命中 conan 的副本
        if lib_paths:
            env.define("LD_LIBRARY_PATH", os.pathsep.join(lib_paths))
        return env

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SDL_SHARED"] = "ON"
        tc.variables["SDL_STATIC"] = "OFF"
        tc.variables["SDL_PTHREADS"] = "ON"
        tc.variables["SDL_TRAY"] = "OFF"
        # Build the upstream test directory so the non-interactive suite can
        # run during packaging (R51). Tests are not installed into the
        # package (SDL_INSTALL_TESTS defaults to OFF).
        tc.variables["SDL_TESTS"] = "ON"
        # Patch 0001 sets UNIX_SYS=ON so HarmonyOS gets the POSIX paths
        # (pthread, unix time/fs), but that also flips the desktop-Linux
        # backend defaults (X11, Wayland, ALSA, ...) to ON. X11 and the desktop
        # audio stacks do not exist on HarmonyOS, so disable them explicitly.
        # This also makes builds deterministic on CI workers that carry stale
        # pkg-config entries: a leftover fribidi.pc made SDL3's CheckFribidi
        # create PkgConfig::PC_FRIBIDI with a non-existent include dir, failing
        # CMake generation (SDL_FRIBIDI is force-ON while SDL_X11 is still
        # undetected, because its dep_option is evaluated before CheckX11).
        #
        # Wayland stays ON (option `wayland`, default True) because it is the
        # display protocol on HarmonyOS PC. SDL3's Wayland probe is one
        # pkg_check_modules over wayland-client/wayland-egl/wayland-cursor/egl/
        # xkbcommon, so the recipe now (1) puts the dependency .pc dirs into
        # PKG_CONFIG_PATH, (2) generates the egl.pc the OHOS sysroot does not
        # ship, (3) adds the dependency include dirs since the dependency .pc
        # files use prefix "/" (pkg-config would emit -I//include), and
        # (4) self-signs the wayland-scanner copy (OHOS refuses unsigned ELF).
        tc.variables["SDL_X11"] = "OFF"
        tc.variables["SDL_WAYLAND"] = "ON" if self.options.wayland else "OFF"
        # Wayland 后端走动态加载（SDL_WAYLAND_SHARED=ON，其 dep_option 条件还要求
        # SDL_DEPS_SHARED=ON）：SDL3-shared 不再硬依赖 libwayland-egl/-client/-cursor、
        # libEGL 与 libxkbcommon，改为运行期 dlopen，避免共享库带上这些 DT_NEEDED
        # 后测试与消费方都必须把 conan 依赖包 lib 目录塞进加载器搜索路径。
        # 这两个是 SDL 自己的 option（cache 变量），必须用 cache_variables 下发。
        tc.cache_variables["SDL_DEPS_SHARED"] = "ON" if self.options.wayland else "OFF"
        tc.cache_variables["SDL_WAYLAND_SHARED"] = "ON" if self.options.wayland else "OFF"
        tc.variables["SDL_KMSDRM"] = "OFF"
        tc.variables["SDL_RPI"] = "OFF"
        tc.variables["SDL_ROCKCHIP"] = "OFF"
        tc.variables["SDL_FRIBIDI"] = "OFF"
        tc.variables["SDL_LIBTHAI"] = "OFF"
        tc.variables["SDL_ALSA"] = "OFF"
        tc.variables["SDL_JACK"] = "OFF"
        tc.variables["SDL_PIPEWIRE"] = "OFF"
        tc.variables["SDL_PULSEAUDIO"] = "OFF"
        tc.variables["SDL_SNDIO"] = "OFF"
        # CMake does not know the HarmonyOS platform, so it leaves
        # CMAKE_SHARED_LIBRARY_SONAME_C_FLAG empty and drops the SONAME and
        # version symlinks. Inject the flag so libSDL3.so.0 (the SONAME that
        # sdl2-compat dlopen()s at runtime) is produced together with
        # libSDL3.so.<SDL_SO_VERSION> and the libSDL3.so symlink.
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        if self.options.wayland:
            # 依赖包内 .pc 的 prefix 是 "/"（pkg-config 会给出 -I//include 这类
            # 无效路径）：_build_env() 用覆写目录修正 prefix，这里再显式补上依赖
            # 包 include 路径，覆盖没有 .pc 的依赖（与设备上验证过的配置一致）
            includes = []
            for dep in self.dependencies.values():
                if dep.package_folder:
                    inc = os.path.join(dep.package_folder, "include")
                    if os.path.isdir(inc):
                        includes.append(inc)
            if includes:
                tc.extra_cflags.extend([f"-I{p}" for p in includes])
                tc.extra_cxxflags.extend([f"-I{p}" for p in includes])
            scanner = self._wayland_scanner()
            if scanner:
                tc.variables["WAYLAND_SCANNER"] = scanner
            self._build_env().vars(self).save_script("conanbuild_env")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        if self.options.wayland:
            # 依赖包 .pc 与签名 scanner 的运行期库路径必须在 configure/build 内生效
            with self._build_env().vars(self).apply():
                cmake.configure()
                cmake.build()
        else:
            cmake.configure()
            cmake.build()
        if can_run(self):
            # Upstream non-interactive suite: CTest only registers programs
            # marked SDL_NONINTERACTIVE and already injects the dummy
            # video/audio drivers via TESTS_ENVIRONMENT.
            #
            # testrwlock is excluded: the OHOS musl pthread_rwlock has no
            # writer-queue fairness (a waiting writer does not block new
            # readers), so under testrwlock's saturated reader pattern
            # (6 readers holding the lock 1000ms with 10ms gaps) the writer
            # thread starves forever and the test deadlocks. A bare
            # pthread_rwlock probe confirms single write-lock acquisition
            # works fine, and --nbthreads 1 (unsaturated) passes, so this is
            # a libc fairness difference vs glibc/macOS/Windows, not an SDL
            # logic defect. The SDL_RWLock API does not promise writer
            # priority. All other 24 registered tests run.
            environment = Environment()
            environment.prepend_path("LD_LIBRARY_PATH", self.build_folder)
            # 依赖包 lib 目录：动态加载形态下用不到，静态链接形态下
            # SDL3-shared 会硬依赖 libwayland-*/libxkbcommon，ctest 需要能找到
            for dep in self.dependencies.values():
                dep_lib = os.path.join(dep.package_folder or "", "lib")
                if dep.package_folder and os.path.isdir(dep_lib):
                    environment.prepend_path("LD_LIBRARY_PATH", dep_lib)
            with environment.vars(self).apply():
                # ctest 通过 env="conanbuild" 运行时，conan 生成的脚本会用依赖 lib
                # 目录整体替换 LD_LIBRARY_PATH，把 build 目录丢掉；而 SDL 的测试
                # 可执行文件本身没有 RPATH（libSDL3.so.0 是一条普通 NEEDED），
                # 因此在命令内部重新拼一次，确保 build 目录一定在搜索路径里。
                lib_paths = [self.build_folder]
                for dep in self.dependencies.values():
                    dep_lib = os.path.join(dep.package_folder or "", "lib")
                    if dep.package_folder and os.path.isdir(dep_lib):
                        lib_paths.append(dep_lib)
                ld_library_path = os.pathsep.join(lib_paths)
                self.run(
                    f'LD_LIBRARY_PATH="{ld_library_path}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}" '
                    "ctest --output-on-failure --timeout 180 -E '^testrwlock$'",
                    cwd=self.build_folder,
                    env="conanbuild",
                )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["SDL3"]
        self.cpp_info.set_property("pkg_config_name", "sdl3")
        self.cpp_info.set_property("cmake_file_name", "SDL3")
        self.cpp_info.set_property("cmake_target_name", "SDL3::SDL3")
