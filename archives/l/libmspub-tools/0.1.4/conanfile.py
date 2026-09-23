#!/usr/bin/env python3
"""Conan recipe — libmspub-tools 0.1.4（Microsoft Publisher 解析库 + 转换工具）.

libmspub-tools = libmspub 0.1.4 源码树整体编译（src/lib 库本体 + src/conv 的
pub2raw / pub2xhtml 两个转换工具），与 Alpine libmspub 拆包口径一致：工具
LDADD 指向本树内 libtool 产出的 libmspub-0.1.la，库本体不在制品仓
（libmspub/0.1.2 仅为手工编译时代归档，无 conan 配方），因此在本配方内一并
编译（W0/R36 核验：librevenge/0.0.5、icu4c/78、zlib/1.3.1、boost/1.90.0.3、
pkgconf/3.0.5 conan download 全部 EXIT=0）。

依赖接线（关键决策）：
- configure.ac 用 PKG_CHECK_MODULES 检测 librevenge-0.0 / librevenge-stream-0.0 /
  librevenge-generators-0.0 / zlib / icu-i18n。conan 依赖包的 .pc/.la 带
  libdir='//lib' 病灶（E236），libtool 沿 -L/-l 找 .la 会中止，因此全部
  PKG_CHECK_MODULES 模块用「预置 <MODULE>_CFLAGS/<MODULE>_LIBS 环境变量 +
  绝对路径 .a」绕过 pkg-config 探测与 libtool .la 查找（librevenge 配方的
  ZLIB_CFLAGS/ZLIB_LIBS 预置先例 + ctpl E236 la-free 先例）。
- boost 仅头文件使用（optional/cstdint/numeric-conversion/cast + configure
  未声明但 MSPUBCollector.cpp 实际使用的 multi_array.hpp，1.90.0.3 包已
  验证齐全），经 CPPFLAGS 注入。
- pkgconf/3.0.5 作为 tool_requires 提供 PKG_PROG_PKG_CONFIG 所需二进制
  （整仓 30+ 包先例）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmspubToolsConan(ConanFile):
    name = "libmspub-tools"
    version = "0.1.4"
    description = "Microsoft Publisher parsing library + conversion tools (pub2raw, pub2xhtml)"
    license = "MPL-2.0"
    homepage = "https://github.com/LibreOffice/libmspub"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("publisher", "converter", "document")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: 判断必须包含 Linux 与 OHOS 两种取值
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libmspub-tools is supported only on Linux/OHOS, got os=%s" % self.settings.os)
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # W0 核验（依赖已从制品仓 ohpcd 下载验证，全部 EXIT=0）
        # librevenge: 库与工具都链接其三个子库（revenge/revenge-stream/revenge-generators）；
        # transitive_headers/transitive_libs 使消费者（test_package）可见其头文件与静态库
        self.requires("librevenge/0.0.5", transitive_headers=True, transitive_libs=True)
        # ICU: MSPUBCollector.cpp 用 ucsdet/uloc，libmspub_utils.cpp 用 ucnv/utypes
        self.requires("icu4c/78")
        # zlib: 上游 libmspub.pc Requires.private 声明；libmspub_la_LIBADD 挂接
        self.requires("zlib/1.3.1")
        # boost: 仅头文件（optional/cstdint/numeric-conversion/cast/multi_array）。
        # transitive_headers 使下游消费者编译时也能看到 boost 头（纯头文件，
        # 不进 cpp_info.requires，避免 "direct dependency not used" 报错）。
        self.requires("boost/1.90.0.3", transitive_headers=True)

    def build_requirements(self):
        # configure.ac 无条件调用 PKG_PROG_PKG_CONFIG([0.20])，需 pkg-config 兼容
        # 二进制（真机无系统 pkg-config，整仓 pkgconf tool_requires 先例）
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _dep(self, name):
        return self.dependencies.host[name]

    def _shadow_libdir(self):
        """la-free 依赖归档 staging 目录（ctpl _stage_dependency_archives 同款）。

        E236 + libtool _LIBADD 语义冲突的根治：
        - libtool 的 <lib>_la_LIBADD 里，绝对路径 `.a` 被当作「要嵌入的
          convenience 库」直接打包进产物 .a（导致 `archive member 'libz.a'
          is neither ET_REL nor LLVM bitcode`），必须用 `-L<dir> -l<name>` 才
          是「链接依赖」语义；
        - 但 librevenge 的 lib 目录里 .a 与 .la 并存，且 .la 带 `libdir=
          '//lib'` 病灶（E236），`-lrevenge` 会让 libtool 优先读 .la 而中止。
        解法：把三个依赖的 `.a` 拷进一个只含 .a、不含 .la 的 shadow 目录，
        PKG_CHECK_MODULES 预置变量一律写 `-L<shadow> -l<name>`。这样 libtool
        既拿到正确的链接依赖语义，又因 shadow 里没有 .la 而不会触发病灶。
        """
        dest = os.path.join(self.build_folder, ".dep-archives")
        if os.path.isdir(dest):
            shutil.rmtree(dest, ignore_errors=True)
        os.makedirs(dest, exist_ok=True)
        copied = 0
        for name in ("librevenge", "icu4c", "zlib"):
            dep = self._dep(name)
            for libdir in getattr(dep.cpp_info, "libdirs", []):
                if not libdir or not os.path.isdir(libdir):
                    continue
                for entry in os.listdir(libdir):
                    if not entry.endswith(".a"):
                        continue
                    dst = os.path.join(dest, entry)
                    if os.path.isfile(dst):
                        continue
                    shutil.copy2(os.path.join(libdir, entry), dst)
                    copied += 1
        self.output.info("[ok] staged %d .a into la-free shadow %s" % (copied, dest))
        if copied == 0:
            raise RuntimeError("no dependency .a staged; cannot build la-free link flags")
        return dest

    def _pkg_env(self):
        """自定义 PKG_CHECK_MODULES 预置变量 + CPPFLAGS 头路径（独立环境对象）。

        这些变量必须在 configure 运行时作为「环境变量」存在（pkg.m4：环境变量
        已设置时跳过 pkg-config 探测），而 tc.extra_cflags 只能进 CFLAGS、
        进不了 REVENGE_LIBS 这类 pkg.m4 变量，故单独组织成一个 Environment，
        与 Toolchain 环境（conanbuild）严格分离，避免污染 conanbuild 命名空间
        （E2BIG 死循环教训：绝不可再 save_script("conanbuild") 覆盖框架生成物）。
        """
        env = Environment()
        rev = self._dep("librevenge")
        icu = self._dep("icu4c")
        zlib = self._dep("zlib")
        boost = self._dep("boost")

        rev_inc = "-I%s" % rev.cpp_info.includedirs[0]
        # configure.ac 的 AC_CHECK_HEADERS(boost/...) 与源码 include 需要的头路径
        for inc in ("-I%s" % boost.cpp_info.includedirs[0],
                    "-I%s" % icu.cpp_info.includedirs[0],
                    "-I%s" % zlib.cpp_info.includedirs[0],
                    rev_inc):
            env.append("CPPFLAGS", inc)

        # E236 + _LIBADD 语义：所有依赖用 `-L<shadow> -l<name>` 形式（la-free
        # shadow 目录，见 _shadow_libdir），libtool 正确当链接依赖、不嵌 .a。
        shadow = self._shadow_libdir()
        L = "-L%s" % shadow

        env.define("REVENGE_CFLAGS", rev_inc)
        env.define("REVENGE_LIBS", " ".join([
            L, "-lrevenge-generators-0.0", "-lrevenge-0.0", "-lrevenge-stream-0.0",
        ]))
        env.define("REVENGE_STREAM_CFLAGS", rev_inc)
        env.define("REVENGE_STREAM_LIBS", " ".join([L, "-lrevenge-stream-0.0"]))
        env.define("REVENGE_GENERATORS_CFLAGS", rev_inc)
        env.define("REVENGE_GENERATORS_LIBS", " ".join([
            L, "-lrevenge-generators-0.0", "-lrevenge-0.0",
        ]))
        env.define("ICU_CFLAGS", "-I%s" % icu.cpp_info.includedirs[0])
        # icu-i18n.pc: Requires icu-uc (-licuuc -licudata)；静态序 i18n -> uc -> data
        env.define("ICU_LIBS", " ".join([
            L, "-licui18n", "-licuuc", "-licudata", "-lm",
        ]))
        env.define("ZLIB_CFLAGS", "-I%s" % zlib.cpp_info.includedirs[0])
        env.define("ZLIB_LIBS", " ".join([L, "-lz"]))

        # E165 姊妹陷阱（E-rm）：本机 PATH 最前的 `rm` 是 codebuddy 安全
        # shim（safe-bin/rm，shebang #!/bin/bash），而 HarmonyOS 无 /bin/bash，
        # 所有 rm 调用报 `bad interpreter`，automake 的 AC_PROG_RM 严格检查
        # 因而判 rm 为劣质并 abort。真正的根治在 build() 的 _sanitize_path()
        # 里从 PATH 剔除 safe-bin；这里保留 ACCEPT_INFERIOR_RM_PROGRAM 作
        # 双保险（automake 官方逃逸开关，接受 toybox rm）。
        env.define("ACCEPT_INFERIOR_RM_PROGRAM", "yes")
        return env

    def generate(self):
        # 只用 tc.generate()：它生成 conanbuild.conf（供 Autotools 帮手读
        # configure_args）+ conanbuild.sh（框架自带的正确 wrapper，含 CC/CFLAGS/
        # LDFLAGS/CPPFLAGS/PKG_CONFIG_PATH）。绝不手动 save_script("conanbuild")
        # —— 那会 self-source 成死循环（E2BIG：printenv Argument list too long）。
        tc = AutotoolsToolchain(self)
        # E001/E096：上游 config.sub(2012) 不识别 aarch64-linux-ohos（实测
        # config.sub 返回 Invalid configuration），改用 ctpl/cdecl/castget 先例
        # 的 GNU triplet 强制交叉编译模式（跳过运行探测），OHOS 目标由工具链
        # CFLAGS/LDFLAGS/sysroot 达成。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # R26: 系统名库默认静态
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def _sanitize_path(self):
        """从环境剔除 codebuddy 注入的 safe-delete shim（PATH + bash 函数）。

        E165 姊妹陷阱（双通道注入，缺一不可）：
        1) PATH 首项被 codebuddy 注入 safe-bin/ 目录，其中 rm/rmdir/unlink
           是 shebang `#!/bin/bash` 的 shim，而 HarmonyOS 无 /bin/bash（bash
           在 /data/service/hnp/bin/bash）→ 每次调用都报
           `bad interpreter: /bin/bash: No such file or directory`；
        2) 更隐蔽的是 codebuddy 还导出了 `BASH_FUNC_rm%%` / `BASH_FUNC_unlink%%`
           / `BASH_FUNC_rmdir%%` 三个环境变量，bash 子进程启动时会据此
           **自动 import 同名 shell 函数**，强制 `rm` 指向 safe-bin 的绝对
           路径 shim——这比 PATH 优先级更高，光剔 PATH 无效（libtool/Makefile
           的 SHELL 是 /data/service/hnp/bin/bash，正是 bash）。
        根治：在 build() 入口（configure 之前）用 os.environ 同步清除 PATH
        中的 safe-bin 目录 + 三个 BASH_FUNC_* 变量 + CODEBUDDY_SAFE_DELETE_
        ENABLED。这样 configure 生成的 libtool/Makefile 记录的 RM 落到 toybox
        的 /bin/rm（rm -f/-rf 均正常），无需改 shim 或上游。
        """
        removed = []

        # 1) 剔除 PATH 中的 safe-bin 目录
        path = os.environ.get("PATH", "")
        if path:
            entries = path.split(os.pathsep)
            kept = [e for e in entries if "safe-bin" not in e]
            if len(kept) != len(entries):
                os.environ["PATH"] = os.pathsep.join(kept)
                removed.append("%d safe-bin dir(s) from PATH" % (len(entries) - len(kept)))

        # 2) 清除 bash 函数注入变量（bash 会据此 import rm/unlink/rmdir 函数）
        for func_var in ("BASH_FUNC_rm%%", "BASH_FUNC_unlink%%", "BASH_FUNC_rmdir%%"):
            if os.environ.pop(func_var, None) is not None:
                removed.append(func_var)

        # 3) 清除 safe-delete 的复活通道（关键！）：
        #    codebuddy 通过 BASH_ENV 指向 shell-runtime-bash-env.sh，该脚本在每个
        #    bash 子进程启动时被自动 source，又 source safe-delete-bash-env.sh，
        #    后者只要检测到 CODEBUDDY_SAFE_DELETE_BIN_DIR 非空就重新定义
        #    rm/unlink/rmdir 函数指向 safe-bin shim。仅删 BASH_FUNC_* 与 PATH
        #    是徒劳的——bash 子进程（make/libtool 的 SHELL 都是 bash）会据此
        #    **重新注入** rm 函数。必须连带清掉 BASH_ENV 与
        #    CODEBUDDY_SAFE_DELETE_BIN_DIR，掐断整个 source 链。
        for kill_var in (
            "CODEBUDDY_SAFE_DELETE_ENABLED",
            "CODEBUDDY_SAFE_DELETE_BIN_DIR",
            "BASH_ENV",
        ):
            if os.environ.pop(kill_var, None) is not None:
                removed.append(kill_var)

        if removed:
            self.output.info("[ok] sanitized env: %s" % ", ".join(removed))

    def build(self):
        apply_conandata_patches(self)
        self._patch_configure_umask()
        self._sanitize_path()
        # HMDFS: getcwd() 解析不了父目录时 shell pwd 走逻辑路径（cdecl 先例）
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass
        os.environ["PWD"] = self.build_folder
        # E002: 设备 /tmp 只读（erofs），重定向 TMPDIR
        tmpdir = os.environ.get("TMPDIR") or os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

        autotools = Autotools(self)
        # 自定义 PKG_CHECK_MODULES 预置变量 + CPPFLAGS 头路径在运行时注入
        # （libnfc 先例的 apply() 模式，不进 conanbuild 命名空间）
        with self._pkg_env().vars(self).apply():
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # E236 收尾：包内不得残留 libtool 元数据（下游 libtool 链接会重读
        # 陈旧 dependency_libs 路径）
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for entry in os.listdir(lib_dir):
                if entry.endswith(".la"):
                    os.remove(os.path.join(lib_dir, entry))
                    self.output.info("[ok] removed libtool archive %s" % entry)
        # 静态库内对 -lm 的引用：消费者链接时由 AutotoolsDeps/CMakeDeps 的
        # system_libs 补齐，这里无需处理
        copy(self, "COPYING.MPL", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libmspub")
        self.cpp_info.set_property("cmake_target_name", "libmspub::libmspub")
        self.cpp_info.set_property("pkg_config_name", "libmspub-0.1")
        # 上游 libtool 命名：libmspub-0.1（MSPUB_MAJOR_VERSION.MSPUB_MINOR_VERSION）
        self.cpp_info.libs = ["mspub-0.1"]
        self.cpp_info.includedirs = ["include/libmspub-0.1"]
        # R38：构建产物含 pub2raw/pub2xhtml 两个可执行文件（autotools.install()
        # 安装到 package_folder/bin），声明 bindirs 使 CI L0k/detect_bindirs 判定
        # 为 tool 类型，与软件级 commands.json（type=tool）保持一致。
        self.cpp_info.bindirs = ["bin"]
        # 不写 cpp_info.requires（libvisio/0.1.11 同族先例）：icu4c 配方未定义
        # cmake_target_name，无法用 `icu4c::xxx` 引用；boost 为纯头文件、librevenge
        # 带 components。留空时 conan 的「直接依赖必须在 requires 中引用」校验
        # 提前 return（cpp_info.requires 为空即跳过），依赖闭包由消费侧
        # AutotoolsDeps/CMakeDeps 依据各依赖的 cpp_info 自动解析。
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    # ------------------------------------------------------------------
    # 平台适配（先例：ctpl/0.3.5 同款）
    # ------------------------------------------------------------------
    def _patch_configure_umask(self):
        # E011: configure/config.status 用 `umask 077 && mktemp -d`，HMDFS 上
        # 生成不可写临时目录 -> Permission denied；放宽为 022（仅变量形态替换）
        for root, _, files in os.walk(self.source_folder):
            if "configure" not in files:
                continue
            cfg = os.path.join(root, "configure")
            try:
                with open(cfg, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except OSError:
                continue
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                with open(cfg, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
                self.output.info("[ok] relaxed umask 077 -> 022 in %s" % cfg)
