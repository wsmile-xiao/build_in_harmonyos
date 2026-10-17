#!/usr/bin/env python3
"""Conan recipe — libgmobile 0.7.2 (Meson).

gmobile is a small library with functions useful in mobile related, glib
based projects: device tree parsing, display panel cutouts, MCC/MNC lookup.
It is a hard dependency of Phosh.

OHOS notes
----------
* ``data/gmobile.gresources.xml`` preprocesses 34 JSON files with
  ``preprocess="json-stripblanks"``.  glib's ``glib-compile-resources`` does
  *not* link libjson-glib — it spawns an external ``json-glib-format`` binary
  (looked up on ``PATH`` or in the ``JSON_GLIB_FORMAT`` environment variable)
  which it then has to be able to *load*.  On this worker that spawn is not
  recoverable from the recipe side: handing it the re-signed ELF (see below)
  still failed inside the child's own dynamic loader, because
  ``g_spawn_sync`` does not propagate the wrapper's ``LD_LIBRARY_PATH`` far
  enough for ``libjson-glib-1.0.so.0`` to resolve, and the spawning process is
  a glib-internal helper we do not control.  The recipe therefore patches the
  manifest to drop ``preprocess="json-stripblanks"``: gmobile parses these
  files with ``JsonParser`` at *runtime*, where whitespace is irrelevant, so
  the preprocessing is a pure (small) size optimisation and dropping it is
  behaviour-preserving.
* ``glib-compile-resources`` itself is a *compiled* OHOS ELF, and HMFS
  refuses to execute it straight out of the conan package cache (EPERM,
  surface by ninja as exit code 126).  The recipe stages it into the build
  folder and re-signs it — the same treatment the in-tree ``glade`` and
  ``gnumeric`` recipes give glib's build-time ELF tools — because signing
  *the cached package* is what makes it runnable.  It links the shared conan
  glib libraries, so it is exposed through a ``sh`` wrapper that injects
  ``LD_LIBRARY_PATH``; ``gio-2.0.pc`` is pointed at that *wrapper*, because
  meson's gnome module resolves the resource compiler through the pkg-config
  variable rather than through ``PATH``.
* Upstream builds ``both_libraries`` so the examples can link the shared
  flavour; the static library is produced as well.
"""
import glob
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# Number of upstream test *programs* registered in tests/meson.build:
#   tests = ['cutout', 'display-panel', 'mcc-mnc', 'svg-path', 'timeout',
#            'utils', 'device-tree']
# (upstream main and the v0.7.2 tag agree on this list; `device-tree` is only
#  excluded from *installing* its .test metadata, it is still built and run.)
UPSTREAM_TEST_PROGRAMS = 7

HNP_BIN = "/data/service/hnp/bin"
SIGN_TOOL = os.path.join(HNP_BIN, "binary-sign-tool")
OBJCOPY = os.path.join(HNP_BIN, "llvm-objcopy")


class LibgmobileConan(ConanFile):
    name = "libgmobile"
    version = "0.7.2"
    description = "Functions useful in mobile related, glib based projects (Phosh)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/World/Phosh/gmobile"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # Public headers include glib.h / gio/gio.h / json-glib headers, so
        # both dependencies are transitive for headers and libs.
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("json-glib/1.10.6", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    # ─────────────────────────── source ───────────────────────────
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ────────────────────────── generate ──────────────────────────
    def generate(self):
        PkgConfigDeps(self).generate()
        staged_tools = self._stage_glib_build_tools()
        self._augment_glib_pkg_config(staged_tools)
        toolchain = MesonToolchain(self)
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.project_options["default_library"] = "shared" if self.options.shared else "static"
        toolchain.project_options["introspection"] = False
        toolchain.project_options["vapi"] = False
        toolchain.project_options["gtk_doc"] = False
        toolchain.project_options["man"] = False
        toolchain.project_options["tests"] = True
        # examples are demo programs that upstream installs into bin/ with
        # `install: true`; the package delivers the library, not demos, and
        # shipping unvetted executables would also drag in the CLI-tool
        # declaration requirements.
        toolchain.project_options["examples"] = False
        toolchain.project_options["hwdb"] = True
        toolchain.c_link_args.extend(self._glib_libintl_link_args())
        toolchain.generate()
        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()

    # ─────────────────────────── build ────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            if not cross_building(self) and can_run(self):
                meson.test()
                self._assert_suite_not_vacuous()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.LIB", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["gmobile"]
        self.cpp_info.includedirs = ["include/gmobile"]
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
            "json-glib::json-glib-1.0",
        ]
        self.cpp_info.set_property("cmake_file_name", "gmobile")
        self.cpp_info.set_property("cmake_target_name", "gmobile::gmobile")
        self.cpp_info.set_property("pkg_config_name", "gmobile")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ────────────────────────── helpers ───────────────────────────
    def _build_environment(self):
        """PATH/LD_LIBRARY_PATH/TMPDIR for the staged glib build tools.

        ``glib-compile-resources`` is reached through the ``gio-2.0.pc``
        wrapper (see ``_stage_glib_build_tools``), which needs the dependency
        ``lib`` folders on ``LD_LIBRARY_PATH`` to load the shared conan glib.
        """
        environment = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)

        # The staged (re-signed) tools folder goes first: the package-cache
        # copies are the ones HMFS refuses to exec.
        tools_folder = self._glib_tools_folder()
        if os.path.isdir(tools_folder):
            environment.prepend_path("PATH", tools_folder)

        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
        for libdir in self._dependency_libdirs():
            environment.prepend_path("LD_LIBRARY_PATH", libdir)
        # ★ 依赖包里的 SONAME 名是**符号链接**且带旧签名，设备 dlopen 不了：
        # 物化成真文件副本并重签，见 _stage_symlinked_sonames。
        staged_sonames = self._stage_symlinked_sonames()
        if staged_sonames:
            environment.prepend_path("LD_LIBRARY_PATH", staged_sonames)
        return environment

    def _stage_symlinked_sonames(self):
        """把依赖 libdir 里的 .so 符号链接物化成真文件副本，并**重签**。

        `json-glib/1.8.0` 包内 `lib/libjson-glib-1.0.so.0` 只是指向
        `libjson-glib-1.0.so.0.1000.6` 的**符号链接**（判据：Conan 的
        `conanmanifest.txt` 对符号链接记的是**目标字符串**的 md5），
        而鸿蒙 HMDFS 对 .so 符号链接的运行期 dlopen 支持不完整 —— 于是
        meson 测试 `exit status 127`：

            Error loading shared library libjson-glib-1.0.so.0:
                (needed by .../build-release/src/libgmobile.so.0)
            Error relocating .../libgmobile.so.0: json_from_string: symbol not found

        冒号后 **strerror 为空**是「文件找得到、加载器解析不到」的特征（真找不到
        会写 `No such file or directory`）。

        ★ 只做「物化」不够，必须重签。同一批 PR 的 A/B 实测（2026-09-27）：
          - libratbag/0.18：物化 → CI FAIL；物化 **+ 重签** → CI PASS
            （09:20 FAIL、09:37 推重签、09:43 PASS）。
          - 本包与 pgroonga/4.0.8、libgsystemservice/0.3.0 只做物化，
            09:42~09:46 仍是同一条空 strerror FAIL。
        所以副本复制下来后走 `_resign_build_tool()`：丢掉随包带来的旧
        `.codesign`，再 `binary-sign-tool sign -selfSign 1` 就地重签
        （依赖包在 Conan 缓存里只读且被其它包引用，改不得；只动物化出来的副本）。
        staging 目录置于 LD_LIBRARY_PATH 最前，加载器命中的是重签后的普通文件。
        """
        staged = os.path.join(self.build_folder, "conan-staged-soname-libs")
        materialized = []
        for libdir in self._dependency_libdirs():
            for name in sorted(os.listdir(libdir)):
                if not name.endswith(".so") and ".so." not in name:
                    continue
                source = os.path.join(libdir, name)
                if not os.path.islink(source):
                    continue
                target = os.path.join(staged, name)
                if os.path.exists(target):
                    continue
                real = os.path.realpath(source)
                if not os.path.isfile(real):
                    continue
                os.makedirs(staged, exist_ok=True)
                shutil.copy2(real, target)  # copy2 跟随链接 → 真文件内容
                os.chmod(target, 0o755)
                # 丢掉旧签名后重签，否则设备仍拒绝映射（空 strerror）
                self._resign_build_tool(target)
                materialized.append(name)
        if not materialized:
            return None
        self.output.info(
            "E073: 物化并重签 %d 个符号链接 SONAME 到 %s（%s）"
            % (len(materialized), staged, ", ".join(materialized)))
        return staged

    def _find_host_tool(self, tool_name):
        for dependency in self.dependencies.host.values():
            candidate = os.path.join(dependency.package_folder, "bin", tool_name)
            if os.path.isfile(candidate):
                return candidate
        return shutil.which(tool_name)

    def _append_dependency_pkg_config_paths(self):
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        paths = [self.generators_folder]
        for dependency in self.dependencies.host.values():
            for relative in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                candidate = os.path.join(dependency.package_folder, *relative)
                if os.path.isdir(candidate):
                    paths.append(candidate)
        unique_paths = []
        for path in paths:
            normalized = path.replace("\\", "/")
            if normalized not in unique_paths:
                unique_paths.append(normalized)
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        replacement = "pkg_config_path = [" + ", ".join(
            "'{}'".format(p) for p in unique_paths) + "]"
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("pkg_config_path = "):
                lines[index] = replacement
                break
        else:
            lines.append(replacement)
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def _inject_meson_tools(self):
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            for directory in (
                bindir,
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin",
            ):
                if not ar:
                    candidate = os.path.join(directory, "llvm-ar")
                    if os.path.isfile(candidate):
                        ar = candidate
                if not ranlib:
                    candidate = os.path.join(directory, "llvm-ranlib")
                    if os.path.isfile(candidate):
                        ranlib = candidate
            pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
            if not pkg_config or not os.path.isfile(str(pkg_config)):
                pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")

            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insert = []
            if ar and "\nar =" not in content:
                insert.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                insert.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                insert.append(f"pkg-config = '{pkg_config}'")
            if insert:
                content = content.replace(
                    "[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    # Tools that consumers invoke *by name through a shell*, so a `sh` wrapper
    # can inject LD_LIBRARY_PATH before exec'ing the staged ELF.
    WRAPPED_TOOLS = ("glib-compile-resources",)

    def _stage_glib_build_tools(self):
        """Make the build-time ELF tools runnable from the build folder.

        glib ships ``glib-compile-resources`` as an OHOS ELF, but HMFS refuses
        to exec it straight out of the package cache (EPERM, which ninja
        surfaces as exit code 126).  Copying the tool into the build folder
        and re-signing it makes it executable.  It additionally has to load
        the shared conan glib libraries, so it is exposed through a ``sh``
        wrapper that injects ``LD_LIBRARY_PATH`` (same treatment as the
        in-tree ``glade`` / ``gnumeric`` recipes).

        The wrapper exports **every** dependency ``lib`` directory, not just
        glib's, so that anything the tool later spawns -- which inherits its
        environment -- can still resolve the conan libraries.
        """
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        libdirs = self._dependency_libdirs()
        staged = {}
        for tool in self.WRAPPED_TOOLS:
            source = self._find_host_tool(tool)
            if not source:
                raise ConanException(
                    f"build tool not found in any dependency bin/ dir: {tool}")
            target = os.path.join(tools_folder, tool)
            shutil.copyfile(source, target)
            os.chmod(target, 0o755)
            if self.settings.os == "OHOS":
                self._resign_build_tool(target)
            wrapper = target + ".sh"
            # The tool's own libdir goes first, then every dependency's.
            own = os.path.join(os.path.dirname(os.path.dirname(source)), "lib")
            search = [own] + [d for d in libdirs if d != own]
            quote = lambda value: "'" + str(value).replace("'", "'\\''") + "'"
            with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("#!/bin/sh\n"
                             f"export LD_LIBRARY_PATH="
                             f"{quote(os.pathsep.join(search))}"
                             ":$LD_LIBRARY_PATH\n"
                             f"exec {quote(target)} \"$@\"\n")
            os.chmod(wrapper, 0o755)
            staged[tool] = wrapper
        return staged

    def _dependency_libdirs(self):
        """Existing ``lib`` directories of every host dependency, deduplicated."""
        libdirs = []
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir) and libdir not in libdirs:
                    libdirs.append(libdir)
        return libdirs

    def _resign_build_tool(self, binary):
        """Drop the stale .codesign section and self-sign (HMFS exec rule)."""
        if not os.path.isfile(OBJCOPY) or not os.path.isfile(SIGN_TOOL):
            raise ConanException(
                f"OHOS signing tools missing: {OBJCOPY} / {SIGN_TOOL}")
        self.run(f"{shlex.quote(OBJCOPY)} --remove-section .codesign "
                 f"{shlex.quote(binary)}")
        self.run(shlex.join([SIGN_TOOL, "sign", "-inFile", binary,
                             "-outFile", binary, "-selfSign", "1"]))

    def _augment_glib_pkg_config(self, staged_tools):
        """PkgConfigDeps emits simplified .pc files: no tool variables, no -lintl.

        glib on OHOS is built together with its ``proxy-libintl`` subproject,
        so the ``libintl`` symbols live in the glib package rather than in a
        system libc; the generated .pc files have to name it explicitly or
        consumers end up with ``undefined reference to `g_libintl_*'``.
        """
        # Resolve the glib tool directory from a tool we know glib ships,
        # not from "the first dependency that happens to have a bin/ dir".
        glib_mkenums = self._find_host_tool("glib-mkenums")
        glib_bindir = os.path.dirname(glib_mkenums) if glib_mkenums else None
        if not glib_bindir:
            self.output.warning("glib-mkenums not found in any dependency bin/ dir")
        # glib-compile-resources is resolved through the staged wrapper, not
        # through glib's bin/ directly: the package-cache ELF cannot be exec'd
        # on HMFS (EPERM / exit 126).  See _stage_glib_build_tools().
        entries = {
            "glib-2.0.pc": {
                "glib_mkenums": None,
                "glib_genmarshal": None,
                "gobject_query": None,
            },
            "gobject-2.0.pc": {"glib_mkenums": None},
            # gio-2.0.pc carries the tool variables upstream glib puts there
            # (glib_compile_resources / gdbus_codegen).  Meson's gnome module
            # resolves the resource compiler via
            # find_tool('glib-compile-resources', 'gio-2.0',
            #           'glib_compile_resources')
            # which asks dependency('gio-2.0').get_variable(pkgconfig: ...)
            # *before* falling back to a bare PATH lookup, so without the
            # variable `gnome.compile_resources()` in data/meson.build aborts
            # configuration with "Could not get pkg-config variable and no
            # default provided" even though the tool is installed.
            "gio-2.0.pc": {"glib_compile_resources": "glib-compile-resources"},
        }
        for pc_name, variables in entries.items():
            pc_file = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc_file):
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            modified = False
            additions = []
            for variable, staged_name in variables.items():
                if f"{variable}=" in content:
                    continue
                if staged_name:
                    value = staged_tools[staged_name]
                elif glib_bindir:
                    value = os.path.join(glib_bindir, variable.replace("_", "-"))
                else:
                    continue
                additions.append(f"{variable}={value.replace(os.sep, '/')}")
            if additions:
                content += "\n" + "\n".join(additions) + "\n"
                modified = True
            if "-lintl" not in content:
                lines = []
                for line in content.splitlines(True):
                    if line.startswith("Libs:") and "-lintl" not in line:
                        line = line.rstrip("\n") + " -lintl\n"
                    lines.append(line)
                content = "".join(lines)
                modified = True
            if modified:
                with open(pc_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _glib_libintl_link_args(self):
        if self.settings.os != "OHOS":
            return []
        for dependency in self.dependencies.host.values():
            for library_name in ("libintl.so", "libintl.a"):
                library_path = os.path.join(dependency.package_folder, "lib", library_name)
                if os.path.isfile(library_path):
                    return [library_path.replace("\\", "/")]
        return []

    def _assert_suite_not_vacuous(self):
        """Read back the meson suite summary instead of trusting the exit code.

        A green ``meson test`` only means "nothing failed": tests that were
        skipped, or tests that were never registered, exit 0 as well.  The
        summary block is asserted explicitly so a silently shrinking suite is
        a hard error rather than a green build.
        """
        log = os.path.join(self.build_folder, "meson-logs", "testlog.txt")
        if not os.path.isfile(log):
            raise ConanException(f"meson test log missing: {log}")
        with open(log, encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        summary = {}
        for key in ("Ok", "Expected Fail", "Fail", "Unexpected Pass", "Skipped", "Timeout"):
            match = re.search(rf"^{re.escape(key)}:\s+(\d+)\s*$", content, re.MULTILINE)
            if match:
                summary[key] = int(match.group(1))
        self.output.info(f"upstream meson suite summary: {summary}")
        for key in ("Fail", "Timeout", "Unexpected Pass"):
            if summary.get(key, 0):
                raise ConanException(
                    f"upstream meson suite reports {key}={summary[key]}:\n"
                    + "\n".join(content.splitlines()[-40:])
                )
        if summary.get("Ok", 0) < UPSTREAM_TEST_PROGRAMS:
            raise ConanException(
                f"upstream meson suite ran only {summary.get('Ok', 0)} of "
                f"{UPSTREAM_TEST_PROGRAMS} test programs — suite is vacuous or "
                f"silently truncated:\n" + "\n".join(content.splitlines()[-40:])
            )

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_installed_elfs(self):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                path = os.path.join(bindir, name)
                if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path):
                    targets.append(path)
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')
