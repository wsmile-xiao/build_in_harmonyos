#!/usr/bin/env python3
"""Conan recipe — nauty 2.9.3 (autotools)"""
from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout



class NautyConan(ConanFile):
    name = "nauty"
    version = "2.9.3"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")
        # nauty 的 Makefile **不支持异地（VPATH）构建**：conan 默认在 build-release/ 里
        # 跑 configure，make 立刻报 `No rule to make target 'dreadnaut.c'`（它只会在
        # 当前目录找 .c）。把构建目录设成源码目录，改成 in-source 构建。
        self.folders.build = self.folders.source

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--includedir=/include/nauty")
        # 环境里可能已有 LDFLAGS（设备与 CI worker 的 ~/.zshrc 都导出了
        # -L$HOME/usr/local/lib）。conan 对 LDFLAGS 用的是 **append**，自己的 -L 排在
        # 它**后面**；链接器按 -L 顺序取第一个命中的目录，于是 `-lfoo` 可能命中系统的
        # libfoo.so 而不是 conan 包里的 libfoo.a，configure 的 conftest 运行期就加载不到：
        #   Error loading shared library libffi.so.8: (needed by ./conftest)
        #   configure: error: cannot run C compiled programs.
        # （ecl 24.5.10 实撞；本机 unset LDFLAGS 能过、CI 不 unset 就挂，
        #   等于用调用方环境掩盖了 recipe 缺陷。）
        # 把依赖的 libdir **前置**，让 recipe 不再受环境 LDFLAGS 影响，本机与 CI 行为一致。
        # ⚠️ 必须只取**绝对路径**：被 skip 的传递依赖（无 package_folder）其
        # cpp_info.libdirs 会退化成相对的 "lib"，原样拼进去就是 `-Llib`，
        # libtool 链接时直接报：
        #   ./libtool: cd: lib: No such file or directory
        #   libtool: error: cannot determine absolute directory name of 'lib'
        # （m4rie 20250128 实撞。）
        import os as _os
        _env = tc.environment()
        _Lp = " ".join("-L{}".format(_d) for _ref, _dep in self.dependencies.items()
                       for _d in (_dep.cpp_info.libdirs or []) if _os.path.isabs(_d))
        if _Lp:
            _env.prepend("LDFLAGS", _Lp)
        tc.generate(_env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # 发布 tarball（ftp.gnu.org 那类）里带现成的 configure，直接用；
        # 但 **GitHub 的 archive tarball 从不含 configure**（它只是 git tree 的快照，
        # configure 是 autoreconf 的产物、不进版本库），此时必须先自举。
        # 判在运行期而非生成期：同一份配方两种源都能用。
        import os as _os
        if not _os.path.isfile(_os.path.join(self.source_folder, "", "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            # **必须在源码所在子目录里跑**：判定用的是 SRC_SUBDIR，执行也要一致。
            # 实测 libmspack/1.11：源码是 `libmspack/configure.ac`，在顶层 autoreconf
            # 直接报 `autoreconf: error: 'configure.ac' is required`。
            autotools.autoreconf(build_script_folder=_os.path.join(
                self.source_folder, ""))
        # ⚠️ umask / uname 这类对 configure 脚本本身的修补**必须在 autoreconf 之后**：
        # 自举会重新生成 configure，放在前面等于白改（改的是不存在的文件，
        # 或改完又被覆盖）。
        import glob as _glob, os as _os
        for _cfg in _glob.glob(_os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        # 【skill: 默认删 .la】libtool 的 .la 里烤死 libdir 绝对路径，
        # conan 包按 prefix=/ 构建 → 里面写的是 '/lib'，下游 libtool 会去找
        # `//lib/libxxx.la` 而失败（graphviz 实撞）。链接信息 .pc/cpp_info 已提供。
        import glob as _glob, os as _os
        for _la in _glob.glob(_os.path.join(self.package_folder, "lib", "*.la")):
            _os.remove(_la)




    def package_info(self):
        self.cpp_info.includedirs = ['include', 'include/nauty']
        self.cpp_info.libs = ['nauty']
        self.cpp_info.set_property("cmake_file_name", "nauty")
        self.cpp_info.set_property("cmake_target_name", "nauty::nauty")
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)



    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob as _glob
        import os as _os
        pcs = sorted(_glob.glob(_os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return _os.path.splitext(_os.path.basename(pcs[0]))[0]
