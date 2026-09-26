from conan import ConanFile
from conan.tools.files import get, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
import os

required_conan_version = ">=2.0"


class LessConan(ConanFile):
    name = "less"
    version = "710"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "conandata.yml"

    def config_options(self):
        del self.options.fPIC

    def layout(self):
        pass

    def requirements(self):
        self.requires("ncurses/6.5")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # conan 2 AutotoolsToolchain does NOT inject dependency include/lib
        # dirs into CPPFLAGS/LDFLAGS (pullseq/1.0.2 lesson) — do it manually
        # (ncurses termcap headers are probed by configure).
        cppflags, ldflags = [], []
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if not pf:
                continue
            for d in dep.cpp_info.includedirs:
                cppflags.append("-I" + (d if os.path.isabs(d) else os.path.join(pf, d)))
            for d in dep.cpp_info.libdirs:
                ldflags.append("-L" + (d if os.path.isabs(d) else os.path.join(pf, d)))
        # E386 (§12.38): hnp bash as CONFIG_SHELL getcwd-fails on HMDFS build
        # dirs. Route shells to /bin/sh, unset CONFIG_SHELL; tc.environment()
        # is taken FIRST and passed back (tc.generate(env=X) replaces, so all
        # edits must land on that Environment object).
        env = tc.environment()
        if cppflags:
            env.define("CPPFLAGS", " ".join(cppflags))
        if ldflags:
            env.define("LDFLAGS", " ".join(ldflags))
        env.define("SHELL", "/bin/sh")
        env.unset("CONFIG_SHELL")
        tc.generate(env)

    def _patch_configure_umask(self):
        """E011: HMDFS umask 077 fix (less/661 pattern).

        config.status creates its temp dir via ``umask 077 && mktemp -d``;
        on HMDFS the resulting dir is not writable by the build process.
        configure is a generated file and cannot be a conandata patch.
        """
        cfg = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cfg):
            return
        text = load(self, cfg)
        changed = False
        if "umask 000" not in text:
            nl = text.find("\n")
            text = text[: nl + 1] + "umask 000\n" + text[nl + 1:]
            changed = True
        for old, new in (
            ('(umask 077 && mktemp -d "./confXXXXXX")',
             '(umask 000 && mktemp -d "./confXXXXXX")'),
            ('(umask 077 && mkdir "$tmp")', '(umask 000 && mkdir "$tmp")'),
        ):
            if old in text:
                text = text.replace(old, new)
                changed = True
        if changed:
            save(self, cfg, text)
            self.output.info("patched configure: umask 077->000 (E011 HMDFS)")

    def build(self):
        self._patch_configure_umask()
        autotools = Autotools(self)
        # E386 / 经验汇总 §12.38①：conan 直接 exec configure 在 HMDFS 构建目录
        # getcwd() 必挂（"working directory cannot be determined"），环境路由
        # 也不根治时用 sh 显式内联执行（pullseq/1.0.2 合入范式）。--build 显式
        # 给出跳过 config.guess 探测（§12.1，automake helper 在 OHOS 上猜不出）。
        configure_path = os.path.join(self.source_folder, "configure")
        self.run(
            f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh "{configure_path}" '
            f"--prefix=/ "
            f"--build=aarch64-unknown-linux-gnu "
            f"'--bindir=${{prefix}}/bin' "
            f"'--sbindir=${{prefix}}/bin' "
            f"'--libdir=${{prefix}}/lib' "
            f"'--includedir=${{prefix}}/include'"
        )
        autotools.make(args=["-j1"])
        # upstream test suite: lesstest (19 .lt scripted terminal cases).
        # `make check` = ${MAKE} LESSTEST=1 (builds less_t) + build
        # lesstest/lt_screen + runtest -l less_t lt.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
