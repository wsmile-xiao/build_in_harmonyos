#!/usr/bin/env python3
"""Conan recipe for libgig 4.5.2 — C++ library for Gigasampler/GigaStudio (.gig),
DLS, SoundFont2, KORG and Akai file access (Autotools: configure + make).

交付面（实测 `make install` 产物，非推测）：
- 库：`lib/libgig/libgig.a` + `lib/libgig/libakai.a`（上游 `pkglib_LTLIBRARIES`，
  落在 `$(libdir)/$(PACKAGE)` 子目录而非 `lib/` 顶层）；`lib/pkgconfig/{gig,akai}.pc`。
- 头：`include/libgig/{RIFF,DLS,SF,gig,Korg,Serialization,sysdef,Akai}.h`。
- 工具：`bin/` 下 14 个 CLI（rifftree dlsdump gigdump gigextract gigmerge
  gig2mono gig2stereo sf2dump sf2extract korgdump korg2gig akaidump akaiextract wav2gig）
  → 软件级 `commands.json`（R38/L0k）。

静态链接（`--disable-shared --enable-static`）：libsndfile/1.2.2 与 libuuid/2.42.2
两个依赖在本制品仓均为静态包，libgig 随之静态化后 `bin/` 下 14 个工具自包含——
既不产生 libfstfar 那类 `bin/`→`../lib` 的 RUNPATH 隐患，也不依赖运行时库搜索路径。

平台适配：
- **E007（`config.guess` 不认 HarmonyOS）**：`conan create` 的 AutotoolsToolchain 在 host==build
  时不传 `--host/--build`，`configure` 因此走 `config.guess` 探测路径，在本机报
  `cannot guess build type`（该探测路径还会用 `umask 077 && mktemp -d` 建 0700 目录，
  在 HMDFS 上不可写）。补丁 `0001` 加 `*:HarmonyOS:*:*` 分支输出
  `aarch64-unknown-linux-ohos` 并 `exit`，短路探测（`config.sub` 已原生支持 `linux-ohos`）。
- **静态链接下的静态初始化顺序缺陷（补丁 0002/0003）**：库内 `static` 数据成员
  `DataType::m_nativeTypes`（`Serialization.cpp`）属动态初始化，而消费者 TU 的全局
  `NativeDataTypeRegistry<T>` 构造器会在自己的动态初始化阶段访问它；静态链接顺序是
  「消费者对象 → 静态库成员」⇒ 访问尚未构造的 map，测试可执行文件在 `main()` 之前
  SIGSEGV（shared 构建下 `.so` 的初始化先于可执行文件，缺陷被掩盖）。补丁把它改为
  **函数内 static 访问器**（首次使用即构造，与链接顺序无关）。
- **E503（CLI 缺 GNU 长选项 → L2 smoke 恒失败）**：上游 14 个工具只实现短选项
  `-v`（`--version`/`--help`/`-V`/`-h` 全部落进 "Unknown option" 或 fopen 失败分支并
  `EXIT_FAILURE`），而 G4/L2 门禁以 `--version`/`--help` 探测可执行性 → 全部工具被测失败。
  按知识图谱 E503（libubox jshn 先例，PR !5897）加补丁（0004–0017）：`main()` 开头拦截
  `--version`（与既有 `-v` 同语义）与 `--help`（与既有 usage 同语义）并 **return 0**。
- **E011（HMDFS 上 configure 的 umask 077 临时目录不可写）**：`configure` 内联
  `sed` 把 `umask 077` 改 `umask 022`（libuuid 2.42.2 / libbfio 家族同口径，不改
  生成文件以外的语义）。
- **包内 `.pc` 前缀**：Conan 以 `--prefix=/` 配置，上游 `@prefix@` 展开成 `/`，
  `package()` 内把 `prefix`/`exec_prefix`/`libdir`/`includedir` 重写为实际包目录。
- **上游测试**：`src/testcases/` 4 个测试程序（gigtests/helpertests/rifftests/
  serializationtests）由 `make check` 构建并逐个执行；本配方在 `build()` 内于
  沙箱 HOME 下实跑（不写入用户真实 HOME）。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# 上游 `src/testcases/Makefile.am` 的 `check:` 目标逐个执行的测试程序（4 个）
UPSTREAM_TESTS = ("helpertests", "serializationtests", "rifftests", "gigtests")


class LibgigConan(ConanFile):
    name = "libgig"
    version = "4.5.2"
    description = ("C++ library for loading and modifying Gigasampler/GigaStudio, "
                   "DLS, SoundFont2, KORG and Akai sampler files")
    license = "LGPL-2.1-or-later"
    homepage = "https://www.linuxsampler.org/libgig/"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        """本包只交付静态库：`shared=True` 必须**显式拒绝**而不是被 generate() 静默忽略。

        原因见 notes.md 问题 1/2：上游 `pkglib_LTLIBRARIES`（装在 `$(libdir)/libgig/`）
        在 `--prefix=/` 下会被 libtool 写成绝对 RUNPATH `//lib/libgig`，14 个工具在裸环境
        全部不可用；同时 shared 构建会掩盖上游的静态初始化顺序缺陷。要支持 shared
        需先解决这两条，不能靠把 `--disable-shared` 写死来"假装支持"。
        口径同 archives/l/libuuid/2.42.2 的 validate()。
        """
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "libgig is packaged as a static library; building it shared needs the "
                "libtool absolute-RUNPATH (//lib/libgig) and the static-init-order issues "
                "resolved first — see archives/l/libgig/4.5.2/notes.md"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac: PKG_CHECK_MODULES(SNDFILE, sndfile >= 1.0.2) 是**硬依赖**
        # （缺则 `exit -1`），供 gigextract/sf2extract/akaiextract/wav2gig 写音频文件。
        self.requires("libsndfile/1.2.2")
        # configure.ac: AC_CHECK_HEADERS(uuid/uuid.h) + AC_SEARCH_LIBS(uuid_generate, uuid)
        # + AC_CHECK_FUNCS(uuid_generate)，非 mac/win32 平台缺则 `exit -1`（DLSID 生成用）。
        self.requires("libuuid/2.42.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dependency_flags(self):
        """libuuid 的头/库目录（configure 只对 sndfile 走 pkg-config）。"""
        dep = self.dependencies["libuuid"]
        cpp_info = dep.cpp_info.aggregated_components()
        root = dep.package_folder

        def absolute(dirs):
            return [d if os.path.isabs(d) else os.path.join(root, d) for d in dirs]

        return absolute(cpp_info.includedirs), absolute(cpp_info.libdirs)

    def generate(self):
        # sndfile.pc 由 PkgConfigDeps 写进 generators 目录；
        # AutotoolsToolchain.environment() 已把该目录前置进 PKG_CONFIG_PATH。
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        includes, libdirs = self._dependency_flags()
        for inc in includes:
            tc.extra_cxxflags.append(f"-I{inc}")
        for lib in libdirs:
            tc.extra_ldflags.append(f"-L{lib}")
        tc.generate()

    def _patch_umask(self):
        """E011：configure 的 `umask 077` 在 HMDFS 上建出的 0700 临时目录连创建者
        都无法写入（config.status 随即 Permission denied）；改 022（libuuid 家族口径）。"""
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        if "umask 077" in content:
            with open(configure, "w", encoding="utf-8") as handle:
                handle.write(content.replace("umask 077", "umask 022"))
            self.output.info("E011: configure umask 077 -> 022")

    def _run_upstream_tests(self):
        """上游 `make check`：4 个测试程序逐个执行，任一非零即失败。

        沙箱 HOME：上游测试会在 CWD（src/testcases）写 a.riff/b.riff/foo.gig 等中间
        文件，不碰 HOME；此处仍显式指向任务私有沙箱，避免任何写用户真实 HOME 的路径
        （notes/device-facts.md §一.11）。
        """
        test_home = os.path.join(self.build_folder, "test-home")
        os.makedirs(test_home, exist_ok=True)
        for test in UPSTREAM_TESTS:
            # `make check` 的 check 目标本身就跑这 4 个程序；此处逐个重跑以取得
            # 每个程序的独立退出码与断言计数（"OK (N checks)"）。
            # HOME 用命令内联前缀注入（ConanFile.run 没有 extra_env 参数）。
            self.run(f"HOME={test_home} ./{test}",
                     cwd=os.path.join(self.build_folder, "src", "testcases"),
                     env="conanbuild")

    def build(self):
        apply_conandata_patches(self)
        self._patch_umask()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=[f"-j{build_jobs(self)}"])

        # 上游自带的 `check:` 目标：构建并逐个执行 4 个测试程序
        self.run("make check", cwd=self.build_folder, env="conanbuild")
        self._run_upstream_tests()

    def _fix_pkgconfig_prefix(self):
        """重写包内 .pc 的路径为实际包目录。

        上游 `gig.pc.in`/`akai.pc.in` 用 `@prefix@`，而 Conan 以 `--prefix=/` 配置、
        `make install DESTDIR=<package_folder>` 安装，于是包内 .pc 写成
        `prefix=/`、`libdir=${prefix}/lib/libgig`、`includedir=${prefix}/include/libgig`——
        非 Conan 的消费者（把 `PKG_CONFIG_PATH` 指向本包）按该 .pc 取到的是 `/lib`、`/include`
        这类系统路径而不是包路径（libart-lgpl 家族同型缺陷）。
        """
        for name in ("gig", "akai"):
            pc_file = os.path.join(self.package_folder, "lib", "pkgconfig", f"{name}.pc")
            if not os.path.isfile(pc_file):
                continue
            with open(pc_file, "r", encoding="utf-8") as handle:
                content = handle.read()
            rewrites = {
                "prefix": self.package_folder,
                "exec_prefix": self.package_folder,
                "libdir": os.path.join(self.package_folder, "lib", self.name),
                "includedir": os.path.join(self.package_folder, "include", self.name),
            }
            for key, value in rewrites.items():
                content = re.sub(rf"^{key}=.*$", f"{key}={value}", content, flags=re.M)
            with open(pc_file, "w", encoding="utf-8") as handle:
                handle.write(content)
            self.output.info(f"pkg-config prefix fixed: lib/pkgconfig/{name}.pc")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._fix_pkgconfig_prefix()

    def package_info(self):
        # 上游 pkglib_LTLIBRARIES：libgig.la/libakai.la 装在 $(libdir)/libgig/
        self.cpp_info.libs = ["gig", "akai"]
        self.cpp_info.libdirs = ["lib", os.path.join("lib", self.name)]
        # 上游 libgigincludedir = $(includedir)/libgig：头文件装在 include/libgig/，
        # 且 gig.pc 的 Cflags 是 -I${includedir}/libgig（消费者按 #include <gig.h> 使用）。
        # 两个目录都给出：include/libgig 供 <gig.h>，include 供 <libgig/gig.h>。
        self.cpp_info.includedirs = ["include", os.path.join("include", self.name)]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "gig")
        self.cpp_info.set_property("cmake_file_name", "libgig")
        self.cpp_info.set_property("cmake_target_name", "libgig::libgig")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
