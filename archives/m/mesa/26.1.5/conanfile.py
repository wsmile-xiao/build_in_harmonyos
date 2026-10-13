#!/usr/bin/env python3
"""Conan recipe — mesa 26.1.5（Mesa 3D 图形库，HarmonyOS PC 适配）

Conan 包版本 26.1.5 与上游 Mesa 26.1.5 一一对应（真版本升级）。

交付范围（headless 图形栈）：
  EGL（surfaceless + GBM 平台）、OpenGL ES 1.1 / 2.0、GBM、Gallium
  llvmpipe + softpipe 软件渲染器。

⚠ 与 24.3.4 系列的关键差异：**上游 Mesa 已在 25.1.0 移除 OSMesa**
（docs/relnotes/25.1.0.rst:2459 "Remove osmesa"；
  docs/relnotes/25.2.0.rst:4724 "meson: remove unused osmesa option"），
  26.1.5 源码树中已不存在 `-Dosmesa` 选项与 `src/gallium/targets/osmesa`
  目标。因此本版本不再交付 libOSMesa，改为交付 OHOS 桌面栈实际消费的
  libEGL / libGLESv2 / libGLESv1_CM / libgbm / libgallium 组合，
  离屏渲染由 EGL pbuffer/surfaceless + llvmpipe 承担（与 OSMesa 等价用途）。

OHOS 适配点：
- harmonyos 纳入 DRM/KMS 平台集合（libdrm 用户态存在），使 -Dgbm=enabled 通过
- harmonyos 纳入 _GNU_SOURCE 平台列表（clock_gettime 等严格 C11 声明）
- harmonyos 注入 -fno-emulated-tls（OHOS 工具链默认 emutls 污染导出符号）
- /proc/self/exe 进程名能力宏（OHOS 无 program_invocation_name/getprogname）
- u_memstream_close() 在 fclose 前 fflush（musl/OHOS open_memstream 语义）
- symbols-check.py 识别 HarmonyOS 平台并放行 OHOS 运行库符号
- 测试关闭时 `nm` 不再是 configure 期硬依赖（OHOS worker 无 nm）
- 强制 meson cross 文件（CI 同 profile 双端导致 host_machine 被误判为 x86_64）
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
import os
import shutil


class MesaConan(ConanFile):
    name = "mesa"
    version = "26.1.5"
    description = "mesa 26.1.5 — Mesa 3D 图形库（HarmonyOS PC, EGL/GLES/GBM + llvmpipe/softpipe）"
    license = "MIT"
    homepage = "https://www.mesa3d.org/"
    url = "https://gitlab.freedesktop.org/mesa/mesa"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        # 上游 meson 测试套件开关。默认关闭（交付包只含运行时制品）；
        # 打开后用 `meson test -C <build>` 跑上游全量用例做 rule4 证据。
        "build_tests": [True, False],
    }
    default_options = {"shared": True, "build_tests": False}

    # 鸿蒙专项测试源码（rule12 消费者端到端用例）随配方导出，
    # 在 source() 阶段复制进包内源码树，供 patches/0005 注册的 target 编译
    exports_sources = "src_additions/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # expat：mesa xmlconfig/drirc 解析必需
        self.requires("expat/2.8.2.1.1")
        # libdrm：GBM 后端硬依赖（-Dgbm=enabled 需要 libdrm 头文件/库）
        self.requires("libdrm/2.4.133")
        # llvm：llvmpipe 软件渲染器依赖
        self.requires("llvm/20.1.0")
        # zlib：mesa 通过 dependency('zlib') 探测压缩支持。若不显式提供 OHOS
        # zlib，meson 会回落到宿主 pkg-config，把 x86_64 的
        # /usr/lib/x86_64-linux-gnu/libz.so 链进 aarch64 目标
        # （ld.lld: libz.so is incompatible with aarch64linux）。
        self.requires("zlib/1.3.1.1")

    def build_requirements(self):
        # Mesa 的 Gallium/GL 解析器源码在 Meson configure 阶段生成
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4.2")
        # flex 二进制的绝对 M4 路径可能残留构建机路径，在本图内解析 m4
        self.tool_requires("m4/1.4.19")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 将导出的鸿蒙专项测试源码放入包内源码树。
        # export_sources 保留 `src_additions/` 作为根，因此源前缀是
        # src_additions/gallium/tests/ohos；patches/0005 在 src/meson.build
        # 里注册的 subdir('gallium/tests/ohos') 正是这里的目标位置。
        copy(self, "*",
             src=os.path.join(self.export_sources_folder,
                              "src_additions", "gallium", "tests", "ohos"),
             dst=os.path.join(self.source_folder, "src", "gallium", "tests", "ohos"),
             keep_path=False)

    def _patch_meson_native(self, tc):
        """Inject ar/ranlib + llvm tools into the generated Meson machine file.

        conan 的 MesonToolchain 不写 tools.build:compiler_executables 的
        ar/ranlib，meson 便按裸名 llvm-ar 探测归档器；CI profile 只给 c/cpp，
        PATH 上无 llvm-ar 时 configure 失败。同样地，llvmpipe 通过
        dependency('llvm', method:'config-tool') 探测 LLVM，需保证选中 conan
        依赖的 llvm/20.1.0 而非宿主系统 LLVM。

        generate() 里已强制交叉构建，因此正常情况下文件名是
        conan_meson_cross.ini；两种名字都尝试，保持对非交叉调用的兼容。
        """
        nf = None
        for candidate in ("conan_meson_cross.ini", "conan_meson_native.ini"):
            path = os.path.join(self.generators_folder, candidate)
            if os.path.isfile(path):
                nf = path
                break
        if nf is None:
            return
        with open(nf) as f:
            content = f.read()
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                cand = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(cand):
                    ar = cand
                    rlc = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(rlc):
                        rl = rlc
        adds = ""
        if ar and "ar =" not in content:
            adds += "ar = '%s'\n" % ar
        if rl and "ranlib =" not in content:
            adds += "ranlib = '%s'\n" % rl
        # meson 需要显式知道 pkg-config 二进制；缺失时 meson 直接报
        # "Pkg-config binary missing from cross or native file" 并把
        # expat/libdrm 判为 NOT FOUND，configure 在 meson.build:1848 处硬失败。
        # conan 的 MesonToolchain 只认 tools.gnu:pkg_config，不会写进 cross 文件。
        if "pkgconfig =" not in content:
            pkgcfg = self.conf.get("tools.gnu:pkg_config", default=None)
            if not pkgcfg:
                pkgcfg = shutil.which("pkg-config") or shutil.which("pkgconf")
            if pkgcfg and os.path.isfile(pkgcfg):
                adds += "pkgconfig = '%s'\n" % pkgcfg
        if "llvm" in self.dependencies:
            llvm_bin = os.path.join(self.dependencies["llvm"].package_folder, "bin")
            if os.path.isdir(llvm_bin):
                if "llvm-config =" not in content:
                    adds += "llvm-config = '%s'\n" % os.path.join(llvm_bin, "llvm-config")
                if "llvm-nm =" not in content:
                    adds += "llvm-nm = '%s'\n" % os.path.join(llvm_bin, "llvm-nm")
        if adds and "[binaries]" in content:
            content = content.replace("[binaries]\n", "[binaries]\n" + adds, 1)

        # conan 的 cross 文件只写 `needs_exe_wrapper = true`，不写 exe_wrapper。
        # meson 因此拒绝执行任何目标二进制，把全部可运行的上游测试判为
        # SKIP(exit 77)——rule4 需要的是真实执行结果，不是 0/N 的跳过。
        # 交叉构建时注入 qemu-user 包装器（OHOS musl 运行根），让上游测试
        # 真正跑起来；找不到包装器时保持原样（CI 由 L0/L1 自行处理执行）。
        if "needs_exe_wrapper" in content and "\nexe_wrapper = " not in content:
            for cand in ("/root/ohpc/bin/mesa-qemu-aarch64",
                         "/root/ohpc/bin/ohos-qemu-aarch64",
                         "/root/ohpc/sdk/qemu/usr/bin/qemu-aarch64-static"):
                if os.path.isfile(cand):
                    wrapper = ("exe_wrapper = ['%s']\n" % cand)
                    if "[binaries]" in content:
                        content = content.replace("[binaries]\n",
                                                  "[binaries]\n" + wrapper, 1)
                    else:
                        content += "\n[binaries]\n" + wrapper
                    break

        with open(nf, "w") as f:
            f.write(content)

    def generate(self):
        # 强制 conan 生成 meson **cross** 文件（conan_meson_cross.ini）。
        #
        # CI 用 `-pr:h=ohos-aarch64 -pr:b=ohos-aarch64`（同一 profile），此时
        # build_os==host_os==OHOS 且 build_arch==host_arch==armv8，
        # conan.tools.build.cross_building() 判为「非交叉」，MesonToolchain 便
        # 只写 native 文件（无 [host_machine]）。meson 于是把 host_machine
        # 当成构建机 x86_64，Mesa 的 src/util/blake3/meson.build 走
        # `cpu_family == 'x86_64'` 分支去汇编 blake3_avx512_x86-64_unix.S，
        # 在 aarch64 目标上必然失败（unrecognized instruction mnemonic）。
        #
        # 显式声明为交叉构建后，MesonToolchain 写 conan_meson_cross.ini，
        # 其 [host_machine] 的 cpu_family/system 取自 host profile（aarch64 /
        # harmonyos），meson 便选择正确的 aarch64 NEON 分支。
        self.conf.define("tools.build.cross_building:cross_build", True)

        # llvm-config 探测发生在 conanbuild 环境（不继承 build() 内的
        # os.environ 改动），通过 buildenv_info 把依赖 llvm 包的 bin 前置注入
        if "llvm" in self.dependencies:
            llvm_bin = os.path.join(self.dependencies["llvm"].package_folder, "bin")
            if os.path.isdir(llvm_bin):
                self.buildenv_info.prepend_path("PATH", llvm_bin)

        # expat/libdrm 的 .pc 进入 generators 目录，meson 的 pkg-config 探测才能找到
        PkgConfigDeps(self).generate()

        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"

        # 无窗口系统：OHOS SDK sysroot 无 X11/Wayland 头文件。
        # EGL 在未选择窗口系统平台时自动启用内建 surfaceless 平台。
        tc.project_options["platforms"] = ""
        tc.project_options["egl-native-platform"] = "surfaceless"

        # 软件渲染器：softpipe + llvmpipe（LLVM 20.1.0 registry 二进制已验证）
        tc.project_options["gallium-drivers"] = "softpipe,llvmpipe"
        tc.project_options["vulkan-drivers"] = ""

        # 交付制品集合：GBM + EGL + GLESv1/v2（桌面合成/浏览器/GTK 栈消费面）
        tc.project_options["gbm"] = "enabled"
        tc.project_options["egl"] = "enabled"
        tc.project_options["glx"] = "disabled"
        tc.project_options["opengl"] = True
        tc.project_options["gles1"] = "enabled"
        tc.project_options["gles2"] = "enabled"
        # glvnd 需要额外的 libglvnd 依赖，OHOS 侧不需要间接层
        tc.project_options["glvnd"] = "disabled"

        tc.project_options["llvm"] = "enabled"
        tc.project_options["libunwind"] = "disabled"
        tc.project_options["valgrind"] = "disabled"
        tc.project_options["zstd"] = "disabled"
        # 上游 26.1.5 已无 osmesa 选项（25.1.0 移除），此处不再传递
        has_tests = bool(self.options.build_tests)
        tc.project_options["build-tests"] = "true" if has_tests else "false"
        tc.project_options["tools"] = ""
        tc.generate()

        self._patch_meson_native(tc)

    def _prepare_parser_tools(self):
        """把解析器生成器绑定到本隔离 Conan 图中的包。"""
        bison = self.dependencies.build["bison"]
        bison_datadir = os.path.join(bison.package_folder, "share", "bison")
        if os.path.isdir(bison_datadir):
            os.environ["BISON_PKGDATADIR"] = bison_datadir
            os.environ["M4PATH"] = os.path.join(bison_datadir, "m4sugar")

        m4 = self.dependencies.build["m4"]
        m4_bin = os.path.join(m4.package_folder, "bin", "m4")
        if os.path.isfile(m4_bin):
            os.environ["M4"] = m4_bin
            os.environ["PATH"] = os.path.dirname(m4_bin) + os.pathsep + os.environ.get("PATH", "")
        else:
            raise ConanException(f"m4 executable is missing from the resolved package: {m4_bin}")

    def build(self):
        # 在 meson configure 之前套用 conandata.yml 声明的 OHOS 适配补丁
        apply_conandata_patches(self)

        # Mesa 的 Meson 构建需要 Python mako>=0.8.0 生成部分源码
        self.run("python3 -c 'import mako'", env="conanbuild", ignore_errors=True)
        try:
            import mako  # noqa: F401
            _mako_ver = getattr(mako, "__version__", "")
        except Exception:
            _mako_ver = ""
        if not _mako_ver:
            self.output.info("installing python mako (mesa meson build dependency)")
            rc = self.run("python3 -m pip install 'mako>=0.8.0' --quiet", env="conanbuild")
            if rc != 0:
                raise ConanException(
                    "mesa 构建需要 Python mako>=0.8.0，但直 pip 安装失败；"
                    "请确保构建环境可访问安装源或在 CI 环境预装 mako")

        self._prepare_parser_tools()
        meson = Meson(self)
        meson.configure()
        # 显式构建交付目标（OHOS 适配版 conan 2.29.1 的 Meson.build() 只接受
        # 单个 target 字符串；空格分隔是 meson compile 原生的多目标语法）。
        # 目标名必须是 meson 认识的名字（`meson compile <t>` 实测）：
        # Gallium 共享库用 `gallium`（`gallium-26.1.5` 是产物文件名而非目标名，
        # `libgallium` 亦不被 meson 识别）。
        targets = "gallium gbm dri_gbm EGL GLESv1_CM GLESv2 llvmpipe softpipe"
        if bool(self.options.build_tests):
            # 测试模式下编译上游全部测试目标（meson test 需要它们存在）
            targets = ""
        if targets:
            meson.build(target=targets)
        else:
            meson.build()

    def package(self):
        import glob
        meson = Meson(self)
        # 不让安装阶段重建所有未选中的默认目标
        meson.install(cli_args=["--no-rebuild"])

        # OHOS 不创建 Meson 生成的 SONAME 符号链接。把链接名发布为普通文件，
        # 使 Conan 消费者无需依赖符号链接能力即可解析
        # -lEGL / -lGLESv2 / -lGLESv1_CM / -lgbm。
        libdir = os.path.join(self.package_folder, "lib")
        aliases = [
            ("libEGL.so", "libEGL.so"),
            ("libEGL.so.1", "libEGL.so"),
            ("libGLESv2.so", "libGLESv2.so"),
            ("libGLESv2.so.2", "libGLESv2.so"),
            ("libGLESv1_CM.so", "libGLESv1_CM.so"),
            ("libGLESv1_CM.so.1", "libGLESv1_CM.so"),
            ("libgbm.so", "libgbm.so"),
            ("libgbm.so.1", "libgbm.so"),
            ("libgallium.so", "libgallium.so"),
        ]
        for linker_name, base in aliases:
            target = os.path.join(libdir, linker_name)
            if os.path.isfile(target) or os.path.exists(target):
                continue
            for cand in sorted(glob.glob(os.path.join(libdir, base + ".*"))):
                if os.path.isfile(cand) and not cand.endswith(".a"):
                    shutil.copy2(cand, target)
                    break

        self._sign_shared_libs()

    def _sign_shared_libs(self):
        """为 OHOS loader 重新签名已安装的 ELF 共享对象。"""
        if str(self.settings.os) != "OHOS":
            return
        import glob

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        libdir = os.path.join(self.package_folder, "lib")
        shared_objects = []
        for pattern in ("*.so", "*.so.*"):
            shared_objects.extend(glob.glob(os.path.join(libdir, pattern)))
        for shared_object in sorted(set(shared_objects)):
            if os.path.islink(shared_object):
                continue
            # Meson/lld 产物可能残留过期签名，先移除再追加当前自签名
            self.run(
                f'{objcopy} --remove-section .codesign "{shared_object}"',
                ignore_errors=True,
            )
            self.run(
                f'{signer} sign -inFile "{shared_object}" '
                f'-outFile "{shared_object}" -selfSign 1'
            )

    def _ohos_libcxx_dir(self):
        """定位 OHOS SDK 的 libc++_shared.so 目录。

        libgallium 由 C++ 源码编译，DT_NEEDED 含 libc++_shared.so；该库由
        OHOS SDK 提供（不在 conan 图内），loader 仍需要一个可查找目录。
        """
        ce = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict) or {}
        cc = ce.get("c") or ce.get("cpp") or ""
        if cc and os.path.sep in cc:
            # <sdk>/native/llvm/bin/<triple>-clang -> <sdk>/native/llvm/lib/<triple>
            llvm_root = os.path.dirname(os.path.dirname(cc))
            triple = os.path.basename(cc)
            for suffix in ("-clang++", "-clang"):
                if triple.endswith(suffix):
                    triple = triple[: -len(suffix)]
                    break
            cand = os.path.join(llvm_root, "lib", triple)
            if os.path.isfile(os.path.join(cand, "libc++_shared.so")):
                return cand
            # 回退：lib/<triple> 之外的任一含 libc++_shared.so 的子目录
            libroot = os.path.join(llvm_root, "lib")
            if os.path.isdir(libroot):
                for entry in sorted(os.listdir(libroot)):
                    sub = os.path.join(libroot, entry)
                    if os.path.isfile(os.path.join(sub, "libc++_shared.so")):
                        return sub
        return ""

    def package_info(self):
        self.cpp_info.libs = ["EGL", "GLESv2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.runenv_info.append_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )

        # 交付制品是**动态**库，其 DT_NEEDED 含本包之外的运行库：
        #   libgallium-26.1.5.so -> libLLVM.so.20.1, libc++_shared.so, libexpat.so
        #   libEGL.so.1           -> libgallium-26.1.5.so, libgbm.so.1, libexpat.so
        # conan 只为**直接**依赖生成 runenv 条目；而这些库的实际查找发生在
        # OHOS/musl loader 里 —— 目录缺失时进程在 main() 之前就被判死
        # （`Error loading shared library libLLVM.so.20.1`、
        #  `Error relocating ... symbol not found`），对外表现为 exit 127，
        # 而不是一条可读的断言失败。这里把传递闭包里的运行库目录一并注入，
        # 消费者（test_package / 上层应用）无需自行拼 LD_LIBRARY_PATH。
        for dep_name in ("llvm", "expat"):
            if dep_name not in self.dependencies:
                continue
            dep = self.dependencies[dep_name]
            for candidate in (os.path.join(dep.package_folder, "lib"),
                              os.path.join(dep.package_folder, "bin")):
                if os.path.isdir(candidate):
                    self.runenv_info.append_path("LD_LIBRARY_PATH", candidate)
        libcxx_dir = self._ohos_libcxx_dir()
        if libcxx_dir:
            self.runenv_info.append_path("LD_LIBRARY_PATH", libcxx_dir)

        self.cpp_info.set_property("cmake_file_name", "mesa")
        self.cpp_info.set_property("cmake_target_name", "mesa::mesa")
