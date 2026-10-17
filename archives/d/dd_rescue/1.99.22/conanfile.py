#!/usr/bin/env python3
"""Conan recipe — dd_rescue 1.99.22（garloff.de，autoconf + 手写 Makefile）。

⚠️ **与 GNU ddrescue 不是同一个项目**：GNU 版（gnu.org，C++，产物 ddrescue /
ddrescuelog）在仓库内已有 `archives/d/ddrescue/1.30`；本包是 **Kurt Garloff 的
dd_rescue**（带下划线，C，产物 dd_rescue 与 libddr_* 插件）。

OHOS 适配要点（**全部为实测结论**，逐条对应下方实现）：
1. **官方 tarball 不含预生成的 `configure`**（只有 `configure.ac`）→ 必须先
   `autoheader` + `autoconf`（上游 `autogen.sh` 即做这两步）。
2. **`configure` 内 `umask 077` 在 HMDFS 上会让 `config.status` 写临时文件失败**
   （实测：`./config.status[666]: can't create ./confXXXXXX/defines.awk:
   Permission denied` → `could not setup config headers machinery`）。
   根因是 `configure:5547/5552` 的 `(umask 077 && mktemp -d)`：HMDFS 上按 077
   建出的目录权限为 `drwx--S--- (2700)`，而当前 uid 与该文件 owner 不同 →
   写不进去。**改为 `umask 022` 后 configure rc=0、`config.h` 正常生成**（实测）。
3. **`Makefile` 里 `CC = gcc` 是硬赋值**（非 `?=`）→ 会**覆盖环境变量**，
   必须在 `make` 命令行显式传 `CC=`。
4. **`OS = $(shell uname)` + `ifeq ($(OS), Linux)` 门控 `OBJECTS += fstrim.o`**
   → OHOS 上 `uname` 返回 `HarmonyOS`，条件不成立 → 缺 `fstrim.o` →
   链接报 `undefined symbol: fstrim`。**命令行传 `OS=Linux` 即可**（实测 rc=0）。
5. **OHOS 无 coreutils `install`**（E188），且 Makefile 的
   `INSTASROOT = -o root -g root` 在非 root 下必然失败 → **不调用 `make install`**，
   由本配方按 upstream `install` 目标的布局自行落盘。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (copy, get, chmod, mkdir, replace_in_file)
from conan.tools.layout import basic_layout

# 真实产物（实测 `BINTARGETS` / `LIBTARGETS`）
EXE_TARGETS = ["dd_rescue"]           # BINTARGETS = dd_rescue
SO_TARGETS = [                        # LIBTARGETS（libddr_MD5.so 是符号链接）
    "libddr_hash.so",
    "libddr_null.so",
    "libddr_crypt.so",
]
MD5_LINK = "libddr_MD5.so"            # 实测为 -> libddr_hash.so 的符号链接


class DdRescueConan(ConanFile):
    name = "dd_rescue"
    version = "1.99.22"
    description = ("dd_rescue — data recovery / copy tool with bad-block handling "
                   "and a plugin (libddr_*) architecture")
    license = "GPL-2.0-or-later"
    homepage = "https://www.garloff.de/kurt/linux/ddrescue/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    options = {
        # 门控：默认关，交付包不跑上游测试（上游 check 会构建 6 个辅助程序并做大量 IO）
        "run_upstream_tests": [True, False],
    }
    default_options = {
        "run_upstream_tests": False,
    }

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 官方 tarball 只有 configure.ac —— 上游 autogen.sh 即 autoheader + autoconf
        self.run("autoheader", cwd=self.source_folder)
        self.run("autoconf", cwd=self.source_folder)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            raise ConanException("dd_rescue: autoconf 未生成 configure（上游 tarball "
                                 "不含预生成的 configure）")

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        src = self.source_folder
        # 坑 2：HMDFS 上 configure 的 `umask 077 && mktemp -d` 会写出不可写的临时目录
        for name in ("configure", "config.status"):
            p = os.path.join(src, name)
            if os.path.isfile(p):
                replace_in_file(self, p, "umask 077", "umask 022")

        # TMPDIR 指向 conan build 目录（设备默认 TMPDIR 在 HMDFS 上同样有权限问题）
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        os.environ["TMPDIR"] = tmp

        self.run(f'./configure --prefix="{self.package_folder}"', cwd=src)

        cc = self._compiler_cmd()
        # 坑 3：Makefile 硬赋值 `CC = gcc`，必须在命令行覆盖
        # 坑 4：OS=Linux 让 `OBJECTS += fstrim.o` 生效，否则 undefined symbol: fstrim
        mk = f"CC={cc} OS=Linux"

        if self.options.get_safe("run_upstream_tests"):
            self._fix_upstream_test_scripts()
            mk += " check"          # 构建 + 实跑上游测试
        self.run(f"make -j1 {mk}", cwd=src)

        for t in EXE_TARGETS + SO_TARGETS:
            if not os.path.isfile(os.path.join(src, t)):
                raise ConanException(f"dd_rescue: 预期产物缺失: {t}")

    def _fix_upstream_test_scripts(self):
        """上游测试脚本的两个可移植性问题（仅在实跑测试时修正，见 notes.md）。

        ① 6 个 `test_*.sh` 的 shebang 为 `#!/bin/bash`，而 **OHOS 无 `/bin/bash`**
           → `bad interpreter: No such file or directory`（实测 Error 126）。
        ② `test_crypt.sh:128/150` 的守卫写作 `test -n "$HAVE_LZO"`，而 Makefile 传进来的
           是**字符串 "0"**（`HAVE_LZO=$(HAVE_LZO)`）→ `test -n "0"` **为真** → 即使未启用
           LZO 也会进入插件链分支，去加载不存在的 `libddr_lzo.so` 而失败（实测
           `Could not load plugin ./libddr_lzo.so` → Error 1）。改为 `= "1"` 后通过。

        注：`test_crypt.sh:286/289` 的 `test -n "$HAVE_AESNI"` / `"$HAVE_AESARM"` 同理但
        **不可改** —— 二者由 `grep /proc/cpuinfo` 得出，非 Makefile 传入，空值即「不适用」，
        `test -n` 语义正确。
        """
        src = self.source_folder
        # ① shebang：改为经 env 解析，避免硬编码设备专属路径
        bash = os.environ.get("CONFIG_SHELL") or "bash"
        for name in sorted(os.listdir(src)):
            if not (name.startswith("test_") and name.endswith(".sh")):
                continue
            p = os.path.join(src, name)
            replace_in_file(self, p, "#!/bin/bash",
                            f"#!{bash}" if os.path.isabs(bash) else "#!/usr/bin/env bash",
                            strict=False)
        # ② 守卫：test -n 收到字符串 "0" 会误判为真
        replace_in_file(
            self, os.path.join(src, "test_crypt.sh"),
            'if test -n "$HAVE_LZO"; then',
            'if test "$HAVE_LZO" = "1"; then',
            strict=False)

    def _compiler_cmd(self):
        """取编译器绝对路径（Makefile 的 CC=gcc 会覆盖环境变量）。"""
        for var in ("CC", "CXX"):
            v = os.environ.get(var)
            if v:
                return v.split()[0]
        return "clang"

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        libdir = os.path.join(self.package_folder, "lib")
        mkdir(self, bindir)
        mkdir(self, libdir)

        # 不调 `make install`（坑 5）：OHOS 无 coreutils install + INSTASROOT 需 root
        for exe in EXE_TARGETS:
            copy(self, exe, src=src, dst=bindir)
            chmod(self, os.path.join(bindir, exe), execute=True)
        for so in SO_TARGETS:
            copy(self, so, src=src, dst=libdir)
        # libddr_MD5.so 是符号链接，copy() 会跟随链接 → 这里显式重建
        link = os.path.join(libdir, MD5_LINK)
        if os.path.isfile(os.path.join(src, MD5_LINK)) and not os.path.islink(link):
            try:
                os.symlink("libddr_hash.so", link)
            except OSError:
                pass

        copy(self, "COPYING*", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README*", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.1", src=src, dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
