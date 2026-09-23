# Conan 2.x recipe — combat/0.8.1 ("Combat — CORBA Scripting with Tcl")
#
# combat 0.8.1 是纯 Tcl 包：orb/*.tcl 拷贝安装（无 configure/make），bin/idl2tcl
# 与 bin/iordump 是 sh 包装的 Tcl 脚本。唯一 C 代码是可选 tclkill/kill.c 扩展
# （Tcl stubs），归档自带的 kill-linux-x86.so 仅 i386、aarch64 不可用，因此本
# 配方用设备编译器（profile tools.build:compiler_executables）现场编译 kill.so。
#
# Itcl 说明：combat.tcl 在 Itcl 缺失时回退 `package require tcl++`，但 0.8.1
# 归档并不携带 tcl++ —— Itcl 是事实上的硬依赖。设备 tcl/8.6.16 包的
# lib/itcl4.3.2/ 只有 libitcl4.3.2.so + stub 静态库（其配方按 *.so*/*.a 通配
# 拷贝，未收录 Itcl_Init 必需的 itcl.tcl 等库脚本），因此本配方从与已发布
# libitcl4.3.2.so 同源同版本的 Tcl 源码包中提取 itcl 库脚本，随包放入
# lib/combat/itcl/ 并生成 pkgIndex.tcl（加载前设置 ITCL_LIBRARY），
# orb/combat.tcl 的补丁会优先发现该目录。

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


# 生成到 lib/combat/itcl/pkgIndex.tcl。Itcl_Init 按编译期前缀与 ITCL_LIBRARY
# 查找 itcl.tcl；共享库与其库脚本同目录分发时在索引内显式指向该目录。
ITCL_PKG_INDEX = """\
# Itcl support shipped next to Combat for OHOS.
# The tcl dependency package ships libitcl4.3.2.so without its library
# scripts; this index pairs the shared object with the itcl*.tcl scripts
# colocated in this directory. Itcl_Init needs the scripts, so point
# ITCL_LIBRARY here before loading.
package ifneeded Itcl 4.3.2 [list apply {{dir} {
    set ::env(ITCL_LIBRARY) $dir
    load [file join $dir libitcl4.3.2.so]
}} $dir]
"""

# 与 tcl/8.6.16 conandata.yml 同一归档：URL 可达性已被该包 CI 验证，
# SHA256 与已发布 libitcl4.3.2.so 同源同版本（Tcl 8.6.16 内置 pkgs/itcl4.3.2）。
TCL_SOURCE_URL = "https://prdownloads.sourceforge.net/tcl/tcl8.6.16-src.tar.gz"
TCL_SOURCE_SHA256 = "91cb8fa61771c63c262efb553059b7c7ad6757afa5857af6265e4b0bdc2a14a5"


class CombatConan(ConanFile):
    name = "combat"
    version = "0.8.1"
    description = "Combat — CORBA Scripting with Tcl (pure Tcl CORBA ORB)"
    license = "TCL"
    homepage = "http://www.fpx.de/Combat/"
    url = "https://deb.debian.org/debian/pool/main/c/combat/combat_0.8.1.orig.tar.gz"
    topics = ("corba", "orb", "tcl", "scripting")
    settings = "os", "compiler", "build_type", "arch"
    requires = "tcl/8.6.16"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def build(self):
        apply_conandata_patches(self)

        # ── tclkill/kill.c → kill.so（扩展以 Tcl stubs 静态链，不产生对
        #    libtcl8.6 的 DT_NEEDED；-Wl,-z,now 满足 musl BIND_NOW 约束）──
        tcl = self.dependencies["tcl"]
        include_dir = tcl.cpp_info.includedirs[0]
        lib_dir = tcl.cpp_info.libdirs[0]
        stub_lib = os.path.join(lib_dir, "libtclstub8.6.a")
        if not os.path.isfile(stub_lib):
            raise ConanException(f"tcl dependency lacks Tcl stub library: {stub_lib}")
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c", "clang")
        kill_c = os.path.join(self.source_folder, "tclkill", "kill.c")
        kill_so = os.path.join(self.build_folder, "kill.so")
        self.run(
            f'"{cc}" -shared -fPIC -DUSE_TCL_STUBS -I"{include_dir}" '
            f'"{kill_c}" -o "{kill_so}" "{stub_lib}" -Wl,-z,now',
            env="conanbuild",
        )

        # ── 提取 Itcl 库脚本（供 package() 随包分发，见文件头说明）──
        get(
            self,
            TCL_SOURCE_URL,
            sha256=TCL_SOURCE_SHA256,
            destination=self.build_folder,
            strip_root=True,
        )
        itcl_library = os.path.join(self.build_folder, "pkgs", "itcl4.3.2", "library")
        for name in ("itcl.tcl", "itclHullCmds.tcl", "itclWidget.tcl"):
            if not os.path.isfile(os.path.join(itcl_library, name)):
                raise ConanException(f"itcl library script missing in tcl source: {name}")

    def package(self):
        src = self.source_folder
        bld = self.build_folder
        pkg = self.package_folder

        # bin/：sh 包装的 Tcl 脚本工具（补丁已插入 tclsh8.6 探测分支）
        copy(self, "idl2tcl", os.path.join(src, "bin"), os.path.join(pkg, "bin"), keep_path=False)
        copy(self, "iordump", os.path.join(src, "bin"), os.path.join(pkg, "bin"), keep_path=False)

        # lib/combat/：纯 Tcl ORB（combat.tcl 等已补丁，优先发现 itcl/ 子目录）
        copy(self, "*.tcl", os.path.join(src, "orb"), os.path.join(pkg, "lib", "combat"))

        # lib/combat/itcl/：Itcl 库脚本（取自 Tcl 源码包）+ 已发布包内的
        # libitcl4.3.2.so + 生成 pkgIndex.tcl（设置 ITCL_LIBRARY 后 load）
        itcl_dst = os.path.join(pkg, "lib", "combat", "itcl")
        itcl_library = os.path.join(bld, "pkgs", "itcl4.3.2", "library")
        copy(self, "itcl*.tcl", itcl_library, itcl_dst, excludes="test_*")
        tcl = self.dependencies["tcl"]
        itcl_so_src = os.path.join(tcl.cpp_info.libdirs[0], "itcl4.3.2", "libitcl4.3.2.so")
        if not os.path.isfile(itcl_so_src):
            raise ConanException(f"tcl dependency lacks libitcl4.3.2.so: {itcl_so_src}")
        shutil.copy2(itcl_so_src, os.path.join(itcl_dst, "libitcl4.3.2.so"))
        with open(os.path.join(itcl_dst, "pkgIndex.tcl"), "w", encoding="utf-8", newline="\n") as f:
            f.write(ITCL_PKG_INDEX)

        # lib/tclkill/：补丁后的包索引（优先 kill.so）+ 纯 Tcl 回退 + 编译产物
        kill_dst = os.path.join(pkg, "lib", "tclkill")
        copy(self, "unixkill.tcl", os.path.join(src, "tclkill"), kill_dst, keep_path=False)
        copy(self, "pkgIndex.tcl", os.path.join(src, "tclkill"), kill_dst, keep_path=False)
        kill_so = os.path.join(bld, "kill.so")
        if not os.path.isfile(kill_so):
            raise ConanException("kill.so was not built in build()")
        shutil.copy2(kill_so, os.path.join(kill_dst, "kill.so"))
        os.chmod(os.path.join(kill_dst, "kill.so"), 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["lib/combat", "lib/tclkill"]
        # 消费者契约（与上游一致：Tcl 侧自行 lappend auto_path）：
        #   lappend auto_path $COMBAT_ROOT/lib/combat $COMBAT_ROOT/lib/tclkill
        # tclsh8.6 由依赖 tcl/8.6.16 的 runenv PATH 提供。
        self.runenv_info.define("COMBAT_ROOT", self.package_folder)
