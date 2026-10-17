#!/usr/bin/env python3
"""Conan recipe - libformw 6.6_p20260516 (ncurses form library, static wide-character build).

libformw 是 ncurses 源码树 form/ 子库的打包名，不是独立上游项目：源码与已发布
的 ncurses/6.6 为同一份官方 tarball（conandata 逐字一致）。form/*.c 依赖 config.h
与 ncursesw 内部符号，必须完整 configure 后随树构建；包内只保留 form 产物，
libncursesw 本体由依赖 ncurses/6.6 提供，避免与父包双份安装。构建机制（OHOS
私有 build root、hnp bash、-j1、86 项上游测试程序核验、make check）沿用
ncurses/6.6 已验证契约。
"""

import hashlib
import os
import shlex
import shutil
from contextlib import contextmanager
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain


class LibformwConan(ConanFile):
    name = "libformw"
    version = "6.6_p20260516"
    description = "ncurses form library (wide-character) for form-based terminal user interfaces"
    license = "X11"
    homepage = "https://invisible-island.net/ncurses/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    _ohos_data_root = "/data/storage/el2/base"
    _form_headers = ("form.h", "eti.h")
    _form_pkgconfig = "formw.pc"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libformw supports Linux and OHOS, not {self.settings.os}"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "libformw is packaged statically: dependency ncurses/6.6 ships a "
                "static libncursesw only, so no usable libformw.so can be linked"
            )

    def requirements(self):
        # form.h 公开包含 <curses.h>（ncurses/6.6 的公开头）且静态 libformw.a 需要
        # libncursesw.a 一起链接：ncurses 头文件与库对下游必须可见（visible），
        # 否则 Conan 2 CMakeDeps 不为传递依赖生成 include 目录，下游编译找不到 curses.h
        self.requires("ncurses/6.6", headers=True, libs=True, visible=True)

    def layout(self):
        # ncurses supports VPATH builds, but in-source construction avoids
        # embedding HMDFS absolute paths in generated dependency rules.
        self.folders.source = "src"
        self.folders.build = "src"
        self.folders.generators = "build-generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def build(self):
        if self.settings.os == "OHOS":
            self._build_ohos()
            return

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1", "SHELL=/bin/sh"])
        self._verify_upstream_programs(Path(self.build_folder))
        autotools.make(target="check", args=["-j1", "SHELL=/bin/sh"])

    def _configure_args(self):
        args = [
            "--disable-shared",
            "--enable-static",
            "--without-shared",
            "--with-normal",
            "--without-debug",
            "--with-trace",
            "--without-ada",
            "--without-manpages",
            "--enable-widec",
            "--enable-overwrite",
            "--enable-pc-files",
        ]
        if self.settings.os == "OHOS":
            args.extend(
                ["--prefix=/", "--with-pkg-config-libdir=/lib/pkgconfig"]
            )
        return args

    def _ohos_paths(self):
        build_key = hashlib.sha256(
            os.path.abspath(self.build_folder).encode("utf-8")
        ).hexdigest()[:12]
        root = os.path.join(
            self._ohos_data_root,
            f".conan-build-libformw-{self.version}-{build_key}",
        )
        return (
            root,
            os.path.join(root, "src"),
            os.path.join(root, "stage"),
            os.path.join(root, "tmp"),
        )

    def _reset_ohos_root(self, root):
        expected_prefix = os.path.join(
            self._ohos_data_root,
            f".conan-build-libformw-{self.version}-",
        )
        if not root.startswith(expected_prefix):
            raise ConanException(f"refusing to reset unexpected build root: {root}")
        if os.path.lexists(root):
            if os.path.islink(root):
                os.unlink(root)
            else:
                shutil.rmtree(root)
        os.makedirs(root)

    def _build_ohos(self):
        root, work, stage, tmpdir = self._ohos_paths()
        shell = self._ohos_shell()
        self._reset_ohos_root(root)
        shutil.copytree(self.source_folder, work, symlinks=True)
        os.makedirs(stage)
        os.makedirs(tmpdir)

        configure = os.path.join(work, "configure")
        configure_args = " ".join(
            shlex.quote(value) for value in self._configure_args()
        )
        with self._ohos_environment(work, tmpdir, shell):
            self._verify_ohos_tools(shell)
            self.run(
                " ".join(
                    [
                        shlex.quote(shell),
                        shlex.quote(configure),
                        configure_args,
                    ]
                ),
                cwd=work,
                env=None,
            )
            self.run("make -j1 SHELL=/bin/sh", cwd=work, env=None)
            self._verify_upstream_programs(Path(work))
            self.run("make -j1 SHELL=/bin/sh check", cwd=work, env=None)
            self.run(
                f"make -j1 SHELL=/bin/sh DESTDIR={shlex.quote(stage)} install",
                cwd=work,
                env=None,
            )

    @staticmethod
    def _ohos_shell():
        for shell in (
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
            shutil.which("bash"),
        ):
            if shell and os.path.isfile(shell) and os.access(shell, os.X_OK):
                return shell
        raise ConanException("no executable OHOS configure shell is available")

    @contextmanager
    def _ohos_environment(self, work, tmpdir, shell):
        environment = Environment()
        environment.define("TMPDIR", tmpdir)
        environment.define("TMP", tmpdir)
        environment.define("TEMP", tmpdir)
        environment.define("PWD", work)
        environment.define("ac_cv_func_setfsuid", "no")
        environment.define(
            "PATH",
            os.pathsep.join(
                (
                    "/data/service/hnp/bin",
                    "/storage/Users/currentUser/usr/local/bin",
                    os.environ.get("PATH", "/system/bin:/bin:/usr/bin"),
                )
            ),
        )
        environment.compose_env(AutotoolsToolchain(self).environment())
        environment.compose_env(VirtualBuildEnv(self).environment())
        environment.define("CONFIG_SHELL", shell)

        with environment.vars(self).apply():
            yield

    def _verify_ohos_tools(self, shell):
        tools = ["sed", "rm", "expr", "make", "gawk", "clang", "clang++"]
        missing = [tool for tool in tools if shutil.which(tool) is None]
        if not os.path.isfile(shell):
            missing.append(shell)
        if missing:
            raise ConanException(
                "required OHOS build tools are missing: " + ", ".join(missing)
            )
        self.output.info(f"OHOS_BUILD_TOOLS={len(tools) + 1}/{len(tools) + 1}")

    def _verify_upstream_programs(self, build_root):
        programs_file = build_root / "test" / "programs"
        names = []
        for line in programs_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                names.append(stripped.split()[0])

        if len(names) != 86 or len(set(names)) != 86:
            raise ConanException(
                f"upstream test inventory changed: {len(names)}/86 program entries"
            )

        missing = [
            name
            for name in names
            if not (build_root / "test" / name).is_file()
        ]
        if missing:
            raise ConanException(
                "upstream test programs missing after build: " + ", ".join(missing)
            )
        self.output.info("UPSTREAM_TEST_PROGRAMS=86/86")

    def package(self):
        if self.settings.os == "OHOS":
            _root, _work, stage, _tmpdir = self._ohos_paths()
            if not os.path.isdir(stage):
                raise ConanException(f"OHOS staging directory is missing: {stage}")
            shutil.copytree(
                stage,
                self.package_folder,
                symlinks=False,
                dirs_exist_ok=True,
            )
        else:
            autotools = Autotools(self)
            autotools.install(args=["-j1", "SHELL=/bin/sh"])
            self._copy_form_pkgconfig(Path(self.build_folder) / "misc")

        self._prune_to_form_artifacts()
        self._relocate_form_pkgconfig()
        self._validate_package()

    def _copy_form_pkgconfig(self, source_dir):
        source = Path(source_dir) / self._form_pkgconfig
        if not source.is_file():
            raise ConanException(f"generated pkg-config file is missing: {source}")
        destination = Path(self.package_folder) / "lib" / "pkgconfig"
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination / self._form_pkgconfig)

    def _prune_to_form_artifacts(self):
        """只保留 form 产物：libncursesw/terminfo/其余头文件归父包 ncurses/6.6，
        防止下游同时引入两份 ncursesw 符号。"""
        keep = {
            Path("include") / self._form_headers[0],
            Path("include") / self._form_headers[1],
            Path("lib") / "libformw.a",
            Path("lib") / "pkgconfig" / self._form_pkgconfig,
        }
        package_root = Path(self.package_folder)
        for path in package_root.rglob("*"):
            if path.is_file() and path.relative_to(package_root) not in keep:
                path.unlink()
        for path in sorted(package_root.rglob("*"), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()

    @staticmethod
    def _write_lf(path, lines):
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(lines) + "\n")

    def _relocate_form_pkgconfig(self):
        pc_file = Path(self.package_folder) / "lib" / "pkgconfig" / self._form_pkgconfig
        if not pc_file.is_file():
            raise ConanException(f"pkg-config metadata is missing: {pc_file}")

        lines = pc_file.read_text(encoding="utf-8").splitlines()
        original = {}
        for line in lines:
            key, separator, value = line.partition("=")
            if separator and key in {"prefix", "exec_prefix", "libdir", "includedir"}:
                original[key] = value
        if set(original) != {"prefix", "exec_prefix", "libdir", "includedir"}:
            raise ConanException(f"unexpected pkg-config metadata in {pc_file}")

        output = []
        for line in lines:
            key, separator, _value = line.partition("=")
            if separator and key == "prefix":
                line = "prefix=${pcfiledir}/../.."
            elif separator and key == "exec_prefix":
                line = "exec_prefix=${prefix}"
            elif separator and key == "libdir":
                line = "libdir=${prefix}/lib"
            elif separator and key == "includedir":
                line = "includedir=${prefix}/include"
            elif line.startswith(("Libs:", "Libs.private:", "Cflags:")):
                field, _separator, flags = line.partition(":")
                tokens = []
                for token in shlex.split(flags):
                    if token.startswith("-L/"):
                        token = "-L${libdir}"
                    elif token.startswith("-I/"):
                        token = "-I${includedir}"
                    tokens.append(token)
                line = f"{field}: {' '.join(tokens)}"
            else:
                line = line.replace(
                    f"-I{original['includedir']}", "-I${includedir}"
                ).replace(f"-L{original['libdir']}", "-L${libdir}")
            output.append(line)
        self._write_lf(pc_file, output)

    def _validate_package(self):
        package_root = Path(self.package_folder)
        unexpected = sorted(
            path.name
            for path in package_root.iterdir()
            if path.name not in {"include", "lib"}
        )
        if unexpected:
            raise ConanException(
                "unexpected package root entries: " + ", ".join(unexpected)
            )

        shared = []
        for pattern in ("*.so", "*.so.*"):
            shared.extend(package_root.rglob(pattern))
        if shared:
            raise ConanException(
                "static-only package contains shared libraries: "
                + ", ".join(str(path) for path in shared)
            )

        required = [package_root / "include" / name for name in self._form_headers]
        required.append(package_root / "lib" / "libformw.a")
        required.append(package_root / "lib" / "pkgconfig" / self._form_pkgconfig)
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise ConanException(
                "required libformw package artifacts are missing: " + ", ".join(missing)
            )

        # ncursesw 本体与兄弟子库归各自包：出现即说明裁剪失败
        stray = [
            str(path)
            for path in (package_root / "lib").glob("*.a")
            if path.name != "libformw.a"
        ]
        stray.extend(
            str(package_root / "include" / name)
            for name in ("curses.h", "ncurses.h", "term.h", "menu.h", "panel.h")
            if (package_root / "include" / name).exists()
        )
        if stray:
            raise ConanException(
                "parent/sibling artifacts must not ship in libformw: " + ", ".join(stray)
            )

        pc_file = package_root / "lib" / "pkgconfig" / self._form_pkgconfig
        content = pc_file.read_text(encoding="utf-8")
        forbidden = (
            "//include",
            "//lib",
            os.path.abspath(self.package_folder),
        )
        leaks = [value for value in forbidden if value in content]
        if leaks:
            raise ConanException(
                f"non-relocatable paths remain in {pc_file}: {', '.join(leaks)}"
            )

    def package_info(self):
        self.cpp_info.libs = ["formw"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "formw")
        self.cpp_info.set_property("cmake_target_name", "formw::formw")
        self.cpp_info.set_property("pkg_config_name", "formw")
        # formw::formw target 必须显式挂上 ncurses 依赖：CMakeDeps 不会仅凭
        # requires 图自动传递 include/lib（否则下游/消费者 include form.h 时
        # 找不到 curses.h）；顺序 formw 在前、ncursesw 在后满足静态链接序
        self.cpp_info.requires = ["ncurses::ncurses"]
