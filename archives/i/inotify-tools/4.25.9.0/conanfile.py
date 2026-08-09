#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout

class InotifyToolsConan(ConanFile):
    name = "inotify-tools"
    version = "4.25.9.0"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/inotify-tools/inotify-tools"
    url = "https://github.com/inotify-tools/inotify-tools"
    description = "inotify-tools is a C library and a set of command-line programs for Linux."
    topics = ("linux", "filesystem", "monitoring")

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # CI 真根因: autoreconf -fi 缺 aclocal → 整个 autoconf/automake 链死路
    # 改用手写极简 Makefile 直接编译源文件，绕开 autotools 工具链
    # stub Makefile 在 build() 里自带 CC/CXX/AR/CXXFLAGS，无需 AutotoolsToolchain 生成器

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # R39: 仅用官方源（github.com/inotify-tools）。CI 有内置 mirror fallback
        # （gh-proxy 等）处理 GitHub 不可达场景；配方内不再自定义 mirror_url
        # （aireview Critical: mirror 下载 sha256=None 跳过校验属供应链投毒风险，
        # 同 groonga 处理）。
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # stub Makefile 自带工具链（CC/CXX/AR/CXXFLAGS），无需 AutotoolsToolchain 生成器
        # 仅生成 conanbuild.sh 供 build() 合入 Conan conf 工具链环境变量
        from conan.tools.env import VirtualBuildEnv
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # CI 真根因: autoreconf -fi 缺 aclocal failed exit status 2
        # CI worker 缺 autotools 工具链（aclocal），autoreconf/autoconf 链完全不可用，
        # 上游无 CMakeLists.txt，autogen.sh 也只是 autoreconf --install，Debian tarball
        # 也无 pre-generated configure/Makefile.in → 整个 autoconf/automake 链死路。
        # 修法: 手写极简 configure stub + Makefile 直接编译源文件，绕开 autoconf/automake。
        # 源文件清单（15 个）：
        #   libinotifytools/src: inotifytools.cpp redblack.cpp stats.cpp（+ 头）
        #   src: inotifywait.cpp inotifywatch.cpp common.cpp（CLI 二进制）
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        ar = compilers.get("archive") or "llvm-ar"
        # CI 真根因: 上游 #include "inotifytools/inotify.h" 但 build 树无 inotify.h（上游 configure
        # 据 sys/inotify.h 检测结果建：有则 #include <sys/inotify.h>，无则 bundled inotify-nosys.h）
        # OHOS sysroot 真有 sys/inotify.h → 建 inotify.h 钾像头 #include <sys/inotify.h> 避 bundled 路径
        inotify_h_dir = os.path.join(self.source_folder, "libinotifytools", "src", "inotifytools")
        with open(os.path.join(inotify_h_dir, "inotify.h"), "w") as f:
            f.write('#ifndef _INOTIFYTOOLS_INOTIFY_H_SHIM\n')
            f.write('#define _INOTIFYTOOLS_INOTIFY_H_SHIM\n')
            f.write('#include <sys/inotify.h>\n')  # OHOS sysroot 真有此头
            f.write('#endif\n')
        # CI 真根因: 上游 #include "inotifytools/fanotify.h" 但 build 树无 fanotify.h（上游 configure
        # 据 sys/fanotify.h 检测：有则 #include <sys/fanotify.h>，无则 bundled fanotify-dfid-name.h）
        # OHOS sysroot 无 sys/fanotify.h → 建 fanotify.h 钾像头 #include "fanotify-dfid-name.h" 走 bundled
        # 且 #undef LINUX_FANOTIFY（上游 inotifytools.cpp 硬编码 define 该宏，会编译 fanotify_init/
        # fanotify_mark 调用，但 OHOS 无这两个函数实现 → CI undefined identifier）
        with open(os.path.join(inotify_h_dir, "fanotify.h"), "w") as f:
            f.write('#ifndef _INOTIFYTOOLS_FANOTIFY_H_SHIM\n')
            f.write('#define _INOTIFYTOOLS_FANOTIFY_H_SHIM\n')
            f.write('#undef LINUX_FANOTIFY\n')  # OHOS 无 fanotify_init/fanotify_mark，禁用 fanotify 编译路径
            f.write('#include "fanotify-dfid-name.h"\n')  # bundled fallback（OHOS 无 sys/fanotify.h）
            f.write('#endif\n')
        # CI 真根因: 上游 #include "../../config.h" / "../config.h" 但 CI 缺 aclocal → autoconf 链死路
        # → 手写 config.h（OHOS aarch64 真测：sys/inotify.h 存在，sys/fanotify.h 不存在）
        config_h = os.path.join(self.source_folder, "config.h")
        with open(config_h, "w") as f:
            f.write('/* Hand-generated config.h for OHOS cross-build (aclocal unavailable) */\n')
            f.write('#define PACKAGE_NAME "inotify-tools"\n')
            f.write('#define PACKAGE_TARNAME "inotify-tools"\n')
            f.write('#define PACKAGE_VERSION "4.25.9.0"\n')
            f.write('#define PACKAGE_STRING "inotify-tools 4.25.9.0"\n')
            f.write('#define PACKAGE_BUGREPORT "https://github.com/inotify-tools/inotify-tools/issues"\n')
            f.write('#define PACKAGE_URL "https://github.com/inotify-tools/inotify-tools"\n')
            f.write('#define INOTIFYTOOLS_VERSION "4.25.9.0"\n')
            f.write('#define HAVE_STDLIB_H 1\n')
            f.write('#define HAVE_STDIO_H 1\n')
            f.write('#define HAVE_STRING_H 1\n')
            f.write('#define HAVE_STRINGS_H 1\n')
            f.write('#define HAVE_UNISTD_H 1\n')
            f.write('#define HAVE_INTTYPES_H 1\n')
            f.write('#define HAVE_STDINT_H 1\n')
            f.write('#define HAVE_SYS_STAT_H 1\n')
            f.write('#define HAVE_SYS_TYPES_H 1\n')
            f.write('#define HAVE_MCHECK_H 1\n')
            f.write('#define HAVE_DAEMON 1\n')
            f.write('#define HAVE_SYS_INOTIFY_H 1\n')
            f.write('#define SYS_INOTIFY_H_EXISTS_AND_WORKS 1\n')
            # OHOS aarch64 真测：sys/fanotify.h 不存在 → 不定义 HAVE_SYS_FANOTIFY_H
            f.write('#define STDC_HEADERS 1\n')
        # Conan 2.x conanbuild.sh 合入的工具链环境变量（CFLAGS/CXXFLAGS/LDFLAGS 等）
        env_script = os.path.join(self.generators_folder, "conanbuild.sh")
        prefix = os.path.join(self.build_folder, "staging")
        inc_dir = os.path.join(self.source_folder, "libinotifytools", "src")
        # 通用编译参数：补 -Ilibinotifytools/src/inotifytools 让 inotifytools/inotify.h 可见
        # -Wno-unused-parameter: 上游回调函数签名含未用参数（stats.cpp/inotifytools.cpp 多处），
        # -Werror 会将其变错误导致 CI 编译失败（#14403）
        # -Wno-sign-compare: inotifytools.cpp:1525 无符号/有符号比较
        # （unsigned long vs ssize_t），-Werror,-Wsign-compare 升级为错误（CI #15261/#15262）
        common_cxx = (
            f'-std=c++17 -fno-exceptions -Wall -Wextra -Wshadow -Werror '
            f'-Wno-unused-parameter -Wno-sign-compare '
            f'-Wno-unused-command-line-argument -Wno-missing-field-initializers '
            f'-I{inc_dir} -I{inc_dir}/inotifytools '
            f'-DINOTIFYTOOLS_VERSION=\\"4.25.9.0\\"'
        )
        # aireview P3: 删未用变量 lib_src/cli_src（声明后无后续引用）
        # 写极简 Makefile 直接编译（避 autoconf/automake 链）
        makefile_path = os.path.join(self.build_folder, "Makefile")
        with open(makefile_path, "w") as f:
            f.write(f"# Minimal Makefile for inotify-tools OHOS cross-build (aclocal unavailable)\n")
            f.write(f"CC = {cc}\nCXX = {cxx}\nAR = {ar}\n")
            f.write(f"PREFIX = {prefix}\n")
            # aireview P2: CXXFLAGS 用 += 追加 common_cxx（非 ?=），确保 -std=c++17/-I/-D 等关键参数
            # 始终存在，无论 conanbuild.sh 环境变量是否已设 CXXFLAGS（?=? 会被已设环境变量跳过丢参数）
            f.write(f"CXXFLAGS += {common_cxx}\n")
            f.write(f"CXXFLAGS += $(EXTRA_CXXFLAGS)\n")
            f.write(f"LDFLAGS += $(EXTRA_LDFLAGS)\n\n")
            # libinotifytools 静态库
            f.write("LIB_OBJS = libinotifytools/src/inotifytools.o libinotifytools/src/redblack.o libinotifytools/src/stats.o\n")
            f.write("libinotifytools/libinotifytools.a: $(LIB_OBJS)\n")
            f.write("\t$(AR) rcs $@ $^\n\n")
            f.write("libinotifytools/src/%.o: libinotifytools/src/%.cpp\n")
            f.write("\t$(CXX) $(CXXFLAGS) -c $< -o $@\n\n")
            # CLI 二进制
            f.write("src/inotifywait: src/inotifywait.cpp src/common.o libinotifytools/libinotifytools.a\n")
            f.write("\t$(CXX) $(CXXFLAGS) src/inotifywait.cpp src/common.o -Ilibinotifytools/src -Llibinotifytools -linotifytools $(LDFLAGS) -o $@\n\n")
            f.write("src/inotifywatch: src/inotifywatch.cpp src/common.o libinotifytools/libinotifytools.a\n")
            f.write("\t$(CXX) $(CXXFLAGS) src/inotifywatch.cpp src/common.o -Ilibinotifytools/src -Llibinotifytools -linotifytools $(LDFLAGS) -o $@\n\n")
            f.write("src/common.o: src/common.cpp\n")
            f.write("\t$(CXX) $(CXXFLAGS) -c $< -o $@\n\n")
            # install target（package() 复用）
            f.write("install: all\n")
            f.write("\tinstall -d $(PREFIX)/bin $(PREFIX)/lib $(PREFIX)/include/inotifytools\n")
            f.write("\tinstall -m 755 src/inotifywait src/inotifywatch $(PREFIX)/bin/\n")
            f.write("\tinstall -m 644 libinotifytools/libinotifytools.a $(PREFIX)/lib/\n")
            f.write("\tinstall -m 644 libinotifytools/src/inotifytools/inotifytools.h libinotifytools/src/inotifytools/inotify-nosys.h libinotifytools/src/inotifytools/inotify.h $(PREFIX)/include/inotifytools/\n\n")
            f.write("all: libinotifytools/libinotifytools.a src/inotifywait src/inotifywatch\n")
        # 跑 make（用 conanbuild.sh 工具链环境变量）
        # aireview P1 阻塞: Makefile 写入 build_folder 但 make 从 source_folder 跑找不到
        # → make 命令加 -f 指向 build_folder 的 Makefile，cwd 保持 source_folder
        # （Makefile 内路径相对 source_folder，如 libinotifytools/src/%.cpp）
        if os.path.exists(env_script):
            make_cmd = f'. {env_script} && make -f "{makefile_path}" -j$(nproc) all'
        else:
            make_cmd = f'make -f "{makefile_path}" -j$(nproc) all'
        self.run(make_cmd, cwd=self.source_folder, shell=True)

    def package(self):
        copy(self, "COPYING", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        # stub Makefile 的 install target（PREFIX=staging 装到 build_folder/staging）
        env_script = os.path.join(self.generators_folder, "conanbuild.sh")
        prefix = os.path.join(self.build_folder, "staging")
        # aireview P1 阻塞: 同 build() — make install 需 -f 指向 build_folder 的 Makefile
        makefile_path = os.path.join(self.build_folder, "Makefile")
        if os.path.exists(env_script):
            make_cmd = f'. {env_script} && make -f "{makefile_path}" install PREFIX={prefix}'
        else:
            make_cmd = f'make -f "{makefile_path}" install PREFIX={prefix}'
        self.run(make_cmd, cwd=self.source_folder, shell=True)
        # copy staging 到 package_folder
        copy(self, "*", src=prefix, dst=self.package_folder)

    def package_info(self):
        self.cpp_info.libs = ["inotifytools"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
