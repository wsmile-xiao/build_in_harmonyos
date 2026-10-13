#!/usr/bin/env python3
"""Conan test_package — its-playback-time 0.2026-05-26.fdcd2b0.

The package ships two command-line programs, so the L1/L2 consumer test
executes the real binaries (R34) rather than linking a library API:

  ipbt        the interactive curses player — needs a real terminal, so the
              test only exercises its non-curses entry points
              (--version / --help / --licence) and its option validation
  ipbt-dump   the non-interactive converter, which runs the very same
              ipbtsrc/read.c ttyrec parser and the very same PuTTY terminal
              emulator as the player; test.sh drives it over a synthetic
              ttyrec file and over raw terminal bytes, asserting the frame
              summary, the byte-identical typescript round-trip, the hex dump
              and the emulated-screen XML

Everything runs headlessly: no curses initialisation is required by any
assertion, so no TERMINAL/terminfo setup is needed for the tests themselves
(the packaged ncurses terminfo database is still resolved and exported so the
run environment matches a real device).

Level-1 (upstream tests): ipbt ships no test suite at all — audited, see
MANIFEST.yml upstream_test_audit. The honest machine-readable result is
no_tests/0, printed both here and from the recipe's build().
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class ItsPlaybackTimeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The tested package links ncurses statically, but a curses program
        # still reads its terminal description at run time. Declaring the very
        # same ncurses the recipe requires - with run=True - is what makes
        # VirtualRunEnv export TERMINFO / TERMINFO_DIRS into the aggregated
        # conanrun environment for this consumer test, i.e. the same runtime
        # environment a real OHOS PC consumer of this application gets.
        #
        # Measured (Conan 2.29, profile ohos-aarch64-wsl): without this line the
        # test_package graph still contains ncurses/6.6, but with "run=False"
        # and package_folder=None, and the generated
        # conanrunenv-release-armv8.sh carries no TERMINFO export at all -
        # which is why the terminal-database assertion used to fail on CI.
        self.requires("ncurses/6.6", run=True)

    def build(self):
        # The package ships executables, not a library: there is nothing to
        # compile here. All assertions happen in test().
        pass

    def _resolve_terminfo(self):
        """Resolve the terminal database directory, returning (path, source).

        Lookup order (first existing directory wins):
          1. TERMINFO / TERMINFO_DIRS already present in the environment
          2. the exported values inside the generated conanrunenv*.sh
          3. share|lib|etc/terminfo inside any host dependency package folder
          4. common system locations (a real device provides its own database)
        """
        candidates = []
        for var in ("TERMINFO", "TERMINFO_DIRS"):
            value = os.environ.get(var)
            if value:
                for part in value.split(os.pathsep):
                    candidates.append((part, "env:" + var))

        # conanrunenv*.sh holds the aggregated run environment (ncurses exports
        # TERMINFO/TERMINFO_DIRS there). self.generators_folder can point at the
        # recipe folder for a test_package, so collect the real locations: the
        # generators folders that Conan creates under the build folder.
        generators_dir = self.generators_folder or ""
        scan_dirs = []
        if generators_dir and os.path.isdir(generators_dir):
            scan_dirs.append(os.path.abspath(generators_dir))
        build_folder = getattr(self, "build_folder", "") or ""
        if build_folder and os.path.isdir(build_folder):
            root_depth = os.path.abspath(build_folder).count(os.sep)
            scan_dirs.append(os.path.abspath(build_folder))
            for root, dirs, files in os.walk(build_folder):
                if root.count(os.sep) - root_depth > 4:
                    dirs[:] = []
                    continue
                if any(
                    f.startswith("conanrunenv") and f.endswith(".sh") for f in files
                ):
                    scan_dirs.append(os.path.abspath(root))
        seen_dirs = set()
        for scan_dir in scan_dirs:
            if scan_dir in seen_dirs:
                continue
            seen_dirs.add(scan_dir)
            try:
                entries = sorted(os.listdir(scan_dir))
            except OSError:
                continue
            for fname in entries:
                if not (fname.startswith("conanrunenv") and fname.endswith(".sh")):
                    continue
                try:
                    with open(os.path.join(scan_dir, fname), "r", errors="replace") as handle:
                        for line in handle:
                            line = line.strip()
                            for var in ("TERMINFO", "TERMINFO_DIRS"):
                                prefix = "export {}=".format(var)
                                if not line.startswith(prefix):
                                    continue
                                value = line[len(prefix):].strip().strip('"').strip("'")
                                for part in value.split(os.pathsep):
                                    candidates.append(
                                        (part, "runenv:{}:{}".format(fname, scan_dir))
                                    )
                except OSError:
                    pass

        host_deps = []
        for api_name in ("host", "direct_host"):
            try:
                api = getattr(self.dependencies, api_name, None)
                if api:
                    host_deps.extend(list(api.values()))
            except Exception:  # noqa: BLE001 - dependency API differences
                pass
        try:
            if not host_deps:
                host_deps = [dep for _, dep in self.dependencies.items()]
        except Exception:  # noqa: BLE001
            host_deps = []
        for dep in host_deps:
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            for sub in ("share/terminfo", "lib/terminfo", "etc/terminfo"):
                candidates.append(
                    (os.path.join(folder, sub), "dep:" + str(getattr(dep, "ref", "?")))
                )

        for sys_dir in (
            "/usr/share/terminfo",
            "/etc/terminfo",
            "/lib/terminfo",
            "/usr/lib/terminfo",
            "/data/service/hnp/share/terminfo",
        ):
            candidates.append((sys_dir, "system"))

        dep_refs = [str(getattr(dep, "ref", "?")) for dep in host_deps]
        self.output.info(
            "its-playback-time test: terminfo lookup: {} candidates, "
            "{} host deps [{}], generators_dir={}".format(
                len(candidates),
                len(dep_refs),
                ", ".join(dep_refs) or "<none>",
                "{} scan dirs".format(len(seen_dirs)),
            )
        )
        for path, source in candidates:
            if path and os.path.isdir(path):
                self.output.info(
                    "its-playback-time test: terminfo hit: {} (source={})".format(
                        path, source
                    )
                )
                return path, source
        self.output.info(
            "its-playback-time test: terminfo not found; candidates were: {}".format(
                "; ".join("{} <- {}".format(p, s) for p, s in candidates[:8])
            )
        )
        return None, "not found ({} candidates checked)".format(len(candidates))

    def test(self):
        # The test scripts run under the aggregated run environment
        # (env="conanrun"), which is where ncurses exports TERMINFO /
        # TERMINFO_DIRS for the packaged binaries.
        #
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries, so the test
        # script is run through bash. The absolute HNP path is missing on some
        # preflight workers, hence the PATH lookup before the hard-coded path.
        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )

        dep = self.dependencies["its-playback-time"]
        package_folder = dep.package_folder
        player = os.path.join(package_folder, "bin", "ipbt")
        dumper = os.path.join(package_folder, "bin", "ipbt-dump")
        for binary in (player, dumper):
            if not os.path.isfile(binary):
                raise ConanException(
                    "packaged binary not found at {}".format(binary)
                )

        # The ncurses package ships its terminfo database inside the package
        # folder (share/terminfo + lib/terminfo) and its runenv exports
        # TERMINFO/TERMINFO_DIRS. Resolve it from several sources and record
        # which one was used, because CI workers do not always source the
        # aggregated conanrun script before running the test step.
        terminfo, terminfo_source = self._resolve_terminfo()
        if terminfo:
            os.environ["TERMINFO"] = terminfo
            os.environ["TERMINFO_DIRS"] = terminfo
        self.output.info(
            "its-playback-time test: TERMINFO={} (source={})".format(
                terminfo or "<none>", terminfo_source
            )
        )

        script = os.path.join(self.source_folder, "test.sh")
        discovered = 32  # 14 集成测试 (test.sh) + 18 鸿蒙特有测试 (test_ohos_playback.sh)
        passed = 0
        try:
            self.run(
                '"{bash}" "{script}" "{player}" "{dumper}"'.format(
                    bash=bash, script=script, player=player, dumper=dumper
                ),
                env="conanrun",
            )
            passed = 14
        except Exception as exc:  # noqa: BLE001 - reported through the marker
            self.output.error("test.sh failed: {}".format(exc))

        # 鸿蒙特有测试（rule12 完整端到端消费者用例）：用安装后的 ipbt/ipbt-dump
        # 跑完整 ttyrec 转换流水线 + OHOS PC 交付契约，18 条 TAP 断言。
        ohos_script = os.path.join(self.source_folder, "test_ohos_playback.sh")
        ohos_count = 18
        try:
            self.run(
                '"{bash}" "{script}" "{pkg}" "{terminfo}"'.format(
                    bash=bash, script=ohos_script, pkg=package_folder,
                    terminfo=terminfo or "",
                ),
                env="conanrun",
            )
            passed += ohos_count
        except Exception as exc:  # noqa: BLE001 - reported through the marker
            self.output.error("test_ohos_playback.sh failed: {}".format(exc))

        print(
            "HMBS_TEST_PACKAGE_RESULT={}".format(
                json.dumps(
                    {
                        "executed": True,
                        "passed": passed == discovered,
                        "command": "{bash} test.sh".format(bash=bash),
                        "discovered": discovered,
                        "passedCount": passed,
                    }
                )
            )
        )
        print(
            "HMBS_UPSTREAM_TEST_RESULT={}".format(
                json.dumps(
                    {
                        "status": "no_tests",
                        "framework": "cmake",
                        "command": "ctest (upstream defines no test target)",
                        "discovered": 0,
                        "executed": 0,
                        "passed": 0,
                        "failed": 0,
                        "skipped": 0,
                        "reason": (
                            "ipbt-20260527.fdcd2b0.tar.gz (sha256 5303c8010add"
                            "f1b2dec5375c8cf32d70e1835545d639ee2183863e09d"
                            "4e80aa3): no tests/ directory, no test sources, "
                            "no enable_testing()/add_test() anywhere, and the "
                            "only *test* file (terminal/bidi_test.c) is "
                            "referenced by no build rule; upstream executes "
                            "zero test cases"
                        ),
                    }
                )
            )
        )

        if passed != discovered:
            raise ConanException(
                "its-playback-time test_package assertions failed: {}/{}".format(
                    passed, discovered
                )
            )