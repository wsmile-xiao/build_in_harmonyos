#!/usr/bin/env python3
"""Conan recipe - libpng1.6 1.6.58 (autotools)."""

import json
import os
import re
import shlex
import shutil
import subprocess
from io import StringIO
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class Libpng16Conan(ConanFile):
    name = "libpng1.6"
    version = "1.6.58"
    description = "PNG reference library"
    license = "libpng-2.0"
    homepage = "https://libpng.sourceforge.io/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    _test_programs = (
        "pngtest",
        "pnggetset",
        "pngunknown",
        "pngstest",
        "pngvalid",
        "pngimage",
        "pngcp",
        "timepng",
    )
    _nested_pngstest_drivers = (
        "pngstest-1.8",
        "pngstest-1.8-alpha",
        "pngstest-linear",
        "pngstest-linear-alpha",
        "pngstest-none",
        "pngstest-none-alpha",
        "pngstest-sRGB",
        "pngstest-sRGB-alpha",
    )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Use ohpcd-only suffix version to force the station Makefile recipe:
        # conancenter also hosts zlib/1.3.2 (CMake) which fails on this worker
        # (unknown CMake Platform/HarmonyOS + readonly /tmp try_compile), while
        # zlib/1.3.1.1 exists only in ohpcd (Makefile --static -fPIC, same API).
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        self._autotools_toolchain().generate()

    def build(self):
        apply_conandata_patches(self)
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._configure_with_posix_shell()
                # E182/E188: HMBS install shim (runtime/.../bin/install,
                # install_shim:true) only accepts single-file two-arg calls
                # ([ $# -eq 2 ] || exit 64); automake install-man3 does
                # `install -c -m 644 libpng.3 libpngpf.3 dir/` (multi-source)
                # -> Error 64. Redirect generated Makefiles to cp/mkdir shim
                # (adms 2.3.7 / aribb24 1.0.4 / torsocks 2.5.0 precedent).
                shim_install = self._write_install_shim()
                self._redirect_install_to_shim(shim_install)
                self._run_with_posix_shell("make -j1")
                self._prepare_ohos_test_programs()
                self._route_nested_pngstest_drivers()
                shell = shlex.quote(self._posix_shell())
                test_environment = Environment()
                if self.options.shared:
                    test_environment.prepend_path(
                        "LD_LIBRARY_PATH", os.path.join(self.build_folder, ".libs")
                    )
                with test_environment.vars(self).apply():
                    self._run_upstream_check_with_evidence(shell)
            else:
                autotools = Autotools(self)
                autotools.configure()
                autotools.make(args=["-j1"])
                self._run_upstream_check_generic(autotools)

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                # Makefiles already redirected in build(), but package() may
                # run with a fresh build folder view; re-ensure shim wiring
                # before make install so install-man3/libtool never touch the
                # single-file-only HMBS install shim.
                shim_install = self._write_install_shim()
                self._redirect_install_to_shim(shim_install)
                destination = shlex.quote(self.package_folder)
                self._run_with_posix_shell(
                    f"make -j1 install DESTDIR={destination}"
                )
            else:
                Autotools(self).install(args=["-j1"])
        self._relocate_metadata()
        if str(self.settings.os) == "OHOS":
            for name in ("pngfix", "png-fix-itxt"):
                self._sign_elf(Path(self.package_folder, "bin", name))
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["png16"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libpng")
        self.cpp_info.set_property("cmake_target_name", "libpng::libpng")
        self.cpp_info.set_property("pkg_config_name", "libpng")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    def _autotools_toolchain(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        return tc

    def _build_environment(self):
        # [readonly_tmp] HMBS真机 /tmp 只读：优先复用HMBS注入的任务独立
        # TMPDIR/TMP/TEMP（真机 capabilities.tmpdir），回退到build内.tmp；
        # 三变量同时设置，autoconf mktemp/CMake/Python统一可见。
        temporary = self._writable_tmpdir()
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        environment.define_path("TMP", str(temporary))
        environment.define_path("TEMP", str(temporary))
        mkdir = shutil.which('mkdir')
        if mkdir:
            environment.define('MKDIR_P', mkdir + ' -p')
        try:
            live_cc = self._c_compiler()
            environment.define('CC', live_cc)
        except Exception:
            pass
        try:
            live_cxx = self._cxx_compiler()
            if live_cxx:
                environment.define('CXX', live_cxx)
        except Exception:
            pass
        return environment

    def _writable_tmpdir(self):
        # [readonly_tmp] probe writability (mkdir+write+unlink); isdir alone
        # is not enough on HMDFS/CI workers. Prefer HMBS-injected dirs.
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR", "HMBS_INSTALL"):
            candidate = os.environ.get(key)
            if candidate:
                try:
                    Path(candidate).mkdir(parents=True, exist_ok=True)
                    probe = Path(candidate, ".hmbs-write-probe")
                    probe.write_text("ok", encoding="utf-8")
                    probe.unlink()
                    return Path(candidate)
                except OSError:
                    continue
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        return temporary

    def _configure_with_posix_shell(self):
        shell = self._posix_shell()
        compiler = self._c_compiler()
        triplet = subprocess.check_output(
            [compiler, "-dumpmachine"], text=True
        ).strip()
        if not triplet:
            raise ConanInvalidConfiguration("C compiler returned an empty target triplet")
        configure = Path(self.source_folder, "configure")
        temporary_configure = Path(self.build_folder, ".conan-configure")
        try:
            shutil.copy2(configure, temporary_configure)
            self._relax_private_umask(temporary_configure)
            arguments = self._autotools_toolchain().configure_args + [
                f"--build={triplet}",
                f"--srcdir={self.source_folder}",
            ]
            quoted_arguments = " ".join(
                shlex.quote(argument) for argument in arguments
            )
            self._run_with_posix_shell(
                f"{shlex.quote(shell)} {shlex.quote(str(temporary_configure))} "
                f"{quoted_arguments}"
            )
        finally:
            if temporary_configure.exists():
                temporary_configure.unlink()

    def _probe_live_program(self, candidate):
        try:
            subprocess.check_output([candidate, '--version'], stderr=subprocess.STDOUT, text=True, timeout=30)
            return True
        except Exception:
            return False

    def _live_cc_exports(self):
        parts = []
        try:
            cc = self._c_compiler()
            parts.append("CC=" + shlex.quote(cc))
            parts.append("ac_cv_prog_CC=" + shlex.quote(cc))
            parts.append("ac_cv_prog_ac_ct_CC=" + shlex.quote(cc))
        except Exception as exc:
            self.output.warning("live CC probe failed; keeping conanbuild CC: %s" % exc)
        try:
            cxx = self._cxx_compiler()
            if cxx:
                parts.append("CXX=" + shlex.quote(cxx))
                parts.append("ac_cv_prog_CXX=" + shlex.quote(cxx))
        except Exception:
            pass
        if not parts:
            return ":;"
        return "export " + " ".join(parts) + "; "

    def _run_with_posix_shell(self, command):
        shell = shlex.quote(self._posix_shell())
        prefix = f'export SHELL={shell} CONFIG_SHELL={shell}; ' + self._live_cc_exports()
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _run_upstream_check_with_evidence(self, shell):
        buf = StringIO()
        try:
            self._run_with_posix_shell_capture(
                f"make -j1 check LOG_COMPILER={shell}", buf
            )
        except Exception as exc:
            buf.write(f"\nmake check raised: {exc}\n")
        out = buf.getvalue()
        self.output.info(out)
        result = self._parse_automake_check(out, f"make -j1 check LOG_COMPILER={shell}")
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        if result["failed"] > 0 or result["executed"] == 0:
            raise ConanException(
                f"upstream tests failed: {result['passed']}/{result['discovered']} passed"
            )

    def _run_upstream_check_generic(self, autotools):
        buf = StringIO()
        try:
            autotools.make(target="check", args=["-j1"], stdout=buf, stderr=buf)
        except Exception as exc:
            buf.write(f"\nmake check raised: {exc}\n")
        out = buf.getvalue()
        self.output.info(out)
        result = self._parse_automake_check(out, "make -j1 check")
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        if result["failed"] > 0 or result["executed"] == 0:
            raise ConanException(
                f"upstream tests failed: {result['passed']}/{result['discovered']} passed"
            )

    def _run_with_posix_shell_capture(self, command, buf):
        shell = shlex.quote(self._posix_shell())
        prefix = f'export SHELL={shell} CONFIG_SHELL={shell}; ' + self._live_cc_exports()
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild",
                 stdout=buf, stderr=buf)

    @staticmethod
    def _parse_automake_check(out, command):
        def _count(label):
            m = re.search(r"^#\s+%s:\s+(\d+)" % label, out, re.M)
            return int(m.group(1)) if m else 0
        total, passed = _count("TOTAL"), _count("PASS")
        failed = _count("FAIL") + _count("XPASS") + _count("ERROR")
        skipped = _count("SKIP") + _count("XFAIL")
        if total == 0:
            passed = len(re.findall(r"^PASS:", out, re.M))
            failed = len(re.findall(r"^(?:FAIL|XPASS|ERROR):", out, re.M))
            skipped = len(re.findall(r"^(?:SKIP|XFAIL):", out, re.M))
            total = passed + failed + skipped
        executed = passed + failed
        status = "failed" if failed > 0 else ("passed" if executed > 0 else "failed")
        return {
            "status": status,
            "framework": "automake test-driver (make check)",
            "command": command,
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }

    def _write_install_shim(self):
        # E182/E188: HMBS install shim only accepts single-file two-arg calls
        # (exit 64 / EX_USAGE otherwise); automake install-man3 needs
        # multi-source `install -c -m 644 a b dir/`. Provide cp/mkdir shim
        # with best-effort chmod (HMBS_CAP_CHMOD=0). Via os.open 0o755 so no
        # chmod capability is required for exec permission.
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            pass
        install = os.path.join(shim_dir, "install")
        script = (
            "#!/bin/sh\n"
            "set -eu\n"
            "mode=\n"
            "while [ $# -gt 0 ]; do\n"
            "  case \"$1\" in\n"
            "    -p|-c) shift ;;\n"
            "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
            "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
            "    --) shift; break ;;\n"
            "    -*) shift ;;\n"
            "    *) break ;;\n"
            "  esac\n"
            "done\n"
            "[ $# -ge 2 ] || exit 2\n"
            "dest=\n"
            "for arg in \"$@\"; do dest=$arg; done\n"
            "count=$(($# - 1))\n"
            "if [ \"$count\" -gt 1 ]; then\n"
            "  mkdir -p \"$dest\"\n"
            "else\n"
            "  mkdir -p \"$(dirname \"$dest\")\"\n"
            "fi\n"
            "i=1\n"
            "for src in \"$@\"; do\n"
            "  [ $i -gt $count ] && break\n"
            "  cp -f \"$src\" \"$dest\"\n"
            "  if [ -n \"$mode\" ]; then\n"
            "    if [ -d \"$dest\" ]; then\n"
            "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
            "    else\n"
            "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
            "    fi\n"
            "  fi\n"
            "  i=$((i + 1))\n"
            "done\n"
        )
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(script)
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass  # HMBS_CAP_CHMOD=0: open mode already grants exec
        return install

    def _redirect_install_to_shim(self, shim_install):
        # configure bakes the probed install path into every generated
        # Makefile's INSTALL variable. Point it at the cp/mkdir shim so
        # `make install` (libtool + automake rules) never calls the
        # single-file-only HMBS shim. INSTALL_DATA/INSTALL_PROGRAM reference
        # ${INSTALL} and follow automatically.
        redirected = 0
        seen = set()
        for root in (self.build_folder, self.source_folder):
            if not root or not os.path.isdir(root):
                continue
            for dirpath, _, filenames in os.walk(root):
                if "Makefile" not in filenames:
                    continue
                mf = os.path.join(dirpath, "Makefile")
                try:
                    key = os.path.realpath(mf)
                except Exception:
                    key = mf
                if key in seen:
                    continue
                seen.add(key)
                try:
                    with open(mf, "r", encoding="utf-8",
                              errors="ignore") as f:
                        content = f.read()
                except OSError:
                    continue
                if "INSTALL =" not in content:
                    continue
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if (stripped.startswith("INSTALL = ")
                            and "/install" in stripped):
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL = %s\n"
                                     % (indent, shim_install))
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    try:
                        with open(mf, "w", encoding="utf-8",
                                  newline="\n") as f:
                            f.writelines(lines)
                        redirected += 1
                    except OSError:
                        continue
        self.output.info(
            "redirected INSTALL to shim in {} Makefile(s)".format(redirected))

    def _posix_shell(self):
        shell = "/system/bin/sh" if os.path.isfile("/system/bin/sh") else shutil.which("sh")
        if not shell:
            raise ConanInvalidConfiguration("No POSIX shell is available")
        return shell

    def _c_compiler(self):
        # [stale_conf_cc v2] 前次仅做存在性回退，configure 仍沿用 conanbuild
        # 中的失效 CC。本轮改用版本命令实测探活并由 _live_cc_exports 内联
        # 固定到配置与构建全程（经验1策略）。
        try:
            executables = self.conf.get('tools.build:compiler_executables', default={}, check_type=dict)
        except Exception:
            executables = {}
        conf_cc = executables.get('c') if isinstance(executables, dict) else None
        candidates = []
        if conf_cc:
            candidates.append(str(conf_cc))
            if os.path.isabs(str(conf_cc)):
                base = os.path.basename(str(conf_cc))
                which_base = shutil.which(base)
                if which_base:
                    candidates.append(which_base)
        for candidate in ('clang', 'cc', 'gcc'):
            resolved = shutil.which(candidate)
            if resolved:
                candidates.append(resolved)
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            resolved = shutil.which(candidate) or candidate
            if resolved and os.path.isfile(resolved) and self._probe_live_program(resolved):
                if candidate != resolved or candidate == str(conf_cc):
                    self.output.info('live C compiler selected: %s' % resolved)
                return resolved
        if conf_cc:
            fallback = shutil.which(os.path.basename(str(conf_cc))) if os.path.isabs(str(conf_cc)) else None
            if fallback and os.path.isfile(fallback):
                self.output.warning('configured C compiler not live; falling back to PATH: %s' % fallback)
                return fallback
        raise ConanInvalidConfiguration('No live C compiler found (tools.build:compiler_executables.c=%r unusable and no clang/cc/gcc in PATH passes --version probe)' % (conf_cc,))

    def _cxx_compiler(self):
        try:
            executables = self.conf.get('tools.build:compiler_executables', default={}, check_type=dict)
        except Exception:
            executables = {}
        conf_cxx = executables.get('cpp') or executables.get('cxx') or executables.get('c++')
        candidates = []
        if conf_cxx:
            candidates.append(str(conf_cxx))
        for candidate in ('clang++', 'c++', 'g++'):
            resolved = shutil.which(candidate)
            if resolved:
                candidates.append(resolved)
        cc = None
        try:
            cc = self._c_compiler()
        except Exception:
            cc = None
        if cc:
            base = os.path.basename(cc)
            if base.startswith('clang'):
                suffix = base[len('clang'):]
                for name in ('clang++' + suffix, 'clang++'):
                    resolved = shutil.which(name)
                    if resolved and resolved not in candidates:
                        candidates.append(resolved)
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            resolved = shutil.which(candidate) or candidate
            if resolved and os.path.isfile(resolved) and self._probe_live_program(resolved):
                return resolved
        return None

    def _prepare_ohos_test_programs(self):
        build = Path(self.build_folder)
        if self.options.shared:
            self._sign_elf(build / ".libs" / "libpng16.so.16.58.0")
        for name in self._test_programs:
            executable = build / ".libs" / name if self.options.shared else build / name
            self._sign_elf(executable)
            if self.options.shared:
                shutil.copy2(executable, build / name)

    def _route_nested_pngstest_drivers(self):
        shell = shlex.quote(self._posix_shell())
        original = 'exec "${srcdir}/tests/pngstest"'
        replacement = f'exec {shell} "${{srcdir}}/tests/pngstest"'
        for name in self._nested_pngstest_drivers:
            driver = Path(self.source_folder, "tests", name)
            if not driver.is_file():
                raise ConanInvalidConfiguration(
                    f"required upstream test driver is missing: {driver}"
                )
            content = driver.read_text(encoding="utf-8")
            if content.count(original) != 1:
                raise ConanInvalidConfiguration(
                    f"upstream test driver invocation changed: {driver}"
                )
            driver.write_text(
                content.replace(original, replacement, 1), encoding="utf-8"
            )

    def _sign_elf(self, executable):
        executable = Path(executable)
        if not executable.is_file():
            raise ConanInvalidConfiguration(
                f"required OHOS test ELF is missing: {executable}"
            )
        objcopy = self._resolve_tool("objcopy")
        readelf = self._resolve_tool("readelf")
        signer = self._resolve_tool("binary-sign-tool", llvm=False)
        temporary = executable.with_name(
            f"{executable.name}.signing-{os.getpid()}"
        )
        try:
            shutil.copy2(executable, temporary)
            sections = subprocess.run(
                [readelf, "-S", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if ".codesign" in sections:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", str(temporary)],
                    check=True,
                )
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    str(temporary),
                    "-outFile",
                    str(temporary),
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            signed_sections = subprocess.run(
                [readelf, "-S", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if ".codesign" not in signed_sections:
                raise ConanException(f"signer did not add .codesign: {executable}")
            os.replace(temporary, executable)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _resolve_tool(self, tool, llvm=True):
        compiler = self._c_compiler()
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path)
        compiler_name = os.path.basename(compiler_path)
        suffix = (
            compiler_name[len("clang") :]
            if compiler_name.startswith("clang")
            else ""
        )
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        candidates = [executables.get(tool)]
        if compiler_dir:
            if llvm:
                candidates.extend(
                    [
                        os.path.join(compiler_dir, f"llvm-{tool}{suffix}"),
                        os.path.join(compiler_dir, f"llvm-{tool}"),
                    ]
                )
            candidates.append(os.path.join(compiler_dir, tool))
        if llvm and suffix:
            candidates.append(f"llvm-{tool}{suffix}")
        if llvm:
            candidates.append(f"llvm-{tool}")
        candidates.append(tool)
        for candidate in candidates:
            if candidate:
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved
        raise ConanInvalidConfiguration(f"required OHOS tool was not found: {tool}")

    @staticmethod
    def _relax_private_umask(configure):
        path = Path(configure)
        content = path.read_text(encoding="utf-8", errors="surrogateescape")
        if content.count("umask 077") != 2:
            raise ConanInvalidConfiguration(
                "unexpected number of private umask commands in configure"
            )
        content = content.replace("umask 077", "umask 022")
        path.write_text(content, encoding="utf-8", errors="surrogateescape")

    def _relocate_metadata(self):
        for name in ("libpng16.pc", "libpng.pc"):
            pc_path = Path(self.package_folder, "lib", "pkgconfig", name)
            if not pc_path.is_file():
                raise ConanException(f"installed pkg-config file is missing: {name}")
            content = pc_path.read_text(encoding="utf-8")
            content, count = re.subn(
                r"^prefix=.*$",
                "prefix=${pcfiledir}/../..",
                content,
                count=1,
                flags=re.MULTILINE,
            )
            if count != 1:
                raise ConanException(f"{name} has no unique prefix field")
            pc_path.write_text(content, encoding="utf-8")
        for name in ("libpng16.la", "libpng.la"):
            la_path = Path(self.package_folder, "lib", name)
            if la_path.is_file():
                la_path.unlink()
        for name in ("libpng16-config", "libpng-config"):
            config_path = Path(self.package_folder, "bin", name)
            if config_path.is_file():
                config_path.unlink()
