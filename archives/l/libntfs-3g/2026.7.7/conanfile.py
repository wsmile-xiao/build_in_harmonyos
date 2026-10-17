#!/usr/bin/env python3
"""Conan recipe — libntfs-3g 2026.7.7 (NTFS-3G Safe Read/Write Driver library).

上游: https://github.com/tuxera/ntfs-3g (tag 2026.7.7)，autotools 构建。
本配方对应主分支派生的 libntfs-3g 库 + ntfsprogs 命令行工具集。

OHOS 适配要点:
- **autogen 直跑链**：上游 tarball 不含预生成 configure，且 configure.ac
  引用 AM_PATH_LIBGCRYPT / PKG_CHECK_MODULES / LT_INIT 外部宏。三个 m4 宏
  文件（libgcrypt.m4/pkg.m4 由 recipe 导出，libtool 宏内嵌源码 m4/）通过
  ACLOCAL_PATH 注入；用 $ACLOCAL/$AUTOMAKE/$LIBTOOLIZE 环境变量直跑
  aclocal→autoconf→autoheader→automake（CI 沙箱无系统 automake，对应
  制品仓 tool_requires 注入，参考 abiword 先例）。
- **E052/E114**：HMDFS 上 autoconf 生成的 configure 使用 `umask 077 &&
  mktemp -d ./confXXXXXX` 创建临时目录，077 权限目录在 HMDFS 上创建后
  不可写（chmod 无效）→ 配置阶段建 confXXXXXX/subs1.awk 必现
  "Permission denied"。修复：移除 configure 中两处 `umask 077 &&` 前缀
  （E114 与 libgsf 同源修复），并注入 TMPDIR（libgsf 同型）。
- **ELF 签名**：鸿蒙要求共享库/可执行 ELF 有效签名才能运行，对安装产物
  统一重签名（同 libgsf/bart 模板）。
- fuse 默认 internal（内嵌 libfuse-lite，无外部依赖）；crypto（gcrypt/
  gnutls）与 uuid 为可选特性，缺失时 configure 自动降级（warn 不报错）。
"""
import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    copy,
    export_conandata_patches,
    apply_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libntfs3gConan(ConanFile):
    name = "libntfs-3g"
    version = "2026.7.7"
    description = "NTFS-3G Safe Read/Write Driver library (libntfs-3g + ntfsprogs tools)"
    license = "GPL-2.0"
    homepage = "https://github.com/tuxera/ntfs-3g"
    url = "https://github.com/tuxera/ntfs-3g"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported (Linux/OHOS only)")

    def export_sources(self):
        export_conandata_patches(self)
        # 配方自带 m4 宏（libgcrypt.m4/pkg.m4）：configure.ac 的
        # AM_PATH_LIBGCRYPT / PKG_CHECK_MODULES / PKG_PROG_PKG_CONFIG
        # 需要这些宏定义，CI 沙箱(USER=100)无系统宏（同 abiword 先例）。
        # 复制到 export_sources 后由 conan 合并进 source_folder/m4/，
        # 供 aclocal 展开。
        _src_m4 = os.path.join(self.recipe_folder, "m4")
        if os.path.isdir(_src_m4):
            import shutil as _sh
            _dst_m4 = os.path.join(self.export_sources_folder, "m4")
            if not os.path.exists(_dst_m4):
                _sh.copytree(_src_m4, _dst_m4)
                self.output.info(f"  [ok] exported m4 macros to {_dst_m4}")

    def build_requirements(self):
        # 上游 git tarball 无预生成 configure，需 autogen 自举；
        # CI 沙箱无系统 automake/libtool（hnp/bin 仅 autoconf 家族），
        # 用制品仓 tool_requires 补齐（同 abiword-plugin-eml 先例）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload tag 归档 URL 末段为 "2026.7.7"（无 .tar.gz 扩展名），get()
        # 按 URL 末段取名后 unzip 按 zip 解压 tar.gz 报 BadZipFile——
        # 显式指定 filename 保留扩展名（E017 镜像注入不改变本参数）。
        get(self, **self.conan_data["sources"], strip_root=True,
            filename=f"{self.name}-{self.version}.tar.gz")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        VirtualBuildEnv(self).generate()

    def _run_autogen(self):
        """autotools 直跑链生成 configure（绕过 autoreconf 对宏加载的依赖）。

        $ACLOCAL/$AUTOMAKE/$LIBTOOLIZE 由 tool_requires 以 buildenv
        环境变量注入（同 abiword 先例），autoconf/autoheader 在
        hnp/bin（profile buildenv PATH 已含）裸调即可。
        """
        _m4 = os.path.join(self.source_folder, "m4")
        self.output.info("Running aclocal to generate aclocal.m4...")
        self.run(
            f'ACLOCAL_PATH="{_m4}:$ACLOCAL_PATH" "${{ACLOCAL:-aclocal}}" --force',
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,
        )
        self.output.info("Running autoconf to generate configure...")
        self.run(
            "autoconf -o configure configure.ac",
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,
        )
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException("autoconf failed to generate configure")
        self.output.info("Running autoheader to generate config.h.in...")
        self.run(
            "autoheader",
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,
        )
        # P3-3 审计修复: autoheader 产物必须存在且非空（空 config.h.in 会让
        # configure 后续检测静默失效）。不静默创建空文件兜底。
        _cfg_h_in = os.path.join(self.source_folder, "config.h.in")
        if (not os.path.exists(_cfg_h_in)
                or os.path.getsize(_cfg_h_in) == 0):
            raise ConanException(
                "autoheader failed to generate config.h.in (missing or empty)")
        # ltmain.sh 必须先于 automake 存在（automake 报 missing ltmain.sh）
        _ltmain = os.path.join(self.source_folder, "ltmain.sh")
        if not os.path.exists(_ltmain):
            self.run(
                'lt="$LIBTOOLIZE"; '
                'if [ -n "$lt" ] && [ -f "$lt" ]; then '
                '  srcdir="$(cd "$(dirname "$(dirname "$lt")")" && pwd)"; '
                '  src="$srcdir/share/libtool/build-aux/ltmain.sh"; '
                '  [ -f "$src" ] && cp "$src" ltmain.sh && '
                '  echo "  [ok] Copied ltmain.sh via LIBTOOLIZE env"; '
                "fi",
                cwd=self.source_folder,
                env="conanbuild",
                ignore_errors=True,
            )
            try:
                _lt_pkg = self.dependencies["libtool"].package_folder
                if _lt_pkg:
                    _cand = os.path.join(
                        _lt_pkg, "share", "libtool", "build-aux", "ltmain.sh")
                    if os.path.exists(_cand):
                        shutil.copy(_cand, _ltmain)
                        self.output.info("  [ok] ltmain.sh from tool_requires libtool")
            except Exception:
                pass
        self.output.info("Running automake to generate Makefile.in...")
        self.run(
            '"${AUTOMAKE:-automake}" --add-missing --copy --force-missing',
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,
        )
        # P3-3 审计修复: automake 产物 Makefile.in 必须已生成
        # （libntfs-3g 顶层 Makefile.am 必须展开，否则 configure 后无
        # 法 make；missing automake 或宏缺失时该文件不会出现）。
        if not os.path.exists(os.path.join(self.source_folder, "Makefile.in")):
            raise ConanException(
                "automake failed to generate Makefile.in (missing)")

    def _patch_configure_hmdfs(self):
        """E052/E114: 移除 configure 中 `umask 077 &&` 前缀。

        HMDFS 上 077 权限临时目录创建后不可写（chmod 无效），
        config.status 写 subs1.awk 报 Permission denied。移除 umask 077
        后 mktemp 默认 755，可写（同 libgsf _patch_configure_umask）。
        """
        path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(path):
            return
        content = load(self, path)
        fixed = content.replace("umask 077 && mktemp", "mktemp")
        fixed = fixed.replace("umask 077 && mkdir", "mkdir")
        if fixed != content:
            save(self, path, fixed)
            self.output.info(
                "  [ok] patched configure: removed 'umask 077 &&' (E052/E114)")

    def _patch_config_for_ohos(self):
        """给 config.guess/config.sub 注入 HarmonyOS 识别。

        automake --add-missing 安装的 config.guess（2024-07-27 官方版）
        不认识 `uname -s = HarmonyOS`，configure 报 "unable to guess
        system type" 直接 abort；且其后的 dummy.c 编译探测还会触发
        HMDFS tmpdir 限制。此处内嵌 skill patch-autotools-ohos.pl 的
        补丁逻辑（自包含，CI 沙箱不依赖 skill 脚本路径）：
        - config.guess: 加 __OHOS__ LIBC 分支 + *:HarmonyOS:*:* 系统块
        - config.sub:   加 ohos-linux 三元组 + ohos* 到 OS 列表 +
                        linux-ohos 到内核验证列表
        """
        base = self.source_folder
        cg = os.path.join(base, "config.guess")
        cs = os.path.join(base, "config.sub")

        def _apply(path, repls):
            if not os.path.exists(path):
                self.output.warning(f"  [warn] {path} not found, skip")
                return
            content = load(self, path)
            orig = content
            for old, new in repls:
                if old in content:
                    content = content.replace(old, new, 1)
            if content != orig:
                save(self, path, content)
                self.output.info(f"  [ok] patched {os.path.basename(path)} (OHOS)")

        # config.guess: __OHOS__ LIBC 分支（紧跟 __ANDROID__ 检测后）
        _cg_repls = [
            (
                "#if defined(__ANDROID__)\n    LIBC=android",
                "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos",
            ),
            (
                "    *:NetBSD:*:*)\n",
                "    *:HarmonyOS:*:*)\n"
                "\tcase \"$UNAME_MACHINE\" in\n"
                "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                "\t    i?86)         MACHINE=i686 ;;\n"
                "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                "\tesac\n"
                "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                "\t;;\n\n"
                "    *:NetBSD:*:*)\n",
            ),
        ]
        _apply(cg, _cg_repls)

        # config.sub: 加 ohos-linux 三元组、OS 列表、内核验证列表
        _cs_repls = [
            (
                "android-linux)\n"
                "\t\tbasic_machine=$field1-unknown\n"
                "\t\tbasic_os=linux-android\n"
                "\t\t;;",
                "android-linux)\n"
                "\t\tbasic_machine=$field1-unknown\n"
                "\t\tbasic_os=linux-android\n"
                "\t\t;;\n"
                "\tohos-linux)\n"
                "\t\tbasic_machine=$field1-unknown\n"
                "\t\tbasic_os=linux-ohos\n"
                "\t\t;;",
            ),
            (
                "gnu* | android*",
                "gnu* | android* | ohos*",
            ),
            (
                "linux-uclibc*)",
                "linux-uclibc* | linux-ohos*)",
            ),
        ]
        _apply(cs, _cs_repls)
        # 验证补丁是否生效（对应 perl 脚本的 grep 校验）
        _cg_ok = os.path.exists(cg) and "HarmonyOS" in load(self, cg)
        _cs_ok = os.path.exists(cs) and "ohos-linux" in load(self, cs)
        if _cg_ok and _cs_ok:
            self.output.info("  [ok] OHOS config.guess/config.sub patch verified")
        else:
            self.output.warning(
                "  [warn] OHOS autotools patch partially failed "
                f"(cg={_cg_ok} sub={_cs_ok})")

    def build(self):
        self._run_autogen()
        apply_conandata_patches(self)
        self._patch_configure_hmdfs()
        # E490: automake --add-missing 安装的脚本可能丢失执行位
        for _script in ("configure", "config.guess", "config.sub",
                        "install-sh", "missing"):
            _p = os.path.join(self.source_folder, _script)
            if os.path.exists(_p):
                os.chmod(_p, 0o755)
        self._patch_config_for_ohos()
        # TMPDIR 注入 build 内可写目录（同 libgsf：clang 写 TMPDIR 临时
        # 文件被鸿蒙安全框架拦，且 conanbuild.sh 会覆盖 build() 注入，
        # 故统一在 build() 内用 os.environ 设置）
        _tmpdir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = _tmpdir
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 鸿蒙要求共享库/可执行 ELF 有效签名才能加载（同 libgsf/bart 模板）
        self._sign_installed_elfs()

    def _elf_type(self, path):
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError:
            return None
        if header[:4] != b"\x7fELF":
            return None
        return header[16]  # e_type: 2=EXEC, 3=DYN

    def _has_codesign_section(self, objdump, path):
        result = subprocess.run(
            [objdump, "-h", path], capture_output=True, text=True, timeout=60)
        return any(".codesign" in line.split()
                   for line in result.stdout.splitlines())

    def _sign_installed_elfs(self):
        """对安装产物中的 ELF（.so 与可执行文件）执行鸿蒙二进制签名。

        P3-4 审计修复: 工具路径从 conf（tools.build:objcopy 等）或环境
        （OHC_SIGN_TOOL_DIR）读取，不再硬编码 /data/service/hnp/bin；
        工具缺失时 warn 跳过（弱失败，跨环境可移植）。
        """
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):
                    binaries.append(candidate)
        if not binaries:
            return
        # 工具定位: conf > 环境 OHC_SIGN_TOOL_DIR > 默认 hnp/bin
        _tool_dir = os.environ.get("OHC_SIGN_TOOL_DIR", "/data/service/hnp/bin")
        try:
            _cc = self.conf.get("tools.build:compiler_executables", default={}) or {}
            _cc_path = os.path.dirname(_cc.get("c") or "") if _cc.get("c") else ""
            if _cc_path:
                _tool_dir = _cc_path
        except Exception:
            pass
        objcopy = os.path.join(_tool_dir, "llvm-objcopy")
        objdump = os.path.join(_tool_dir, "llvm-objdump")
        signer = os.path.join(_tool_dir, "binary-sign-tool")
        if not all(os.path.exists(t) for t in (objcopy, objdump, signer)):
            self.output.warning(
                "  [warn] signing tools missing, skip ELF sign "
                f"(dir={_tool_dir})")
            return
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with self._tmpsign_dir(binary) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    subprocess.run(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        check=True, capture_output=True, text=True, timeout=60)
                result = subprocess.run(
                    [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                     "-selfSign", "1"],
                    capture_output=True, text=True, timeout=60)
                if result.returncode != 0 or not os.path.isfile(signed):
                    self.output.warning(
                        f"sign {binary} failed: {result.stderr.strip()[:200]}")
                    continue
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _tmpsign_dir(self, binary):
        import tempfile
        return tempfile.TemporaryDirectory(
            prefix=".conan-sign-", dir=os.path.dirname(binary))

    def package_info(self):
        self.cpp_info.libs = ["ntfs-3g"]
        self.cpp_info.set_property("pkg_config_name", "libntfs-3g")
        self.cpp_info.bindirs = ["bin", "sbin"]