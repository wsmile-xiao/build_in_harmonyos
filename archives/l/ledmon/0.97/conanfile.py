#!/usr/bin/env python3
"""Conan recipe — ledmon 0.97 (Intel Enclosure LED Utilities), Autotools, OHOS.

ledmon/ledctl：机柜盘位 LED 守护进程 + CLI（root 特权 + SES/SGPIO 硬件数据面）。
依赖 eudev(libudev)、libsgutils(sgutils2)、pciutils(libpci)，全部静态链接进二进制。

OHOS 适配要点（详见 patches/ 与 notes.md）：
- GitHub tag tarball 无 configure/Makefile.in → autoreconf -fi 自举
  （CI worker 缺 automake/aclocal 且拒 exec shebang 脚本 → 生成 ELF perl
  launcher 转译，avahi/0.9_rc5 已合入方案；pkgconf 供 pkg-config + pkg.m4）。
- src/ses.h `#include <asm/types.h>`：OHOS sysroot 无该头（aarch64 上其内容
  由 linux/types.h 承载）→ 0001 补丁换 include。
- doc/ 子目录用 pod2man 生成 man 页，CI worker 无 perl/Pod::Man 保证
  → 0002 补丁从 SUBDIRS 去掉 doc（man 页为文档产物，不影响功能）。
- 上游 AM_CFLAGS 写 `-I../config`（只在 in-source 构建成立）→ 0003 改
  `-I$(top_srcdir)/config`，否则 VPATH 构建下所有 .c 报 config.h not found。
- configure 用 `PKG_CHECK_MODULES([LIBPCI],[libpci])`，而 conan pciutils 包
  无 pkg_config_name，PkgConfigDeps 生成的是 pciutils.pc → generate() 里
  按内容别名出 libpci.pc。
- systemd 服务单元：OHOS 无 systemd，上游默认即关闭（不传 --enable-systemd）。
- sbin_PROGRAMS 安装到 package/sbin → package() 移入 bin/（R38 工具类，
  commands.json 随包）。
- OHOS XPM：产出的 ELF 可执行文件必须自签后才能 exec → package() 内
  二进制逐个 binary-sign-tool 自签（先剥 .codesign 占位段）。
"""
import glob
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LedmonConan(ConanFile):
    name = "ledmon"
    version = "0.97"
    description = ("Intel(R) Enclosure LED Utilities: ledmon service daemon "
                   "and ledctl command line tool for SES/SGPIO/raid drive LEDs")
    license = "GPL-2.0-or-later"
    author = "Intel Corporation"
    homepage = "https://github.com/intel/ledmon"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # tag tarball 无 configure/Makefile.in → autoreconf -fi 自举。
        # CI worker 的 hnp SDK 提供 autoconf/m4/perl，但没有 automake/aclocal；
        # 且 worker 拒绝直接 exec shebang 脚本（清单条 8），故 tool_requires
        # automake 后用本机 C 编译器生成 ELF launcher 转译 perl 调用
        # （已合入 avahi/0.9_rc5 同方案）。pkgconf 提供 pkg-config 与 pkg.m4
        # （上游 configure.ac 用 PKG_CHECK_MODULES，缺 pkg.m4 宏不展开）。
        self.tool_requires("automake/1.18")
        self.tool_requires("pkgconf/3.0.5")

    def requirements(self):
        self.requires("eudev/3.2.14")      # PKG_CHECK_MODULES libudev
        self.requires("libsgutils/1.46")   # AC_CHECK_LIB sgutils2 + scsi/sg_*.h
        self.requires("pciutils/3.13.0")   # PKG_CHECK_MODULES libpci

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ledmon requires the Linux SCSI generic (sg) / sysfs subsystem")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        # ledmon 探测的模块名是 libpci，而 pciutils 包未设 pkg_config_name，
        # PkgConfigDeps 落盘的是 pciutils.pc → 同内容别名一份 libpci.pc。
        gen = self.generators_folder
        src_pc = os.path.join(gen, "pciutils.pc")
        dst_pc = os.path.join(gen, "libpci.pc")
        if os.path.isfile(src_pc) and not os.path.isfile(dst_pc):
            content = load(self, src_pc).replace("Name: pciutils", "Name: libpci")
            save(self, dst_pc, content)
        tc = AutotoolsToolchain(self)
        # config.guess 不认识 HarmonyOS（E007 家族）→ 显式三元组跳过探测；
        # build 用 gnu、host 用 ohos（两侧同写 ohos 会被 configure 误判，清单条 4）。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # configure.ac:10 的 AX_CHECK_PROG([gcc]) 只查 PATH 上有没有名为 gcc 的
        # 可执行文件，实际编译一律用 $(CC)（=OHOS clang）。交叉工具链不提供 gcc
        # 这个名字，故预置其 cache 变量跳过探测（与仓内 ac_cv_* 预置同族做法）。
        # 同文件 :11 的 AX_CHECK_PROG([make]) 有意不预置：make 缺席时本包连编译都到不了，
        # 预置只会把失败推迟到更难定位的地方（详见 notes.md「工具链与探测」第 5 条）。
        tc.configure_args.append("ac_cv_prog_PROG_gcc=yes")
        # configure.ac 的 AC_FUNC_MALLOC 在交叉编译下跑不了运行期探测，会把 malloc
        # 改写成 gnulib 的 rpl_malloc（替换件不在本工程源码内）=> 链接期 undefined
        # symbol。malloc(0) 返回非 NULL 本就是 musl 语义，预置 cache 变量跳过替换。
        tc.configure_args.append("ac_cv_func_malloc_0_nonnull=yes")
        tc.generate()

        env = Environment()
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}) or {}
        cc = compilers.get("c")
        if not cc:
            raise ConanException("C compiler missing from "
                                 "tools.build:compiler_executables")
        env.define("CC", cc)
        tools_dir = self._stage_automake_tools()
        env.prepend_path("PATH", tools_dir)
        env.define("ACLOCAL", os.path.join(tools_dir, "aclocal"))
        env.define("AUTOMAKE", os.path.join(tools_dir, "automake"))
        # aclocal 的宏搜索路径：automake 自带 share/aclocal，pkgconf 提供 pkg.m4
        for name in ("automake", "pkgconf"):
            pkg = self.dependencies.build[name].package_folder
            acdir = os.path.join(pkg, "share", "aclocal")
            if not os.path.isdir(acdir):
                raise ConanException(f"{name} package lacks share/aclocal: {acdir}")
            env.prepend_path("ACLOCAL_PATH", acdir)
        # pkgconf 包只落 `pkgconf` 可执行名，而 configure 找的是 `pkg-config`
        # → 按 PKG_CONFIG 变量钉绝对路径（pkg.m4 显式支持该覆盖）。
        pkgconf_bin = os.path.join(
            self.dependencies.build["pkgconf"].package_folder, "bin")
        for cand in ("pkg-config", "pkgconf"):
            if os.path.isfile(os.path.join(pkgconf_bin, cand)):
                env.define("PKG_CONFIG", os.path.join(pkgconf_bin, cand))
                break
        else:
            raise ConanException(f"pkgconf package has no pkg-config in {pkgconf_bin}")
        # AC_CHECK_LIB([rt]/[sgutils2]) 走真实链接探测：AutotoolsToolchain 不把
        # 依赖的 -I/-L 注入 CFLAGS/LDFLAGS，此处按 host 依赖聚合补齐
        # （cpp_info 的路径是相对 package_folder 的，必须拼接）。
        for dep in self.dependencies.host.values():
            cpp = dep.cpp_info.aggregated_components()
            for inc in cpp.includedirs:
                flag = f"-I{inc if os.path.isabs(inc) else os.path.join(dep.package_folder, inc)}"
                env.append("CFLAGS", flag)
                env.append("CPPFLAGS", flag)
            for lib in cpp.libdirs:
                flag = f"-L{lib if os.path.isabs(lib) else os.path.join(dep.package_folder, lib)}"
                env.append("LDFLAGS", flag)
        env.vars(self).save_script("ledmon_env")

    def _stage_automake_tools(self):
        """为 automake 工具包的 perl 脚本生成 ELF launcher（CI 拒绝 shebang exec）。"""
        package = self.dependencies.build["automake"].package_folder
        tools_dir = os.path.join(self.build_folder, ".automake-tools")
        os.makedirs(tools_dir, exist_ok=True)
        for name, real_name, arguments in (
            ("aclocal", ".aclocal-real", (
                f"--automake-acdir={os.path.join(package, 'share', 'aclocal-1.18')}",
                f"--system-acdir={os.path.join(package, 'share', 'aclocal')}",
            )),
            ("automake", ".automake-real", (
                f"--libdir={os.path.join(package, 'share', 'automake-1.18')}",
            )),
        ):
            real_script = os.path.join(package, "bin", real_name)
            if not os.path.isfile(real_script):
                raise ConanException(
                    f"automake package lacks script: {real_script}")
            self._build_perl_tool_launcher(
                os.path.join(tools_dir, name), real_script, arguments)
        return tools_dir

    def _build_perl_tool_launcher(self, launcher, script, fixed_args):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}) or {}
        compiler = compilers.get("c")
        perl = "/data/service/hnp/bin/perl"
        if not os.path.isfile(perl):
            # 本机（鸿蒙 PC 交互环境）无 hnp SDK perl，回退 PATH 上的 perl；
            # CI worker 命中上面的绝对路径，行为与 avahi/0.9_rc5 完全一致。
            perl = shutil.which("perl") or perl
        source = f"{launcher}-runner.c"
        fixed = ", ".join(json.dumps(v) for v in fixed_args)
        fixed = f"{fixed}, " if fixed else ""
        with open(source, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#include <stdio.h>\n"
                "#include <stdlib.h>\n"
                "#include <unistd.h>\n"
                f"static const char *perl_path = {json.dumps(perl)};\n"
                f"static const char *script_path = {json.dumps(script)};\n"
                f"static const char *fixed_args[] = {{{fixed}NULL}};\n"
                "int main(int argc, char **argv) {\n"
                "    size_t fixed_count = (sizeof(fixed_args) / sizeof(fixed_args[0])) - 1;\n"
                "    char **args = (char **)calloc((size_t)argc + fixed_count + 2, sizeof(char *));\n"
                "    if (!args) return 126;\n"
                "    args[0] = (char *)perl_path;\n"
                "    args[1] = (char *)script_path;\n"
                "    for (size_t i = 0; i < fixed_count; ++i) args[i + 2] = (char *)fixed_args[i];\n"
                "    for (int i = 1; i < argc; ++i) args[fixed_count + i + 1] = argv[i];\n"
                "    args[fixed_count + argc + 1] = NULL;\n"
                "    execv(perl_path, args);\n"
                "    perror(\"execv\");\n"
                "    return 127;\n"
                "}\n"
            )
        self.run(f'"{compiler}" "{source}" -o "{launcher}"')
        os.chmod(launcher, 0o755)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("GitHub tag tarball 无 configure，autoreconf -fi 自举")
            autotools.autoreconf(build_script_folder=self.source_folder)
        # E011：HMDFS 下 config.status 的 umask 077 临时目录不可写；
        # 修补必须在 autoreconf 之后（自举会重新生成 configure）。
        for cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"),
                             recursive=True):
            try:
                with open(cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools.configure(build_script_folder=self.source_folder)
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # sbin_PROGRAMS → bin/（conan 工具包约定 bindirs=bin，R38 commands.json）
        pkg = self.package_folder
        sbin = os.path.join(pkg, "sbin")
        bindir = os.path.join(pkg, "bin")
        if os.path.isdir(sbin):
            os.makedirs(bindir, exist_ok=True)
            for name in os.listdir(sbin):
                shutil.move(os.path.join(sbin, name), os.path.join(bindir, name))
            shutil.rmtree(sbin)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(pkg, "licenses"), keep_path=False)
        copy(self, "COPYING.LIB", src=self.source_folder,
             dst=os.path.join(pkg, "licenses"), keep_path=False)
        for la in glob.glob(os.path.join(pkg, "lib", "**", "*.la"), recursive=True):
            os.remove(la)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_tool(self, name):
        # 老设备在 /data/service/hnp/bin（仓库 883 处先例），本机实测该目录
        # 不存在、工具在 ~/usr/local/bin（hw-win-setup 已把它加进 PATH）。
        for cand in ("/data/service/hnp/bin/" + name,
                     os.path.expanduser("~/usr/local/bin/" + name),
                     shutil.which(name) or ""):
            if cand and os.path.isfile(cand):
                return cand
        return ""

    def _sign_binaries(self):
        # OHOS XPM 要求被 exec 的 ELF 先代码签名，否则 Operation not permitted。
        # 签名是内容哈希（.codesign 段）：strip/objcopy 必须在签之前、
        # 不能事后改字节。env -u LD_LIBRARY_PATH 防 SDK llvm 库遮蔽 libc++。
        if str(self.settings.os) != "OHOS":
            return
        objcopy = self._find_tool("llvm-objcopy")
        signer = self._find_tool("binary-sign-tool")
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found; OHOS binaries cannot be exec'd unsigned")
        bindir = os.path.join(self.package_folder, "bin")
        targets = [p for p in glob.glob(os.path.join(bindir, "*"))
                   if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p)]
        for f in targets:
            if objcopy:
                # || true 是有意为之：.codesign 是 OHOS 链接期为签名预留的占位段，是否随
                # final-链接留下取决于链接器路径；段不存在时 objcopy 报错属正常路径
                # （self.run 会查退出码，故需吞掉）。真正的把关在下一步：签完后 test_package
                # 在设备上实测 exec（见 notes.md 探测点 9/10）。
                self.run('env -u LD_LIBRARY_PATH "{}" --remove-section .codesign "{}" 2>/dev/null || true'
                         .format(objcopy, f))
            self.run('env -u LD_LIBRARY_PATH "{}" sign -inFile "{}" -outFile "{}" -selfSign 1'
                     .format(signer, f, f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
