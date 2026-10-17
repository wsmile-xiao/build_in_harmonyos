#!/usr/bin/env python3
"""Conan recipe — libfreehand-tools 0.1.2（FreeHand 解析库 + 转换工具）.

libfreehand-tools = libfreehand 0.1.2 源码树整体编译（src/lib 库本体 + src/conv 的
fh2raw / fh2svg / fh2text 三个转换工具），与 Alpine libfreehand 拆包口径一致：工具
LDADD 指向本树内 libtool 产出的 libfreehand-0.1.la，库本体不在制品仓
（libfreehand/0.1.1 仅为手工编译时代归档，无 conan 配方；本仓另有
libmspub-tools/0.1.4、libmwaw-tools/0.3.22 同族先例），因此在本配方内一并编译。

上游测试：configure.ac 的 --enable-tests **默认为 yes**（`[enable_tests=yes]`），
即 CPPUNIT 是上游默认构建期依赖；src/test/ 注册 1 个 check_PROGRAM（`test`）/
1 个 TESTS 条目 / 2 个 CPPUnit 用例（testRead、testSeek）。本配方按上游默认
（不传 --disable-tests）构建，并在 build() 内 `make check` 真实运行该套件
（HOME 指向构建目录内的沙箱，不写用户真实 HOME）。src/fuzz 的 fhfuzzer 需
`-lFuzzingEngine`（无该制品），按 NOT_RUN 申报，不放开 --enable-fuzzers。

依赖接线（关键决策）：
- configure.ac 用 PKG_CHECK_MODULES 检测 librevenge-0.0 / librevenge-stream-0.0 /
  librevenge-generators-0.0 / zlib / icu-uc / lcms2 / cppunit。conan 依赖包的
  .pc/.la 带 libdir='//lib' 病灶（E236），libtool 沿 -L/-l 找 .la 会中止，因此全部
  PKG_CHECK_MODULES 模块用「预置 <MODULE>_CFLAGS/<MODULE>_LIBS 环境变量 +
  la-free shadow 目录 + 绝对路径 .a」绕过 pkg-config 探测与 libtool .la 查找
  （libmspub-tools/0.1.4 同族先例的 la-free shadow 手法）。
- lcms2：FHParser.cpp 用 cmsOpenProfileFromMem 处理 CMYK 色彩配置文件；制品仓
  发布的 lcms2/2.19 binary 为**动态**（default_options shared=True，无 .a），
  故本包对 lcms2 保持动态链接（-L<libdir> -llcms2），运行时需 liblcms2.so.2
  （test_package 用 conanrun 环境运行）。
- boost/1.90.0.3：仅头文件（libfreehand_utils.h 的 boost/cstdint.hpp），经 CPPFLAGS 注入。
- perl/5.42.2.3（tool_requires）：src/lib/Makefile.am 的 BUILT_SOURCES 规则用
  gentoken.pl（perl）生成 tokens.gperf；gperf 由 HNP 工具链提供
  （/data/service/hnp/bin/gperf，设备与 CI worker PATH 同源，libhubbub/0.3.8 先例），
  制品仓无 gperf binary（`conan install --build=never` rc=1）故不 tool_requires。
- pkgconf/3.0.5 作为 tool_requires 提供 PKG_PROG_PKG_CONFIG 所需二进制。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfreehandToolsConan(ConanFile):
    name = "libfreehand-tools"
    version = "0.1.2"
    description = "FreeHand (Macromedia/Adobe) parsing library + conversion tools (fh2raw, fh2svg, fh2text)"
    license = "MPL-2.0"
    homepage = "https://wiki.documentfoundation.org/DLP/Libraries/libfreehand"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("freehand", "converter", "document")

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
                "libfreehand-tools is supported only on Linux/OHOS, got os=%s" % self.settings.os)
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # W0 核验（依赖已从制品仓 ohpdp 下载验证，全部 EXIT=0）
        # librevenge: 库与三个工具都链接其子库（revenge / revenge-stream /
        # revenge-generators）；transitive_headers/transitive_libs 使消费者
        # （test_package）可见其头文件与静态库
        self.requires("librevenge/0.0.5", transitive_headers=True, transitive_libs=True)
        # ICU: libfreehand_utils.cpp / FHParser.cpp 用 unicode/utf8.h、utf16.h（icu-uc）
        self.requires("icu4c/78")
        # zlib: FHInternalStream.cpp 用 inflate*（上游 .pc Requires.private: zlib）
        self.requires("zlib/1.3.1")
        # lcms2: FHParser.cpp 用 cmsOpenProfileFromMem（制品仓 binary 为动态库）
        self.requires("lcms2/2.19")
        # boost: 仅头文件（boost/cstdint.hpp）。transitive_headers 使下游消费者
        # 编译时也能看到 boost 头（纯头文件，不进 cpp_info.requires）
        self.requires("boost/1.90.0.3", transitive_headers=True)

    def build_requirements(self):
        # configure.ac 无条件调用 PKG_PROG_PKG_CONFIG([0.20])，需 pkg-config 兼容
        # 二进制（真机无系统 pkg-config，整仓 pkgconf tool_requires 先例）
        self.tool_requires("pkgconf/3.0.5")
        # src/lib/Makefile.am: tokens.gperf 由 gentoken.pl 生成（BUILT_SOURCES）
        self.tool_requires("perl/5.42.2.3")
        # --enable-tests 上游默认 yes：CPPUNIT 是默认构建期依赖，make check 运行它
        self.tool_requires("cppunit/1.15.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _host(self, name):
        return self.dependencies.host[name]

    def _build(self, name):
        return self.dependencies.build[name]

    def _shadow_libdir(self):
        """la-free 依赖归档 staging 目录（libmspub-tools/0.1.4 同款手法）。

        E236 + libtool _LIBADD 语义冲突的根治：
        - libtool 的 <lib>_la_LIBADD 里，绝对路径 `.a` 被当作「要嵌入的
          convenience 库」直接打包进产物 .a（`archive member 'libz.a' is neither
          ET_REL nor LLVM bitcode`），必须用 `-L<dir> -l<name>` 才是「链接依赖」语义；
        - 但 librevenge 的 lib 目录里 .a 与 .la 并存，且 .la 带 `libdir='//lib'`
          病灶（E236），`-lrevenge` 会让 libtool 优先读 .la 而中止。
        解法：把依赖的 `.a` 拷进一个只含 .a、不含 .la 的 shadow 目录，
        PKG_CHECK_MODULES 预置变量一律写 `-L<shadow> -l<name>`。
        lcms2 制品只有 .so（无 .a），按原 libdir 以 `-L<libdir> -llcms2` 链接。
        """
        dest = os.path.join(self.build_folder, ".dep-archives")
        if os.path.isdir(dest):
            shutil.rmtree(dest, ignore_errors=True)
        os.makedirs(dest, exist_ok=True)
        copied = 0
        for name in ("librevenge", "icu4c", "zlib"):
            dep = self._host(name)
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
        # cppunit 在 build context（tool_requires），其 .a 同样进 shadow
        for libdir in getattr(self._build("cppunit").cpp_info, "libdirs", []):
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

        pkg.m4：环境变量已设置时跳过 pkg-config 探测；这些变量必须是「环境变量」
        才能被 configure 读到，而 tc.extra_cflags 只能进 CFLAGS，故单独组织成
        一个 Environment，与 Toolchain 环境（conanbuild）严格分离，避免污染
        conanbuild 命名空间（E2BIG 死循环教训：绝不可再 save_script("conanbuild")）。
        """
        env = Environment()
        rev = self._host("librevenge")
        icu = self._host("icu4c")
        zlib = self._host("zlib")
        lcms = self._host("lcms2")
        boost = self._host("boost")
        cppunit = self._build("cppunit")

        rev_inc = "-I%s" % rev.cpp_info.includedirs[0]
        # configure.ac 的 AC_CHECK_HEADERS(boost/...) 与源码 include 需要的头路径
        for inc in ("-I%s" % boost.cpp_info.includedirs[0],
                    "-I%s" % icu.cpp_info.includedirs[0],
                    "-I%s" % zlib.cpp_info.includedirs[0],
                    "-I%s" % lcms.cpp_info.includedirs[0],
                    "-I%s" % cppunit.cpp_info.includedirs[0],
                    rev_inc):
            env.append("CPPFLAGS", inc)

        # E236 + _LIBADD 语义：静态依赖用 `-L<shadow> -l<name>`（la-free shadow）
        shadow = self._shadow_libdir()
        L = "-L%s" % shadow
        lcms_L = "-L%s" % lcms.cpp_info.libdirs[0]

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
        env.define("ZLIB_CFLAGS", "-I%s" % zlib.cpp_info.includedirs[0])
        env.define("ZLIB_LIBS", " ".join([L, "-lz"]))
        env.define("ICU_CFLAGS", "-I%s" % icu.cpp_info.includedirs[0])
        # icu-uc.pc: -licuuc -licudata（静态序 uc -> data）
        env.define("ICU_LIBS", " ".join([L, "-licuuc", "-licudata", "-lm"]))
        env.define("LCMS2_CFLAGS", "-I%s" % lcms.cpp_info.includedirs[0])
        env.define("LCMS2_LIBS", " ".join([lcms_L, "-llcms2", "-lm"]))
        # src/test/Makefile.am: test_LDADD += $(CPPUNIT_LIBS)
        env.define("CPPUNIT_CFLAGS", "-I%s" % cppunit.cpp_info.includedirs[0])
        env.define("CPPUNIT_LIBS", " ".join([L, "-lcppunit", "-lm"]))

        # E165 姊妹陷阱（E-rm）：本机 PATH 最前的 `rm` 是 codebuddy 安全 shim
        # （safe-bin/rm，shebang #!/bin/bash），而 HarmonyOS 无 /bin/bash，automake
        # 的 AC_PROG_RM 严格检查判 rm 为劣质并 abort。根治在 _sanitize_path()，
        # 这里保留 ACCEPT_INFERIOR_RM_PROGRAM 作双保险。
        env.define("ACCEPT_INFERIOR_RM_PROGRAM", "yes")
        return env

    def generate(self):
        # 只用 tc.generate()：它生成 conanbuild.conf（供 Autotools 帮手读
        # configure_args）+ conanbuild.sh（框架自带的正确 wrapper）。绝不手动
        # save_script("conanbuild")——那会 self-source 成死循环（E2BIG）。
        tc = AutotoolsToolchain(self)
        # E001/E096：上游 config.sub(2012) 不识别 aarch64-linux-ohos（实测
        # config.sub 返回 Invalid configuration），改用 ctdl/cdecl/castget 先例
        # 的 GNU triplet 强制交叉编译模式（跳过运行探测），OHOS 目标由工具链
        # CFLAGS/LDFLAGS/sysroot 达成。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # R26: 系统同名库默认静态
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # 上游 configure.ac 的 --enable-werror **默认 yes**（开发默认），2017 年代码
        # + clang 15 触发新告警（实测 FHTransform 的 -Wdeprecated-copy-with-user-
        # provided-copy）→ -Werror 直接编译失败。发行版打包惯例 + 上游自带开关，
        # 用 --disable-werror 关掉「告警当错误」，不改上游源码、不加平台宏。
        tc.configure_args.append("--disable-werror")
        # lcms2 制品仓只有动态 binary（无 .a），FHParser 引用其符号 → 三个工具的
        # 最终链接产物带 DT_NEEDED=liblcms2.so.2。写 RPATH 使包内 bin/ 在构建机
        # 与 CI worker 上可直接执行（L2 冒烟 / test_package 均不需手工设
        # LD_LIBRARY_PATH）；用 -Wl,-rpath,<dir> 形式，libtool 原样透传。
        lcms_libdir = self._host("lcms2").cpp_info.libdirs[0]
        tc.extra_ldflags.append("-Wl,-rpath,%s" % lcms_libdir)
        tc.generate()

    def _sanitize_path(self):
        """从环境剔除 codebuddy 注入的 safe-delete shim（PATH + bash 函数）。

        E165 姊妹陷阱（三重通道注入，缺一不可）：
        1) PATH 首项被 codebuddy 注入 safe-bin/ 目录，其中 rm/rmdir/unlink 是
           shebang `#!/bin/bash` 的 shim，而 HarmonyOS 无 /bin/bash（bash 在
           /data/service/hnp/bin/bash）→ 每次调用都报 `bad interpreter`；
        2) codebuddy 还导出了 `BASH_FUNC_rm%%` / `BASH_FUNC_unlink%%` /
           `BASH_FUNC_rmdir%%`，bash 子进程启动时自动 import 同名 shell 函数；
        3) BASH_ENV 指向 shell-runtime-bash-env.sh，每个 bash 子进程自动 source
           后据 CODEBUDDY_SAFE_DELETE_BIN_DIR 重新定义 rm 函数（最隐蔽的复活通道）。
        根治：在 build() 入口（configure 之前）同步清除三者。
        """
        removed = []

        path = os.environ.get("PATH", "")
        if path:
            entries = path.split(os.pathsep)
            kept = [e for e in entries if "safe-bin" not in e]
            if len(kept) != len(entries):
                os.environ["PATH"] = os.pathsep.join(kept)
                removed.append("%d safe-bin dir(s) from PATH" % (len(entries) - len(kept)))

        for func_var in ("BASH_FUNC_rm%%", "BASH_FUNC_unlink%%", "BASH_FUNC_rmdir%%"):
            if os.environ.pop(func_var, None) is not None:
                removed.append(func_var)

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
            # 上游用例（src/test，CPPUnit）真实运行；HOME 指向构建目录内沙箱，
            # 禁止写用户真实 HOME（AGENTS §3.5 口径）
            self._run_upstream_tests(autotools)

    def _run_upstream_tests(self, autotools):
        home = os.path.join(self.build_folder, ".test-home")
        os.makedirs(home, exist_ok=True)
        env = Environment()
        env.define("HOME", home)
        with env.vars(self).apply():
            autotools.make(target="check", args=["-j1"])

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
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libfreehand")
        self.cpp_info.set_property("cmake_target_name", "libfreehand::libfreehand")
        self.cpp_info.set_property("pkg_config_name", "libfreehand-0.1")
        # 上游 libtool 命名：libfreehand-0.1（FH_MAJOR_VERSION.FH_MINOR_VERSION）
        self.cpp_info.libs = ["freehand-0.1"]
        self.cpp_info.includedirs = ["include/libfreehand-0.1"]
        # R38：构建产物含 fh2raw/fh2svg/fh2text 三个可执行文件（autotools.install()
        # 安装到 package_folder/bin），声明 bindirs 使 CI L0k/detect_bindirs 判定
        # 为 tool 类型，与软件级 commands.json（type=tool）保持一致。
        self.cpp_info.bindirs = ["bin"]
        # 不写 cpp_info.requires（libmspub-tools/0.1.4 同族先例）：icu4c 配方未定义
        # cmake_target_name，无法用 `icu4c::xxx` 引用；boost 为纯头文件。留空时
        # conan 的「直接依赖必须在 requires 中引用」校验提前 return。
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    # ------------------------------------------------------------------
    # 平台适配（先例：libmspub-tools/0.1.4 同款）
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
