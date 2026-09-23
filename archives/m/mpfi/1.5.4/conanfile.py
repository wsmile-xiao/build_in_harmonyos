#!/usr/bin/env python3
"""Conan recipe — mpfi 1.5.4 (autotools)

mpfi 1.5.4：MPFR 之上的任意精度浮点区间运算库。
相对 1.5.2 的适配要点完全一致（同为 autotools + libtool + gmp/mpfr 依赖），
配方沿用 1.5.2 实战验证过的全部鸿蒙补丁性配置：
  · VirtualRunEnv(scope="build")：--build==--host 时 configure 要跑 conftest
  · LDFLAGS 前置依赖 libdir：不受环境 LDFLAGS 污染
  · umask 077 → 022：鸿蒙 Toybox bash 默认 umask 会让 make install 产物失去组/其他读位
  · 删 .la：libtool .la 烤死绝对路径，下游 libtool 解析失败
"""
import glob as _glob
import os as _os

from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import VirtualRunEnv


class MpfiConan(ConanFile):
    name = "mpfi"
    version = "1.5.4"
    description = "MPFI — Multiple Precision Floating-point Interval arithmetic library on top of MPFR"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.inria.fr/mpfi/mpfi/"
    url = "https://perso.ens-lyon.fr/nathalie.revol/mpfi.html"
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
        self.requires("mpfr/4.2.2.1")
        # mpfr/4.2.2.1 自身钉 gmp/6.3.0，与本包要的 6.3.0.1 冲突；
        # 只有 force 能压过传递依赖钉的版本（与 1.5.2 相同，notes 有实录）。
        self.requires("gmp/6.3.0.1", force=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        # AutotoolsDeps 把依赖的 -l 全塞进链接行，于是 configure 的 conftest
        # **链上了这些依赖**；而 --build == --host 时 autoconf 判本机构建，
        # 要**运行** conftest。加载器找不到依赖 .so 就是 $? = 127，
        # configure 却报成「cannot run C compiled programs」——指向完全错误的方向。
        # 故必须把依赖 libdir 写进 build 期 LD_LIBRARY_PATH。
        VirtualRunEnv(self).generate(scope="build")
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        # 环境里可能已有 LDFLAGS（设备与 CI worker 的 ~/.zshrc 都导出了
        # -L$HOME/usr/local/lib）。conan 对 LDFLAGS 用的是 **append**，自己的 -L 排在
        # 它**后面**；链接器按 -L 顺序取第一个命中的目录，于是 `-lfoo` 可能命中系统的
        # libfoo.so 而不是 conan 包里的 —— 把依赖的 libdir **前置**，
        # 让 recipe 不再受环境 LDFLAGS 影响，本机与 CI 行为一致。
        _env = tc.environment()
        # profile 的 buildenv 把 CONFIG_SHELL 写死为 /data/service/hnp/bin/bash，
        # 但本机布局（bash 在 ~/usr/local/bin）该路径不存在 → configure 的
        # libtool 探测 exec 得 127 报 "inaccessible or not found"（知识 E551 场景）。
        # tc.environment() 的 recipe 侧定义优先于 profile buildenv，
        # 这里按 PATH 实际可寻的 bash 覆盖；找不到则回退 /bin/sh（configure 只需 POSIX）。
        import shutil as _sh
        _bash = _sh.which("bash") or "/bin/sh"
        _env.define("CONFIG_SHELL", _bash)
        _env.define("SHELL", _bash)
        # gmp 包（--enable-cxx 版）的 cpp_info.libs 把 gmpxx 也列入；
        # mpfi 是纯 C 库，拖 gmpxx 会把 libc++_shared 带进 NEEDED（实测）。
        # conan 的 LDFLAGS 由 AutotoolsDeps 生成后 append，这里在 LIBS 上
        # 显式只给 C 侧依赖，防止 -lgmpxx 混入。
        _env.define("LIBS", "-lmpfr -lgmp")
        _Lp = " ".join("-L{}".format(_d) for _ref, _dep in self.dependencies.items()
                       for _d in _dep.cpp_info.libdirs)
        if _Lp:
            _env.prepend("LDFLAGS", _Lp)
        tc.generate(_env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # 发布 tarball 带现成的 configure，直接用；
        # 若是 GitHub archive 类快照（无 configure）则先 autoreconf 自举。
        # 判在运行期而非生成期：同一份配方两种源都能用。
        if not _os.path.isfile(_os.path.join(self.source_folder, "", "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            autotools.autoreconf(build_script_folder=_os.path.join(
                self.source_folder, ""))
        # ⚠️ umask / uname 这类对 configure 脚本本身的修补**必须在 autoreconf 之后**：
        # 自举会重新生成 configure，放在前面等于白改。
        for _cfg in _glob.glob(_os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        # CONFIG_SHELL 用命令行前缀赋值直跑 configure（E551）：
        # profile buildenv 把 SHELL/CONFIG_SHELL 写死为 /data/service/hnp/bin/bash，
        # 部署布局（bash 在 ~/usr/local/bin）下该路径不存在；而 conan 的 env 聚合
        # 是「先 profile 后 recipe」,tc.environment() 的 define 遮不住它——configure
        # re-exec `exec $CONFIG_SHELL` 直接 127。命令行前缀赋值优先于一切导出变量，
        # 用 /bin/sh（configure 只需 POSIX sh）彻底绕开。
        _cfgargs = " ".join(["--build=aarch64-unknown-linux-musl",
                             "--host=aarch64-unknown-linux-musl"])
        _prefix_args = " ".join([
            "--prefix=" + self.package_folder,
            "--bindir=${prefix}/bin", "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib", "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
            "--enable-shared", "--disable-static",
        ])
        self.run(f'CONFIG_SHELL=/bin/sh "{self.source_folder}/configure" '
                 f'{_cfgargs} {_prefix_args}', cwd=self.build_folder)
        # 并行编译：src + tests 共 300+ 个目标，-j1 真机要 15 分钟以上。
        # libtool .la 竞态先例只发生在 install 阶段；编译/链接无共享写目标。
        _nj = _os.cpu_count() or 2
        autotools.make(args=["-j{}".format(_nj)])
        # 上游正式测试：tests/ 下 159 个 check_PROGRAMS（tabs…tget_version）。
        # tarball 自带 tests/*.dat 参考数据，make check 全部真跑（不因交叉构建跳过：
        # --build==--host 时 autoconf 判本机构建，conftest/测试可执行）。
        # musl 无任何特殊跳过项。check-TESTS 每测试独立 .log/.trs，可安全并行。
        autotools.make(target="check", args=["-j{}".format(_nj)])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        # 【skill: 默认删 .la】libtool 的 .la 里烤死 libdir 绝对路径，
        # conan 包按 prefix=/ 构建 → 里面写的是 '/lib'，下游 libtool 会去找
        # `//lib/libmpfi.la` 而失败。链接信息 .pc/cpp_info 已提供。
        for _la in _glob.glob(_os.path.join(self.package_folder, "lib", "*.la")):
            _os.remove(_la)

    def package_info(self):
        # 上游 include_HEADERS = src/mpfi.h src/mpfi_io.h → 装到 $(includedir)/
        # 顶层（无子目录），include 一层即可。
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["mpfi"]
        # 依赖传播：mpfi 的 mpfi.pc 声明 -lmpfi -lmpfr -lgmp，
        # cpp_info.requires 与之等价（conan 侧的传递依赖表达）。
        self.cpp_info.requires = ["mpfr::mpfr", "gmp::gmp"]
        self.cpp_info.set_property("cmake_file_name", "mpfi")
        self.cpp_info.set_property("cmake_target_name", "mpfi::mpfi")
        self.cpp_info.set_property("pkg_config_name", "mpfi")
