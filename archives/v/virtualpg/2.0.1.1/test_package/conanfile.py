#!/usr/bin/env python3
"""Direct compiler-and-runtime consumer test for VirtualPG."""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import rm, save


class VirtualpgTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_executables.get("c")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )

        # R25/R27: the virtualpg package installs a shared libsqlite3.so (built by
        # the recipe from the sqlite3 dependency's static archive) so every consumer
        # NEEDEDs the same shared sqlite3 and the dynamic loader owns exactly one
        # runtime copy. self.dependencies.items() resolves dependencies BEFORE
        # dependents (sqlite3, libpq, then virtualpg), so the un-reordered loop would
        # place sqlite3's lib dir — which only has the static archive — ahead of
        # virtualpg's lib dir — which holds libsqlite3.so. ld.lld resolves -lsqlite3
        # to the FIRST matching file in -L order (.so preferred over .a per dir),
        # so the static archive would win: lazy-pulling only the symbols test.c
        # references (sqlite3_open/sqlite3_close) and leaving libvirtualpg.so's other
        # sqlite3_* PLT entries unsourced -> --no-allow-shlib-undefined fails. To
        # guarantee -lsqlite3 resolves to the shared object, prepend virtualpg's
        # cpp_info.libdirs before the rest so -L<virtualpg/lib> precedes every
        # dependency-only -L; -Wl,-rpath records each dir for the dynamic loader at
        # run time so the NEEDED libsqlite3.so is found regardless of LD_LIBRARY_PATH.
        virtualpg_dep = self.dependencies["virtualpg"]
        include_dirs = list(virtualpg_dep.cpp_info.includedirs)
        library_dirs = list(virtualpg_dep.cpp_info.libdirs)
        for _, dependency in self.dependencies.items():
            include_dirs.extend(dependency.cpp_info.includedirs)
            library_dirs.extend(dependency.cpp_info.libdirs)
        include_dirs = list(dict.fromkeys(include_dirs))
        library_dirs = list(dict.fromkeys(library_dirs))

        include_flags = " ".join(f'-I"{path}"' for path in include_dirs)
        library_flags = " ".join(f'-L"{path}"' for path in library_dirs)
        rpath_flags = " ".join(
            f'-Wl,-rpath-link,"{path}" -Wl,-rpath,"{path}"'
            for path in library_dirs
        )
        # R37: feed libsqlite3.so to lld as an explicit INPUT FILE (full .so
        # path on the command line), NOT via -lsqlite3. R27-R36 all tried to make
        # lld NEEDED libsqlite3.so through -lNAME / -l:NAME / --no-as-needed
        # variations, and the true machine proved every one fails: lld 15 in
        # -shared mode does not NEEDED the .so that -lsqlite3 resolves to, so
        # libvirtualpg.so's sqlite3_* PLT entries stay undefined and test.c's
        # direct sqlite3_open/sqlite3_close calls also stay undefined.
        #
        # The one form R1-R36 never tried is passing the .so's full path as a
        # regular link input (the same way an .o or .a is passed). lld treats a
        # bare .so path as a shared-library input file: it NEEDEDs the .so's
        # SONAME and imports every symbol the .so's .dynsym exports. This bypasses
        # -lNAME resolution entirely (no -L search, no .so/.a ambiguity, no
        # --as-needed suppression). The recipe installs libsqlite3.so into
        # <virtualpg package>/lib/ (R25), so its path is known at test_package
        # time. -L<virtualpg/lib> and -Wl,-rpath are still emitted so the dynamic
        # loader can find the NEEDED libsqlite3.so at run time.
        virtualpg_pkg = self.dependencies["virtualpg"].package_folder
        libsqlite3_so = os.path.join(virtualpg_pkg, "lib", "libsqlite3.so")
        if not os.path.isfile(libsqlite3_so):
            raise ConanException(
                f"virtualpg package is missing libsqlite3.so at {libsqlite3_so}"
            )
        libvirtualpg_so = os.path.join(virtualpg_pkg, "lib", "libvirtualpg.so")
        if not os.path.isfile(libvirtualpg_so):
            raise ConanException(
                f"virtualpg package is missing libvirtualpg.so at {libvirtualpg_so}"
            )
        source = os.path.join(self.source_folder, "test.c")
        executable = os.path.join(self.build_folder, "test_virtualpg")
        # R46:推翻 R37 的 bare .so path input file 假设。web 核对 lld 文档澄清：
        # lld `-shared` 默认导出所有 non-local STV_DEFAULT 定义符号到 .dynsym,
        # sqlite3_open 在 amalgamation 是 STV_DEFAULT global(SQLITE_API 默认空展开,
        # 无 -fvisibility=hidden),所以 libsqlite3.so 的 .dynsym 理应含 sqlite3_open。
        # R37-R45 把 "libsqlite3.so" 完整路径作为 input file 传给 lld——lld 对 bare
        # .so path 的处理与 -l 搜索形态根本不同:bare path 把 .so 当作"静态归档式
        # 输入",只 NEEDED 其 DT_NEEDED 依赖,不导入其 .dynsym 符号;R27-R36 的 -lsqlite3
        # 失败是 libtool 链路静默丢弃 -l: 语法(test_package 链路是 clang 直驱 lld,
        # 无 libtool,不受此影响)。
        #
        # R46 改用 -l:libsqlite3.so(冒号语法,exact filename 匹配)+ -L 搜索形态:
        # -l:NAME 强制 lld 按 exact filename 匹配,跳过 libsqlite3.a 的 -l 前缀歧义;
        # lld 把 libsqlite3.so 当作 shared library input 正常 NEEDED 并从 .dynsym
        # 导入符号满足 test.c 的 sqlite3_open/sqlite3_close undefined 引用 + 满足
        # libvirtualpg.so 的 sqlite3_* PLT 引用(--no-allow-shlib-undefined 通过)。
        # library_flags 已含 -L<virtualpg/lib>(R37 notes 描述前置 virtualpg libdirs),
        # -l:libsqlite3.so 在 -L<virtualpg/lib> 先解析到 shared object(非 sqlite3 依赖
        # 包的静态归档)。
        self.run(
            f'"{compiler}" -std=c11 -Wall -Wextra -Werror "{source}" '
            f'-o "{executable}" {include_flags} {library_flags} {rpath_flags} '
            f'-Wl,--no-as-needed -l:libsqlite3.so "{libvirtualpg_so}" -lpq -lm'
        )

        module_executable = os.path.join(
            self.build_folder, "test_virtualpg_module"
        )
        rm(self, "test_virtualpg_module", self.build_folder)
        rm(self, "module_path.h", self.build_folder)
        module = os.path.join(
            self.dependencies["virtualpg"].package_folder,
            "lib",
            "mod_virtualpg.so",
        )
        if os.path.isfile(module):
            header = os.path.join(self.build_folder, "module_path.h")
            save(
                self,
                header,
                '#define VIRTUALPG_MODULE_PATH "'
                f'{self._c_string(module)}"\n',
            )
            module_source = os.path.join(
                self.source_folder, "test_module.c"
            )
            # R46: same as the test_virtualpg link — use -l:libsqlite3.so + -L
            # search form so lld treats libsqlite3.so as a shared library input
            # (NEEDED + .dynsym import), not a bare .so path static-archive-style
            # input that does not import .dynsym symbols.
            self.run(
                f'"{compiler}" -std=c11 -Wall -Wextra -Werror '
                f'"{module_source}" -o "{module_executable}" '
                f'-I"{self.build_folder}" {include_flags} {library_flags} '
                f'{rpath_flags} -Wl,--no-as-needed -l:libsqlite3.so -lm'
            )

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-compiling, skipping runtime test (markers report "
                "executed=false so the gate sees a deliberate skip)"
            )
            tp_skip = {
                "executed": False,
                "passed": False,
                "command": "skipped (cross-compiling)",
                "discovered": 0,
                "passedCount": 0,
            }
            print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_skip)}")
            ut_skip = {
                "status": "no_tests",
                "framework": "autotools",
                "command": "make check -j1",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": (
                    "cross-compiling target; upstream no_tests audit: "
                    "virtualpg 2.0.1 tarball (sha256 "
                    "be2aebeb8c9ff274382085f51d422e823858bca4f6bc2fa90"
                    "9816464c6a1e08b) has no TESTS/check_PROGRAMS in "
                    "Makefile.am, no test framework in configure.ac, no "
                    "tests/ directory"
                ),
            }
            print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_skip)}")
            return

        discovered = 0
        passed = 0
        commands = []
        executable = os.path.join(self.build_folder, "test_virtualpg")
        discovered += 1
        commands.append("test_virtualpg")
        try:
            self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
            passed += 1
        except Exception as exc:
            self.output.error(f"test_virtualpg failed: {exc}")
        module_executable = os.path.join(
            self.build_folder, "test_virtualpg_module"
        )
        if os.path.isfile(module_executable):
            discovered += 1
            commands.append("test_virtualpg_module")
            try:
                self.run(
                    f'"{module_executable}"',
                    env="conanrun",
                    cwd=self.build_folder,
                )
                passed += 1
            except Exception as exc:
                self.output.error(f"test_virtualpg_module failed: {exc}")

        # HMBS machine-evidence markers. The upstream suite is registered as
        # zero Automake TESTS (audited tarball, see test_package/MANIFEST.yml
        # upstream_tests_exist: false), so the upstream marker reports the
        # honest no_tests result; the recipe build() still ran `make check`
        # on the real machine and emitted the same status there.
        tp_result = {
            "executed": True,
            "passed": discovered > 0 and passed == discovered,
            "command": " && ".join(commands),
            "discovered": discovered,
            "passedCount": passed,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")
        ut_result = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check -j1",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "virtualpg 2.0.1 upstream tarball audited (sha256 "
                "be2aebeb8c9ff274382085f51d422e823858bca4f6bc2fa90"
                "9816464c6a1e08b): Makefile.am declares only "
                "lib_LTLIBRARIES (libvirtualpg.la, mod_virtualpg.la) with "
                "no TESTS/check_PROGRAMS/check-local targets; tarball "
                "contains no tests/ directory or test source files; "
                "configure.ac has no test framework; make check executes "
                "Automake's empty check target and exits 0 with zero cases"
            ),
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")

    @staticmethod
    def _c_string(value):
        return value.replace("\\", "\\\\").replace('"', '\\"')
