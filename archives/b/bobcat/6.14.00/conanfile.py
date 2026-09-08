#!/usr/bin/env python3
"""bobcat 6.14.00 — OHOS Conan 配方

上游构建系统为 icmake（作者自有构建工具，`./build light`），设备与 CI 均无此工具。
本配方以 Python 精确复刻上游 light 构建的编译/链接语义（依据
bobcat-6.14.00 的 icmake/libraries、icmake/library、icmake/special 逐行核对）：

- 类集合 = CLASSES 全部条目（跳过注释行）＝ 上游 light 模式（128 类，零第三方依赖）
- 编译行： $CXX $CXXFLAGS -isystem <src>/tmp -c -o <idx><name>.o --std=<cppstd> <src.cc>
           静态遍对象在类目录 tmp/oa；共享遍加 -fPIC 且对象在 tmp/os（复刻上游）
- 静态库： ar cr + ranlib（复刻 icmake/libraries static_library）
- 共享库： $CXX -pthread -shared -Wl,--as-needed,-z,defs,-soname,libbobcat.so.6
           -o libbobcat.so.6.14.00 */os/*.o（light 无附加 -l 库）
- 公共头： tmp/bobcat/<class> = 类无扩展名公共头，#include "x.f" 行内联展开
           （复刻 icmake/libraries catFile 递归语义）；安装到 include/bobcat/
- PCH（.ih.gch/spch.gch）为编译加速缓存，不参与链接与安装，跳过不影响语义

与上游构建的说明性差异：上游一次产出 .a + .so（发行版打包需要）；
Conan 由 shared option 驱动只编所需遍（时间减半，产物语义不变）。

参考：https://gitlab.com/fbb-git/bobcat （tag 6.14.00）
"""
import os
import subprocess
from multiprocessing.pool import ThreadPool
import glob as globmod

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, collect_libs
from conan.tools.build import build_jobs

required_conan_version = ">=2.0"


def _cat_file(dst_lines, src_path):
    """复刻 icmake/libraries catFile：逐行复制；#include "x.f" 行内联展开。

    判定语义与上游 icmake 一致：行首为 #include "（== 0）且该行含 .f"
    （!= -1，允许行尾注释）。"""
    with open(src_path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith('#include "') and '.f"' in line:
                inc = line.split('"')[1]
                _cat_file(dst_lines, os.path.join(os.path.dirname(src_path), inc))
            else:
                dst_lines.append(line)


class BobcatConan(ConanFile):
    name = "bobcat"
    version = "6.14.00"
    description = (
        "Brokken's Own Base Classes And Templates: C++ classes for child "
        "processes, streams/sockets, shared memory, config files and more"
    )
    license = "GPL-3.0-or-later"
    url = "https://gitlab.com/fbb-git/bobcat"
    homepage = "https://fbb-git.gitlab.io/bobcat/"
    topics = ("cpp", "process", "streams", "ipc", "utilities")
    settings = "os", "arch", "compiler", "build_type"
    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    no_copy_source = True

    def export_sources(self):
        # conandata.yml（source() 输入）与 patches/ 随配方导出
        copy(self, "conandata.yml", self.recipe_folder, self.export_sources_folder)
        copy(self, "patches/*", self.recipe_folder, self.export_sources_folder)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ------------------------------------------------------------------
    def _toolchain_executables(self):
        # R33: 编译器/ar 等来自 Conan conf（profile 注入），不经 shell 环境变量。
        # 注意：Conan 2.29 不支持 "tools.build:compiler_executables:cpp" 点分子键
        # 直接 get（抛 ConanException），须先取 dict 再索引（workflow §5.3 已知坑）。
        return self.conf.get(
            "tools.build:compiler_executables", {}, check_type=dict
        ) or {}

    def _cxx(self):
        return self._toolchain_executables().get("cpp", "clang++")

    def _cppstd_flag(self):
        # 上游 bobcat 6.x 需要 C++20（公共头使用 std::unsigned_integral 等概念，
        # 下游消费者同样必须 >= C++20）。profile 声明更低标准时按上游最低要求提升。
        requested = (str(self.settings.compiler.cppstd) or "").replace("gnu", "")
        try:
            level = int(requested)
        except ValueError:
            level = 20
        return "--std=c++" + str(max(level, 20))

    def _cxxflags(self):
        flags = {
            "Debug": "-O0 -g",
            "Release": "-O2",
            "RelWithDebInfo": "-O2 -g",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "-O2")
        return flags + " -Wall"

    def _classes(self, src):
        """上游 light 模式的类清单：CLASSES 全部非注释条目。"""
        classes = []
        with open(os.path.join(src, "CLASSES"), encoding="utf-8") as fh:
            for line in fh:
                name = line.strip()
                if name and not name.startswith("//"):
                    classes.append(name)
        return classes

    # ------------------------------------------------------------------
    def _subproc_env(self):
        """子进程环境：继承当前环境，并确保 OHOS SDK 的 llvm/lib 在
        动态库搜索路径中——SDK 自带的 lld 链接器依赖 libxml2.so.16，
        部分 worker 环境的 loader 搜索路径未覆盖该目录，缺失会导致
        链接子进程无法启动（unable to execute command）。

        注意：profile 的编译器路径可能是符号链接（如 /data/service/hnp/bin/clang++
        → SDK llvm/bin/clang++），必须 realpath 后再推导 lib 目录，
        否则得到不存在的路径使本修复失效。"""
        env = dict(os.environ)
        llvm_lib = os.path.normpath(
            os.path.join(os.path.dirname(os.path.realpath(self._cxx())), "..", "lib")
        )
        if os.path.isabs(llvm_lib) and os.path.isdir(llvm_lib):
            existing = env.get("LD_LIBRARY_PATH", "")
            parts = [p for p in existing.split(os.pathsep) if p]
            if llvm_lib not in parts:
                parts.insert(0, llvm_lib)
            env["LD_LIBRARY_PATH"] = os.pathsep.join(parts)
        return env

    def build(self):
        # R33：编译器与 flags 全部由 Conan conf/settings 内插到显式命令行
        #（每条命令原文记录于构建日志 bobcat_compile_log.txt，可追溯），
        # 不经 shell 环境变量。
        apply_conandata_patches(self)
        src = self.source_folder
        cxx = self._cxx()
        stdflag = self._cppstd_flag()
        base_flags = f"{self._cxxflags()} {stdflag} -isystem {os.path.join(src, 'tmp')}"

        classes = self._classes(src)
        self.output.info(f"light 类数: {len(classes)}")

        # 1. 公共头 tmp/bobcat/<class>（catFile 复刻，含 .f 内联）
        hdr_root = os.path.join(src, "tmp", "bobcat")
        os.makedirs(hdr_root, exist_ok=True)
        for cls in classes:
            lines = []
            _cat_file(lines, os.path.join(src, cls, cls))
            with open(os.path.join(hdr_root, cls), "w", encoding="utf-8") as fh:
                fh.writelines(lines)
        self.output.info(f"公共头生成: {len(classes)}")

        # 2. 编译任务：对象名复刻上游 <类序号><basename>.o
        #    shared:  tmp/os（-fPIC）→ libbobcat.so.6.14.00
        #    static:  tmp/oa（非 PIC）→ libbobcat.a
        compile_cmds = []
        want_shared = bool(self.options.shared)
        want_static = not want_shared

        def add_tasks(dst_dir, extra_flags):
            for idx, cls in enumerate(classes):
                cls_dir = os.path.join(src, cls)
                if not os.path.isdir(cls_dir):
                    continue
                cc_files = sorted(
                    f for f in os.listdir(cls_dir)
                    if f.endswith(".cc") and os.path.isfile(os.path.join(cls_dir, f))
                )
                if not cc_files:
                    continue
                out_dir = os.path.join(cls_dir, dst_dir)
                os.makedirs(out_dir, exist_ok=True)
                for cc in cc_files:
                    obj = os.path.join(out_dir, f"{idx}{cc[:-3]}.o")
                    compile_cmds.append(
                        f"{cxx} {base_flags} {extra_flags} -c "
                        f"-o '{obj}' '{os.path.join(cls_dir, cc)}'"
                    )

        add_tasks("os", "-fPIC" if want_shared else "")
        if want_static:
            add_tasks("oa", "")
        self.output.info(f"编译任务: {len(compile_cmds)}")

        log_path = os.path.join(self.build_folder, "bobcat_compile_log.txt")
        failures = []
        with open(log_path, "w", encoding="utf-8") as log:
            subproc_env = self._subproc_env()

            def run_one(cmd):
                proc = subprocess.run(
                    cmd, shell=True, cwd=src, env=subproc_env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                )
                log.write(f"$ {cmd}\n{proc.stdout}\n")
                log.flush()
                return proc.returncode

            with ThreadPool(processes=max(1, int(build_jobs(self)))) as pool:
                for cmd, rc in zip(compile_cmds, pool.imap(run_one, compile_cmds)):
                    if rc != 0:
                        failures.append(cmd)
        if failures:
            self.output.error(
                f"编译失败 {len(failures)}/{len(compile_cmds)}，日志: {log_path}"
            )
            raise ConanException(
                f"bobcat compile failed ({failures[0]}); log: {log_path}"
            )
        self.output.info(f"编译完成 {len(compile_cmds)} 个任务")

        executables = self._toolchain_executables()
        ar = executables.get("ar", "llvm-ar")
        ranlib = executables.get("ranlib", "llvm-ranlib")

        # 3. 静态库（复刻 static_library：ar cr + ranlib）
        if want_static:
            oa_objs = sorted(globmod.glob(os.path.join(src, "*", "oa", "*.o")))
            static_lib = os.path.join(src, "tmp", "liba", "libbobcat.a")
            os.makedirs(os.path.dirname(static_lib), exist_ok=True)
            if os.path.exists(static_lib):
                os.remove(static_lib)
            subprocess.run([ar, "cr", static_lib] + oa_objs, cwd=src, check=True)
            subprocess.run([ranlib, static_lib], check=True)
            self.output.info(f"静态库: {static_lib} ({len(oa_objs)} 对象)")

        # 4. 共享库（复刻 _shared_library 链接行；light 无附加 -l 库）
        if want_shared:
            os_objs = sorted(globmod.glob(os.path.join(src, "*", "os", "*.o")))
            libso_dir = os.path.join(src, "tmp", "libso")
            os.makedirs(libso_dir, exist_ok=True)
            major = self.version.split(".")[0]
            soname = f"libbobcat.so.{major}"
            out_so = os.path.join(libso_dir, f"libbobcat.so.{self.version}")
            link_cmd = (
                f"{cxx} -pthread -shared -Wl,--as-needed,-z,defs,"
                f"-soname,{soname} -o '{out_so}' "
                + " ".join(f"'{o}'" for o in os_objs)
            )
            proc = subprocess.run(
                link_cmd, shell=True, cwd=src, env=self._subproc_env(),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            if proc.returncode != 0:
                self.output.error(proc.stdout[-4000:])
                raise ConanException(f"link failed: {out_so}")
            self.output.info(f"共享库: {out_so} ({len(os_objs)} 对象)")

    # ------------------------------------------------------------------
    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # 头文件：tmp/bobcat/<class> → include/bobcat/<class>
        #（消费者 #include <bobcat/arg>，包含根为 include/）
        copy(self, "*",
             src=os.path.join(src, "tmp", "bobcat"),
             dst=os.path.join(pkg, "include", "bobcat"))

        if self.options.shared:
            # 共享库：真实版本文件 + soname 软链（复刻上游 _shared_library 布局）
            copy(self, "libbobcat.so.*",
                 src=os.path.join(src, "tmp", "libso"),
                 dst=os.path.join(pkg, "lib"))
            major = self.version.split(".")[0]
            versioned = os.path.join(pkg, "lib", f"libbobcat.so.{self.version}")
            if os.path.exists(versioned):
                for name in (f"libbobcat.so.{major}", "libbobcat.so"):
                    link = os.path.join(pkg, "lib", name)
                    if not os.path.exists(link):
                        os.symlink(f"libbobcat.so.{self.version}", link)
        else:
            copy(self, "libbobcat.a",
                 src=os.path.join(src, "tmp", "liba"),
                 dst=os.path.join(pkg, "lib"))

        # 许可证（Conan 惯例位置）
        copy(self, "LICENSE", src=src, dst=os.path.join(pkg, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "BOBCAT")
        # 包含根 = include/，头以 <bobcat/xxx> 形式引用（上游安装布局）
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = collect_libs(self)
        # 上游共享库链接行带 -pthread；OHOS 的 pthread 接口在 libc 内，
        # 无独立 libpthread（见 docs/ADAPTATION_GUIDE.md §8），不需要 system_libs
