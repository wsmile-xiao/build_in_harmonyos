#!/usr/bin/env python3
"""Conan recipe — hwloc 2.14.0 (autotools)"""
from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps



class HwlocConan(ConanFile):
    name = "hwloc"
    version = "2.14.0"
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
        self.requires("libxml2/2.15.3")
        self.requires("cairo/1.18.4")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--enable-libxml2")
        tc.configure_args.append("--enable-cairo")
        tc.configure_args.append("--disable-cuda")
        tc.configure_args.append("--disable-nvml")
        tc.configure_args.append("--disable-gl")
        tc.configure_args.append("--disable-opencl")
        tc.configure_args.append("--without-x")
        tc.configure_args.append("--disable-doxygen")
        # 【skill: --probe-define 生成】构建期行为探针。
        # 有些能力**编译期看不出来**：鸿蒙 seccomp 对部分 syscall 是 KILL 语义
        # （SIGSYS 直接杀进程，不是返回 ENOSYS），进程内也无从恢复。
        # 只能真跑一次看它死不死。探针失败 → 定义能力宏 → 上游走它已有的降级分支。
        import os as _os, subprocess as _sp, tempfile as _tf
        _cc = (self.conf.get('tools.build:compiler_executables', default={},
                             check_type=dict) or {}).get('c', 'clang')
        for _pd in ('HWLOC_MEMPOLICY_SYSCALL_UNUSABLE=syscall(__NR_get_mempolicy, 0, 0, 0, 0, 0);',):
            _macro, _stmt = _pd.split('=', 1)
            _d = _tf.mkdtemp()
            _src = _os.path.join(_d, 'probe.c')
            _prog = ('#include <unistd.h>\n#include <sys/syscall.h>\n'
                     '#include <errno.h>\nint main(void){ ' + _stmt + ' return 0; }\n')
            with open(_src, 'w') as _f:
                _f.write(_prog)
            _exe = _os.path.join(_d, 'probe')
            if _sp.run([_cc, _src, '-o', _exe], capture_output=True).returncode != 0:
                self.output.warning('探针 %s 编译失败，按不可用处理' % _macro)
                tc.extra_defines.append(_macro)
                continue
            _rc = _sp.run([_exe], capture_output=True).returncode
            if _rc != 0:
                # 被信号打死时 returncode 为负（SIGSYS 表现为 -31）
                self.output.info('探针 %s 未通过(rc=%s) → 定义该宏，走上游降级分支'
                                 % (_macro, _rc))
                tc.extra_defines.append(_macro)
            else:
                self.output.info('探针 %s 通过 → 不定义，保留上游原生实现' % _macro)
        tc.generate()

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
        import glob, os
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
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
        self.cpp_info.includedirs = self._detect_include_dirs()
        self.cpp_info.libs = ['hwloc']
        self.cpp_info.set_property("cmake_file_name", "hwloc")
        self.cpp_info.set_property("cmake_target_name", "hwloc::hwloc")
        self.cpp_info.set_property("pkg_config_name", "hwloc")



    def _detect_include_dirs(self):
        """扫 include/ 下含头文件的一层子目录，连同 include 本身一起返回。

        很多库把公开头装在版本化子目录（pango-1.0 / glib-2.0 / freetype2 / cspice…），
        只声明 include 的话，消费方按上游惯用法 #include <pango/pango.h> 就找不到 ——
        而这个缺陷在**本包构建装包时完全不暴露**，要到下游编译才炸。
        """
        import os
        base = os.path.join(self.package_folder, "include")
        dirs = ["include"]
        if not os.path.isdir(base):
            return dirs
        for name in sorted(os.listdir(base)):
            sub = os.path.join(base, name)
            if not os.path.isdir(sub):
                continue
            for _root, _d, files in os.walk(sub):
                if any(f.endswith((".h", ".hpp", ".hh", ".hxx")) for f in files):
                    dirs.append("include/" + name)
                    break
        return dirs

