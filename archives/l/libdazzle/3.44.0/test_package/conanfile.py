#!/usr/bin/env python3
"""Conan test_package — libdazzle 3.44.0 consumer test (L1).

直接从依赖解析出的 cpp_info 拼 clang 命令行编译消费者程序：
本 OHOS worker 上 PkgConfigDeps 生成的 PKG_CONFIG_PATH 不可靠地注入
test 构建环境（playerctl 2.4.1.1 实证），读 cpp_info 是确定性的。

运行期用 realdep_libs 目录实体化依赖 .so（HMDFS 对符号链接链的
loader 解析不稳定，见踩坑清单 #29/#36），LD_LIBRARY_PATH 优先于
DT_RUNPATH，必然命中实体文件。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, Environment


class LibdazzleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # 实体化全部依赖共享库到 realdep_libs（conan 解压产物在本宿主
        # HMDFS 上对 clang/loader 稳定 ENOENT——主包配方同款规避；
        # 普通进程 shutil 写出的文件对一切进程可读），链接与运行都用
        # 这个镜像目录的绝对路径。
        real_dir = os.path.join(self.build_folder, "realdep_libs")
        os.makedirs(real_dir, exist_ok=True)
        for req in self.dependencies.host.values():
            if not req.package_folder:
                continue
            for libdir in req.cpp_info.libdirs:
                folder = libdir if os.path.isabs(libdir) else os.path.join(req.package_folder, libdir)
                if not os.path.isdir(folder):
                    continue
                for entry in sorted(os.listdir(folder)):
                    if ".so" in entry and not os.path.exists(os.path.join(real_dir, entry)):
                        src = os.path.join(folder, entry)
                        try:
                            if os.path.islink(src):
                                shutil.copy2(src, os.path.join(real_dir, entry))
                            else:
                                shutil.copyfile(src, os.path.join(real_dir, entry))
                        except OSError:
                            pass
        # LD_LIBRARY_PATH 优先于 DT_RUNPATH，实体目录必然命中（踩坑清单 #36 范式）
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", real_dir)
        env.vars(self, scope="run").save_script("conanrealdep_run")

    def build(self):
        cc = os.environ.get("CC") or "clang"

        inc_dirs, lib_dirs, libs = [], [], []
        for dep in self.dependencies.values():
            ci = dep.cpp_info
            inc_dirs.extend(ci.includedirs)
            lib_dirs.extend(ci.libdirs)
            libs.extend(ci.libs)
            for comp in ci.components.values():
                inc_dirs.extend(comp.includedirs)
                lib_dirs.extend(comp.libdirs)
                libs.extend(comp.libs)

        def _uniq(seq):
            seen, out = set(), []
            for x in seq:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            return out

        inc_dirs = _uniq(inc_dirs)
        lib_dirs = _uniq(lib_dirs)
        libs = _uniq(libs)

        inc = " ".join("-I%s" % p for p in inc_dirs)
        lib = " ".join("-L%s" % p for p in lib_dirs)
        # 依赖库一律解析为 realdep_libs / 依赖目录中的绝对路径 .so：
        # 本宿主 conan 解压产物对 clang 稳定 ENOENT，仅 -l 搜索与
        # 指向解压产物的路径都不可靠；镜像副本为普通进程写入，稳定。
        real_dir = os.path.join(self.build_folder, "realdep_libs")
        lnk_toks = []
        for name in libs:
            tok = "-l%s" % name
            for d in [real_dir] + lib_dirs:
                cand = os.path.join(d, "lib%s.so" % name)
                if os.path.isfile(cand):
                    tok = cand
                    break
            lnk_toks.append(tok)
        lnk = " ".join(lnk_toks)
        cmd = "{cc} test.c -o test_libdazzle {inc} {lib} {lnk}".format(
            cc=cc, inc=inc, lib=lib, lnk=lnk)
        self.run(cmd, shell=True, env="conanbuild")
        # 新编译 ELF 在 el2 HMDFS 执行权限整窗抖动 → 运行前自签
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if os.path.isfile(signer):
            self.run(
                "%s sign -inFile test_libdazzle -outFile test_libdazzle -selfSign 1"
                % signer, env="conanbuild")

    def test(self):
        # L0d 文本门禁要求 test() 内有字面 self.run 直跑消费者程序
        self.run("./test_libdazzle", env="conanrun")
