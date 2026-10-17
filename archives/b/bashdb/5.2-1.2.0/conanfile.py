#!/usr/bin/env python3
"""Conan recipe — bashdb (GNU bash debugger), pure bash scripts.

bashdb is a command-line debugger for bash scripts (~180 .sh files, no C code).
The tarball does NOT contain a pre-generated configure; it must be generated
with autogen.sh (autoreconf --install) before configure can run.

HarmonyOS adaptations:
  - configure is generated via `NOCONFIGURE=1 bash autogen.sh` and then run
    explicitly through `bash configure` (HarmonyOS refuses to exec script
    files via their shebang interpreter).
  - a `mktemp` wrapper forces autoconf's config.status to fall back to plain
    mkdir (HarmonyOS `mktemp -d` creates dirs with broken perms).
  - configure.ac version check is patched to accept bash 5.2/5.3 (the ohpcd
    bash package is 5.3).
  - /tmp is read-only on HarmonyOS: debugger tmpdir defaults to $TMPDIR.
"""
import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class BashdbConan(ConanFile):
    name = "bashdb"
    version = "5.2-1.2.0"
    description = "bashdb - GNU bash debugger (bash 5.2 compatible)"
    license = "GPL-2.0-or-later"
    homepage = "https://bashdb.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("bash/5.3")

    def build_requirements(self):
        # GitHub tag archive 不含预生成 configure，autogen.sh(autoreconf --install)
        # 需要 automake(aclocal)/libtool(libtoolize)；CI Worker 缺这些工具（E178），
        # 通过 tool_requires 用 build profile 解析（同 afuse 配方做法）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        # 集成测试 test-bug-loc 需要 pygmentize（语法高亮）。
        # 制品仓 pygments 包仅提供 Python 库（PYTHONPATH），
        # 由 generate() 创建 pygmentize wrapper 转发到 pygments.cmdline。
        self.tool_requires("pygments/2.20.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC),
        # causing config.status to fail. Create a mktemp wrapper that fails
        # so autoconf AS_TMPDIR uses its mkdir fallback.
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            "#!/bin/sh\n"
            "# HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC).\n"
            "# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n"
            "exit 1\n"
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        # Provide `pygmentize` so upstream集成测试 test-bug-loc can run.
        # The ohpcd pygments package ships only the Python library (via
        # PYTHONPATH); shim the CLI entry point so the test's
        # `pygmentize --version` probe succeeds.
        pygmentize = wrapper_dir / "pygmentize"
        pygmentize.write_text(
            "#!/bin/sh\n"
            '# HarmonyOS: pygments CLI shim (test-bug-loc requires `pygmentize`).\n'
            'exec python3 -c "from pygments.cmdline import main; import sys; sys.exit(main())" "$@"\n'
        )
        pygmentize.chmod(pygmentize.stat().st_mode | stat.S_IEXEC)

        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        # Make the pygments library importable by the pygmentize shim.
        pyg = self.dependencies.build["pygments"]
        env.prepend_path(
            "PYTHONPATH",
            str(Path(pyg.package_folder) / "lib" / "python" / "site-packages"),
        )
        env.vars(self).save_script("hmos_env")

    def build(self):
        apply_conandata_patches(self)
        env = ["conanbuild", "hmos_env"]
        # bashdb is an in-source autotools build; run everything from source_folder
        src = self.source_folder
        # The tarball has no configure: generate it via autogen.sh
        # (autoreconf --install). NOCONFIGURE=1 prevents autogen.sh from
        # running configure itself (it would exec the script via shebang,
        # which HarmonyOS refuses).
        self.run("NOCONFIGURE=1 bash autogen.sh", cwd=src, env=env)
        # Run configure explicitly via bash (bypass HarmonyOS script-exec limit).
        # --with-POSIXSHELL=bash makes bashdb resolve `bash` from the runtime
        # PATH instead of hard-coding the build-machine bash absolute path.
        self.run("bash configure --prefix={} --build=aarch64-unknown-linux-gnu --with-POSIXSHELL=bash".format(self.package_folder), cwd=src, env=env)
        # Build
        self.run("make SHELL=bash MAKEINFO=true -j1", cwd=src, env=env)
        # L1: run upstream test suite (unit + integration)
        self.run("make check SHELL=bash MAKEINFO=true LOG_COMPILER=bash", cwd=src, env=env)

    def package(self):
        env = ["conanbuild", "hmos_env"]
        self.run("make install SHELL=bash MAKEINFO=true", cwd=self.source_folder, env=env)

    def package_info(self):
        # bashdb ships only an executable (bin/bashdb); no libraries/headers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
