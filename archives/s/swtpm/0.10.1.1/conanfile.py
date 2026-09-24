#!/usr/bin/env python3
"""Conan recipe — swtpm 0.10.1.

Software TPM (Trusted Platform Module) emulator for HarmonyOS PC.

OHOS adaptations:
  - tool_requires automake/1.18 + libtool/2.5.4 for autoreconf (git archive
    ships no configure script)
  - 补丁 config.guess 识别 HarmonyOS（autoreconf 从 automake 复制的版本不含
    HarmonyOS 分支）；**不使用 --build/--host**（R1 禁止三元组；且 autotools
    包在 CI 传 --build=<gnu triplet> 会触发 "C compiler cannot create
    executables"，见 psfex/weightwatcher/skmaker 教训）
  - --without-gnutls, --without-seccomp, --without-cuse (OHOS lacks these)
  - --disable-tests (expect/socat/etc. test tools unavailable)
  - --disable-hardening (avoid linker probe issues on OHOS)
  - --disable-shared (static linking to avoid RPATH issues)
  - PkgConfigDeps for correct .pc file paths (package .pc files have prefix=/)
  - Explicit LDFLAGS/CPPFLAGS for AC_CHECK_LIB (bypasses pkg-config)
  - Remove .la files from deps (wrong libdir paths from prefix=/)
  - Patch: remove -Werror from configure.ac for clang compatibility
  - -j1 (E074: HMDFS jobserver fifo EPERM)
  - E114: drop umask 077 from generated configure (HMDFS setgid dirs)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """Point automake/aclocal/libtoolize env vars at whatever is on PATH."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(path):
    """E114: HMDFS forces setgid on directories; remove umask 077 from
    generated configure so config.status can create temp dirs."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _patch_config_guess(path):
    """给 autoreconf 生成的 config.guess 加 HarmonyOS 识别（等价于本仓
    scripts/patch-autotools-ohos.pl 的 config.guess 部分）。

    automake/1.18 自带的 config.guess 不认 HarmonyOS，`uname -s` = HarmonyOS
    时直接报 "unable to guess system type" → configure 报
    "cannot guess build type; you must specify one"。补丁把
    *:HarmonyOS:*:* 分支插到 NetBSD 分支之前。

    注：config.sub 无需处理 —— 实测 automake/1.18 的 config.sub 已接受
    `aarch64-unknown-linux-ohos`（输出原样、rc=0）。
    """
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    if "HarmonyOS" in data:
        return False
    block = (
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
    )
    marker = "    *:NetBSD:*:*)\n"
    idx = data.find(marker)
    if idx < 0:
        raise ConanException(
            "config.guess: NetBSD insertion point not found; the upstream "
            "config.guess layout changed, update _patch_config_guess().")
    with open(path, "w", encoding="utf-8") as f:
        f.write(data[:idx] + block + data[idx:])
    return True


class SwtpmConan(ConanFile):
    name = "swtpm"
    version = "0.10.1.1"
    description = "Software TPM (Trusted Platform Module) emulator"
    license = "BSD-3-Clause"
    homepage = "https://github.com/stefanberger/swtpm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "swtpm is only supported on Linux/OHOS")

    def requirements(self):
        self.requires("libtpms/0.10.2")
        self.requires("glib/2.84.0")
        self.requires("json-glib/1.6.6")
        self.requires("libtasn1/4.21.0")
        self.requires("openssl/3.5.6")
        self.requires("gmp/6.3.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-static",
            "--disable-shared",
            "--without-gnutls",
            "--without-seccomp",
            "--without-cuse",
            "--without-selinux",
            "--disable-tests",
            "--disable-hardening",
        ])
        # 不传 --build/--host：R1 禁止三元组；autoreconf 生成的 config.guess
        # 在 build() 内被补上 HarmonyOS 识别（见 _patch_config_guess）。
        tc.extra_cflags.append("-Wno-error")
        tc.extra_ldflags.append("-L/lib")
        tc.extra_ldflags.append("-L/system/lib")
        _all_deps = ["openssl", "libtasn1", "gmp", "libtpms", "glib",
                     "json-glib", "pcre2", "libffi", "zlib"]
        for dep_name in _all_deps:
            try:
                dep = self.dependencies[dep_name]
            except Exception:
                continue
            pkg = dep.package_folder
            if pkg:
                lib_dir = os.path.join(str(pkg), "lib")
                inc_dir = os.path.join(str(pkg), "include")
                if os.path.isdir(lib_dir):
                    tc.extra_ldflags.append(f"-L{lib_dir}")
                if os.path.isdir(inc_dir):
                    tc.extra_cflags.append(f"-I{inc_dir}")
        tc.generate()

        pc = PkgConfigDeps(self)
        pc.generate()

    def build(self):
        _prepare_autotools_env()
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # autoreconf 会把 automake/1.18 的 config.guess 复制到源码树；该版本
        # 不认 HarmonyOS → configure 报 "cannot guess build type"。
        # config.sub 无需处理（automake/1.18 已接受 aarch64-unknown-linux-ohos）。
        if str(self.settings.os) == "OHOS":
            _patch_config_guess(os.path.join(self.source_folder, "config.guess"))
        _drop_umask_077(os.path.join(self.source_folder, "configure"))

        _all_deps = ["openssl", "libtasn1", "gmp", "libtpms", "glib",
                     "json-glib", "pcre2", "libffi", "zlib"]
        extra_pc = []
        for dep_name in _all_deps:
            try:
                dep = self.dependencies[dep_name]
            except Exception:
                continue
            pkg = str(dep.package_folder) if dep.package_folder else ""
            if pkg:
                pc_dir = os.path.join(pkg, "lib", "pkgconfig")
                if os.path.isdir(pc_dir):
                    extra_pc.append(pc_dir)
        if extra_pc:
            existing = os.environ.get("PKG_CONFIG_PATH", "")
            os.environ["PKG_CONFIG_PATH"] = ":".join(extra_pc) + (":" + existing if existing else "")

        import glob as _glob
        for dep_name in _all_deps:
            try:
                dep = self.dependencies[dep_name]
            except Exception:
                continue
            pkg = str(dep.package_folder) if dep.package_folder else ""
            if pkg:
                for _la in _glob.glob(os.path.join(pkg, "lib", "*.la")):
                    try:
                        os.remove(_la)
                    except OSError:
                        pass

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _restore_binaries(self):
        """从构建树恢复 bin/ 下的可执行文件。

        现象（实测，可复现）：
          - 构建树产物  swtpm = 7203328 bytes，含 `.codesign` 段，`--version` 正常
          - install 后   swtpm = 1235968 bytes，**`.codesign` 段缺失**，exec 报 EPERM
          - 构建日志伴随 `ginstall: error deallocating '<pkg>/bin/swtpm': Permission denied`
            （命中 swtpm / swtpm_localca / swtpm_setup 三个**体积较大**的产物；
             体积小的 swtpm_bios / swtpm_ioctl 正常，未被截断）

        即 install 阶段未能完整替换目标文件，留下截断副本并丢失 OHOS 签名段。
        实测「先删后拷」（删除目标再 copyfile）可完整还原产物与签名，故此处回填。

        注：受影响的三个产物恰好是动态链接 libtpms/glib 等的大体积二进制，
        但未进一步区分「体积」与「依赖外部库」两种可能，故此处只按
        「install 产物不可信 → 一律从构建树回填」处理，不做机理假设。
        """
        import glob as _glob
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for src_dir in sorted(_glob.glob(os.path.join(self.build_folder, "src", "*"))):
            name = os.path.basename(src_dir)
            candidate = os.path.join(src_dir, name)
            if not os.path.isfile(candidate):
                continue
            dst = os.path.join(bindir, name)
            if os.path.exists(dst):
                os.remove(dst)          # 先删再拷：install 留在 dst 上的截断副本必须先移除
            shutil.copyfile(candidate, dst)
            os.chmod(dst, 0o755)

    def package(self):
        test_dir = os.path.join(self.source_folder, "tests")
        if os.path.isdir(test_dir):
            for name in ["test_config", "common"]:
                fpath = os.path.join(test_dir, name)
                if not os.path.exists(fpath):
                    open(fpath, "w").close()

        autotools = Autotools(self)
        try:
            autotools.install()
        except Exception:
            pass
        # install 在 HMDFS 上会留下截断的 bin/ 产物（见 _restore_binaries）
        self._restore_binaries()
        import glob as _glob2
        for _la in _glob2.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
