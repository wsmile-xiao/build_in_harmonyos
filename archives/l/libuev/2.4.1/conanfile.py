#!/usr/bin/env python3
"""Conan recipe — libuev 2.4.1 (Autotools).

libuEv is a micro event loop library (epoll + timerfd + signalfd) for Linux
and other POSIX systems.  This recipe builds it for HarmonyOS PC (aarch64).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibuevConan(ConanFile):
    name = "libuev"
    version = "2.4.1"
    description = "Micro event loop library for HarmonyOS PC (epoll/timerfd/signalfd)."
    license = "MIT"
    homepage = "https://github.com/troglobit/libuev"
    url = "https://github.com/troglobit/libuev"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # The GitHub archive ships no generated `configure` (only
        # configure.ac/Makefile.am/autogen.sh), so build() must run
        # `autoreconf -fi` to bootstrap.  The CI sandbox / minimal OHOS
        # image lacks automake/aclocal/libtoolize (only the autoconf suite
        # is present), so pull them in as tool_requires (same approach as
        # abiword-plugin-clarisworks).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS",
        # kernel "HongMeng Kernel") and its compiler probe also fails, so
        # pass the triplet explicitly (config.sub supports *-linux-ohos);
        # same approach as abiword-plugin-clarisworks / argp-standalone.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Bootstrap the autotools build system: the GitHub tag archive
        # ships no `configure`, only configure.ac/Makefile.am.
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114/E110/E112（同 libgsf/abiword/ssdeep 配方）：远端 CI 构建目录
        # （conan cache p/b/... 类路径）上，autoconf config.status 用
        # `umask 077 && mktemp -d "./confXXXXXX"` 建 0700 私有临时目录并向其中
        # 写 subs1.awk 被拒（EACCES → "could not setup config files
        # machinery"，libuev-2.4.1-r02 远端 CI PR #12056 首错一致）。修法：
        # 配方主进程预建可写目录、设置 TMPDIR/TMP/TEMP，并把 autoreconf
        # 生成的 configure 内嵌 config.status 模板的 ac_tmp 改指该目录
        # （同时把 trap 的删除动作改为仅透传退出码，避免预建目录被 rm -fr，
        # 影响后续轮次）。
        if self.settings.os == "OHOS":
            import tempfile as _tempfile
            fixed_tmp = os.path.join(_tempfile.gettempdir(), "libuev-ac-tmp")
            os.makedirs(fixed_tmp, exist_ok=True)
            os.environ["TMPDIR"] = fixed_tmp
            os.environ["TMP"] = fixed_tmp
            os.environ["TEMP"] = fixed_tmp
            _cfg_path = os.path.join(self.source_folder, "configure")
            if os.path.exists(_cfg_path):
                with open(_cfg_path, "r", encoding="utf-8",
                          errors="surrogateescape") as _f:
                    _cfg = _f.read()
                if "ac_tmp=$tmp" in _cfg:
                    _cfg = _cfg.replace("ac_tmp=$tmp",
                                        "ac_tmp={}".format(fixed_tmp))
                    _old_trap = '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status'
                    _new_trap = 'exit $exit_status'
                    if _old_trap in _cfg:
                        _cfg = _cfg.replace(_old_trap, _new_trap)
                    with open(_cfg_path, "w", encoding="utf-8",
                              errors="surrogateescape") as _f:
                        _f.write(_cfg)
                    os.chmod(_cfg_path, 0o755)
                    self.output.info(
                        "  [ok] Patched configure: ac_tmp -> {} + TMPDIR (E114)".format(fixed_tmp))
                else:
                    self.output.warning(
                        "  [warn] ac_tmp=$tmp pattern not found in configure; "
                        "skip ac_tmp patch, TMPDIR still set")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["uev"]
