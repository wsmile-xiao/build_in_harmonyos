#!/usr/bin/env python3
"""Conan recipe for caph 1.1 — physics-based puzzle game (SDL 1.2 + libpng).

HarmonyOS (aarch64) adaptation:
- Disable OpenGL rendering (no GPU context in OHOS sandbox); use SDL software surface
- Build as application package (produces `caph` executable)
- Provide share/caph data files (maps, images, config)
- Fix bash-isms (mkgen/confg shebang /bin/bash doesn't exist on OHOS)

R26: libSDL-1.2 and libpng are not system library names on OHOS — no collision.
R32: settings.os must check in ("Linux", "OHOS").
R38: application package — provides caph executable.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, replace_in_file, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class CaphConan(ConanFile):
    name = "caph"
    version = "1.1"
    description = "Caph 1.1 — physics-based puzzle game (SDL 1.2, libpng)"
    license = "GPL-3.0-or-later"
    homepage = "http://caphgame.sourceforge.net/"
    url = "https://sourceforge.net/projects/caphgame/"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("sdl/1.2.15")
        self.requires("libpng/1.6.58.3")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # R26/R28: declare patch-export hook even when no patches are needed
        # OHOS adaptations use replace_in_file in source() instead of patch files
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

        # HMDFS: conan build 子进程降权无法读取缓存依赖头文件 + 沙箱不跟随符号链接
        # 在 source() 阶段（owner 权限）将头文件复制到源码目录并摊平符号链接
        import shutil as _shutil
        local_inc = os.path.join(self.source_folder, "ohos_inc")
        if os.path.isdir(local_inc):
            _shutil.rmtree(local_inc)
        os.makedirs(local_inc)
        for dep_name, dep_key in [("sdl", "sdl"), ("libpng", "libpng")]:
            try:
                dep = self.dependencies[dep_key]
                dest = os.path.join(local_inc, dep_name)
                os.makedirs(dest, exist_ok=True)
                for inc_dir in dep.cpp_info.includedirs:
                    if os.path.isdir(inc_dir):
                        for root, dirs, files in os.walk(inc_dir):
                            rel = os.path.relpath(root, inc_dir)
                            target_dir = os.path.join(dest, rel) if rel != "." else dest
                            os.makedirs(target_dir, exist_ok=True)
                            for fname in files:
                                src_f = os.path.join(root, fname)
                                dst_f = os.path.join(target_dir, fname)
                                if os.path.islink(src_f):
                                    # 摊平符号链接：复制目标文件内容而非创建链接
                                    real_path = os.path.realpath(src_f)
                                    if os.path.isfile(real_path):
                                        _shutil.copy2(real_path, dst_f)
                                    else:
                                        # 如果 realpath 不存在，保留符号链接
                                        linkto = os.readlink(src_f)
                                        if os.path.lexists(dst_f):
                                            os.remove(dst_f)
                                        os.symlink(linkto, dst_f)
                                else:
                                    _shutil.copy2(src_f, dst_f)
            except Exception:
                pass

        # Fix confg to remove OpenGL dependency (OHOS sandbox has no GPU context)
        confg_path = os.path.join(self.source_folder, "src", "confg")
        if os.path.isfile(confg_path):
            replace_in_file(self, confg_path,
                "CFLAGS+=' -D_OPENGL'",
                "# CFLAGS+=' -D_OPENGL'  # OHOS: no OpenGL in sandbox")
            replace_in_file(self, confg_path,
                "if which pkg-config > /dev/null && pkg-config --exists gl; then\n"
                "\tCFLAGS+=$(pkg-config --cflags gl | sed 's/^/\ /')\n"
                "\tLFLAGS+=$(pkg-config --libs gl | sed 's/^/\ /')\n"
                "else\n"
                "\tLFLAGS+=$(echo '-lGL' | sed 's/^/\ /')\n"
                "fi",
                "# OHOS: no OpenGL library\n"
                "\ttrue")

        # Fix SYS_DATA_DIR: binary at bin/caph, data at res/caph/
        caph_c = os.path.join(self.source_folder, "src", "caph.c")
        if os.path.isfile(caph_c):
            replace_in_file(self, caph_c,
                '#define SYS_DATA_DIR\t"../share/caph/"',
                '#define SYS_DATA_DIR\t"../res/caph/"')

        # Fix mkgen/confg shebang: /bin/bash doesn't exist on OHOS
        for script in ("src/mkgen", "src/confg", "src/build"):
            script_path = os.path.join(self.source_folder, script)
            if os.path.isfile(script_path):
                replace_in_file(self, script_path,
                    "#!/bin/bash",
                    "#!/system/bin/sh")

    def build(self):
        src_dir = os.path.join(self.source_folder, "src")

        # Use deps_cpp_info to get flags instead of pkg-config
        sdl_dep = self.dependencies["sdl"]
        png_dep = self.dependencies["libpng"]

        # HMDFS 多用户工作区: 复制依赖头文件到源码目录并摊平符号链接
        # basic_layout 中 source_folder 在 source() 和 build() 不同
        local_inc = os.path.join(self.source_folder, "ohos_inc")
        if os.path.isdir(local_inc):
            shutil.rmtree(local_inc)
        os.makedirs(local_inc)
        for dep_name, dep in [("sdl", sdl_dep), ("libpng", png_dep)]:
            dest = os.path.join(local_inc, dep_name)
            os.makedirs(dest, exist_ok=True)
            for inc_dir in dep.cpp_info.includedirs:
                if os.path.isdir(inc_dir):
                    for root, dirs, files in os.walk(inc_dir):
                        rel = os.path.relpath(root, inc_dir)
                        target_dir = os.path.join(dest, rel) if rel != "." else dest
                        os.makedirs(target_dir, exist_ok=True)
                        for fname in files:
                            src_f = os.path.join(root, fname)
                            dst_f = os.path.join(target_dir, fname)
                            if os.path.islink(src_f):
                                # 摊平符号链接：复制目标文件内容
                                real_path = os.path.realpath(src_f)
                                if os.path.isfile(real_path):
                                    shutil.copy2(real_path, dst_f)
                                else:
                                    linkto = os.readlink(src_f)
                                    if os.path.lexists(dst_f):
                                        os.remove(dst_f)
                                    os.symlink(linkto, dst_f)
                            else:
                                shutil.copy2(src_f, dst_f)

        sdl_cflags = f"-I{os.path.join(local_inc, 'sdl')}"
        sdl_libflags = " ".join([f"-L{p}" for p in sdl_dep.cpp_info.libdirs])
        sdl_libs = " ".join([f"-l{l}" for l in sdl_dep.cpp_info.libs])
        png_cflags = f"-I{os.path.join(local_inc, 'libpng')}"
        png_libflags = " ".join([f"-L{p}" for p in png_dep.cpp_info.libdirs])
        png_libs = " ".join([f"-l{l}" for l in png_dep.cpp_info.libs])

        # R33: get compiler from Conan conf, not shell env
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={}, check_type=dict)
        cc = compilers.get("c", "/data/service/hnp/bin/clang") if compilers else "/data/service/hnp/bin/clang"

        # CFLAGS: C99, POSIX, include dir, no OpenGL
        cflags = f"-Wall -O3 -ffast-math -pipe -g3 -I../include -std=c99 -D_XOPEN_SOURCE=600 {sdl_cflags} {png_cflags}"
        # LIBS: SDL, png, m (no -lGL), with -L for lib dirs
        lflags = f"{sdl_libflags} {png_libflags} {sdl_libs} {png_libs} -lm"

        # Set env vars for mkgen + make
        os.environ["CC"] = cc
        os.environ["CFLAGS"] = cflags
        os.environ["LFLAGS"] = lflags

        # HMDFS: mkgen 内部调用 cc 探测依赖时使用管道（conan 子进程管道静默错误）
        # 直接在 Python 中生成 caph.mk，避免使用 mkgen
        caph_mk = os.path.join(src_dir, "caph.mk")
        mk_content = f"""# generated by conan recipe (caph/1.1 OHOS adaptation)
#

CC\t= {cc}
RM\t= rm -f

CFLAGS\t= {cflags}
LFLAGS\t= {lflags}

OBJS\t= caph.o\t\t\\
\tdraw.o\t\t\\
\tmaps.o\t\t\\
\tphys.o

BIN\t= caph

all: $(BIN)

$(BIN): $(OBJS)
\t@ echo "  LD\t" $(BIN)
\t@ $(CC) -o $@ $^ $(LFLAGS)

caph.o: caph.c
\t@ echo "  CC\t" $@
\t@ $(CC) -c $(CFLAGS) -o $@ $<

draw.o: draw.c
\t@ echo "  CC\t" $@
\t@ $(CC) -c $(CFLAGS) -o $@ $<

maps.o: maps.c
\t@ echo "  CC\t" $@
\t@ $(CC) -c $(CFLAGS) -o $@ $<

phys.o: phys.c
\t@ echo "  CC\t" $@
\t@ $(CC) -c $(CFLAGS) -o $@ $<

clean:
\t@ echo "  CLEAN\t"
\t@ $(RM) $(BIN) $(OBJS)
"""
        with open(caph_mk, "w") as f:
            f.write(mk_content)

        # HMDFS 已知问题: conan stdout 接管道时子进程静默 Error
        # 直接 subprocess.run 写日志文件绕过
        build_log = os.path.join(src_dir, "build.log")
        with open(build_log, "w") as lf:
            result = subprocess.run(
                ["make", "-f", "caph.mk", "-j1"],
                cwd=src_dir, stdout=lf, stderr=subprocess.STDOUT, check=False)
        if result.returncode != 0:
            raise Exception(f"make failed (rc={result.returncode}), see {build_log}")

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        copy(self, "caph",
             src=src_dir,
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        share_src = os.path.join(self.source_folder, "share", "caph")
        share_dst = os.path.join(self.package_folder, "res", "caph")
        copy(self, "*", src=share_src, dst=share_dst)
        copy(self, "COPYING",
             src=os.path.join(self.source_folder, "doc", "caph"),
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
