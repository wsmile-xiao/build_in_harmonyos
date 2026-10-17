"""conanfile.py — DRAFT (kbtin 2.3, OHOS aarch64)。逐字依据见同目录 RECIPE-DRAFT-notes.md；未经真机。"""
import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


required_conan_version = ">=1.59.0"

# E543：HMDFS 新建文件默认 660 ⇒ configure 期 execute_process(./get_version) 必须先有可执行位
_SCRIPTS_AT_CONFIGURE = ("get_version",)
_SCRIPTS_AT_BUILD = ("make_commands", "make_protos", "a2html", "help2ansi", "fixmanual")


class KbtinConan(ConanFile):
    name = "kbtin"
    version = "2.3"
    description = "K Irc Client - advanced scriptable IRC client with repl"
    license = "GPL-2.0-or-later"
    url = "https://git.sr.ht/~kilobyte/kbtin"
    homepage = "https://git.sr.ht/~kilobyte/kbtin"
    topics = ("irc", "client", "terminal", "scripting")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"mccp": [True, False], "ssl": [True, False]}
    default_options = {"mccp": True, "ssl": True}

    def requirements(self):
        # CMakeLists L68 message(FATAL_ERROR "libiconv is required") ⇒ 硬门
        self.requires("libiconv/1.17.1")
        if self.options.mccp:      # option(MCCP "MCCP compression via zlib" ON)
            self.requires("zlib/1.3.1")
        if self.options.ssl:       # option(SSL "SSL encryption via gnutls" ON) ⇒ 不是 openssl
            # 必须 self.requires + CMakeDeps 生成的 target：上游 L84 只 find_package(GnuTLS QUIET)，
            # 而仓内 gnutls 制品的 CMake config 未必落在 conan 的搜索路径里 —— 真机实测不显式
            # 链接就会把 TLS 静默编没（`Error loading shared library libgnutls.so.30` 之后
            # KBtin 仍以 rc=0 退出，属假通过）。改由 target 强制链接，探测不过即构建失败。
            self.requires("gnutls/3.8.10")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["tarball"], strip_root=True)

    def _dep_libdirs(self):
        """所有依赖的绝对 libdir（真机教训：88/90 假失败的首错是
        `Error loading shared library libgnutls.so.30` + `Error relocating ./KBtin:
        gnutls_record_send: symbol not found` —— ctest 由 cmake.test() 直接起，
        不经 conanrun.sh，所以 LD_LIBRARY_PATH 是空的；musl 的动态加载器又忽略 DT_RUNPATH
        （经验汇总 §12.38），只有把绝对路径写进 DT_RPATH 才解析得到。）"""
        out = []
        for ref, dep in self.dependencies.host.items():
            pf = dep.package_folder
            for d in dep.cpp_info.aggregated_components().libdirs or []:
                out.append(d if os.path.isabs(d) else os.path.join(pf, d))
        return out

    def generate(self):
        VirtualBuildEnv(self).generate()   # 设备侧 cmake 由 hnp 提供；仓内 CMake 配方一律不 tool_requires cmake
        tc = CMakeToolchain(self)
        # 构建树与安装树都要绝对 RPATH：前者给上游 ctest 用，后者给装好的 KBtin 用
        tc.cache_variables["CMAKE_SKIP_BUILD_RPATH"] = False
        # §12.38②（GLM-31 coin3d 实证）：cmake --install 会**字节级改写**安装副本的 RPATH，
        # OHOS musl 对改写后的产物直接拒载 ⇒ 安装期必须关掉改写，让 package 里的 KBtin 与构建树原件字节一致。
        # 上一版这里写的 CMAKE_INSTALL_RPATH_USE_LINK_PATH=True 正是触发改写的那条，已按 KB 更正。
        tc.cache_variables["CMAKE_SKIP_INSTALL_RPATH"] = True
        tc.cache_variables["MCCP"] = bool(self.options.mccp)
        tc.cache_variables["SSL"] = bool(self.options.ssl)
        # 上游把 DATA_PATH 在 configure 期烤成绝对路径（CMakeLists L30），必须是最终安装路径
        tc.cache_variables["CMAKE_INSTALL_DATADIR"] = "res"
        tc.cache_variables["CMAKE_INSTALL_MANDIR"] = "res/man"
        # 真机反证：只写 CMAKE_BUILD_RPATH 缓存变量**不生效**——readelf -d ../KBtin 里
        # 只有 NEEDED(libz/libgnutls/libc)，既无 RPATH 也无 RUNPATH ⇒ 88/90 仍空输出。
        # 改成把 -Wl,-rpath 直接交给链接器（extra_exelinkflags 会进 CONAN_EXE_LINKER_FLAGS_*）。
        rps = [f"-Wl,-rpath,{d}" for d in self._dep_libdirs()]
        for d in self._dep_libdirs():
            self.output.info(f"RPATH(exe linker) += {d}")
        tc.extra_exelinkflags.extend(rps)
        tc.extra_sharedlinkflags.extend(rps)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def _make_scripts_executable(self):
        root = self.source_folder
        for name in _SCRIPTS_AT_CONFIGURE + _SCRIPTS_AT_BUILD:
            p = os.path.join(root, name)
            if os.path.isfile(p):
                st = os.stat(p)
                os.chmod(p, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                self.output.info(f"E543 chmod +x: {name}")
            elif name in _SCRIPTS_AT_CONFIGURE:
                raise ConanInvalidConfiguration(f"configure 期需要的脚本缺失：{name}")

    def build(self):
        apply_conandata_patches(self)
        self._make_scripts_executable()
        cmake = CMake(self)
        cmake.configure()
        # 上游把 HAVE_GNUTLS 写死在 config.h.cmake 的模板里，需确认不是 #cmakedefine 空值
        hdr = os.path.join(self.build_folder, self.folders.build, "config.h") if self.folders.build else ""
        self.output.info(f"configure 后 config.h 路径候选: {hdr or '(build 根)'}")
        cmake.build()
        # §10 硬门：上游注册套件必须真跑（90 条：89 条 foreach 语料 + kbtree_itr）
        # runtest.sh 的 ../KBtin 与 ./get-utf8 是相对路径 ⇒ ctest 工作目录必须是 build/tests（cmake.test 默认如此）
        cmake.test()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        CMake(self).install()
        # 兜底：万一上游仍有被改写的产物，直接用构建树原件覆盖（§12.38② 给的第二条路）
        built = os.path.join(self.build_folder, "KBtin")
        inst = os.path.join(self.package_folder, "bin", "KBtin")
        if os.path.isfile(built) and os.path.isfile(inst):
            shutil.copy2(built, inst)
            self.output.info("package(): 用构建树原件覆盖安装副本（保持 RPATH 字节一致）")
        binpath = os.path.join(self.package_folder, "bin", "KBtin")
        if os.path.isfile(binpath):
            os.chmod(binpath, 0o755)
        self._self_sign()

    def _self_sign(self):
        """OHOS 内核只放行带有效 .codesign 段的 ELF（abx/0.1、plocate、memlockd 先例）；
        找不到签名工具就显式失败，不静默交付不可执行产物。"""
        signer = shutil.which("binary-sign-tool") or os.environ.get("OHOS_BINARY_SIGN_TOOL", "")
        if not signer or not os.path.isfile(signer):
            raise ConanInvalidConfiguration("binary-sign-tool not found on PATH "
                                            "(set OHOS_BINARY_SIGN_TOOL)")
        path = os.path.join(self.package_folder, "bin", "KBtin")
        out = path + ".signed"
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", out,
                        "-selfSign", "1"], check=True, timeout=120)
        os.chmod(out, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(out, path)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]   # KBtin_help.gz 落在 res/kbtin/ 下（上游 DATA_PATH）
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.builddirs = []
        self.cpp_info.frameworkdirs = []
        self.cpp_info.appdirs = []
        # 注：不写 self.user_info —— conan2 中它不跨包可读，消费方按 resdirs 自行定位
