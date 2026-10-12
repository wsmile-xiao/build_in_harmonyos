#!/usr/bin/env python3
"""Conan test_package — libpsml 2.1.0 消费者验证（Conan L1）

真实消费者：用 Fortran 写一个 `use m_psml` 的程序，链接包里的
libpsml.a + libxmlf90.a，跑通「解析上游 Si fixture → 断言原子序数/
元素符号 → 缺失文件错误路径」4 个检查（R34：实质调用被测包 API）。

Fortran 编译用与生产包同一工具链 flang-ohos/20.1.0（.mod 是编译器
私有接口），链接沿用 fortran-shlex 实测口径：flang 编译 + OHOS
clang 驱动链接，显式静态 Fortran 运行时。
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv


class LibpsmlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = ("test_libpsml_consumer.f90", "run_consumer.sh",
                       "fixtures/14_Si.psml")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("test_package 仅在 os=OHOS 下有效")

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _tools(self):
        package = self.dependencies["libpsml"].package_folder
        flang_package = self.dependencies.build["flang-ohos"].package_folder
        flang = os.path.join(flang_package, "bin", "flang")
        flang_lib = os.path.join(flang_package, "lib")
        fortran_runtime = os.path.join(flang_lib, "libFortranRuntime.a")
        fortran_decimal = os.path.join(flang_lib, "libFortranDecimal.a")
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        raw = compilers.get("c", "")
        clang = ""
        # 聚合经验#1：conf 存在即用，缺失时经 PATH 发现（真机 conf 的
        # /data/service/hnp/bin/clang 在 harmonybrew runner 上不存在）。
        for cand in ([raw.split()[0] if isinstance(raw, str) else raw]
                     if raw else []):
            if cand:
                hit = shutil.which(cand)
                if hit:
                    clang = hit
                    break
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    clang = os.path.abspath(cand)
                    break
        if not clang:
            hit = shutil.which("clang")
            if hit:
                clang = hit
        if not clang:
            fallback = "/data/service/hnp/bin/clang"
            if os.path.isfile(fallback) and os.access(fallback, os.X_OK):
                clang = fallback
        if not clang:
            raise ConanInvalidConfiguration(
                "C 驱动均不可用（conf=%s）；属环境故障" % raw)
        include_dir = os.path.join(package, "include")
        library_dir = os.path.join(package, "lib")
        for required in (flang, clang, fortran_runtime, fortran_decimal,
                         include_dir, library_dir):
            if not os.path.isfile(required) and not os.path.isdir(required):
                raise ConanInvalidConfiguration(
                    "required consumer-test input is missing: {}".format(
                        required))
        return (flang, clang, fortran_runtime, fortran_decimal,
                include_dir, library_dir, flang_lib)

    def _mod_include_flags(self, include_dir):
        """包内所有含 .mod 的目录（顶层 include + 编译器版本子目录）。"""
        dirs = [include_dir]
        for cur, _dirs, files in os.walk(include_dir):
            if any(n.endswith(".mod") for n in files) and cur != include_dir:
                dirs.append(cur)
        return " ".join('-I"%s"' % d for d in sorted(set(dirs)))

    def _ohos_flags(self, clang):
        """推导 OHOS 编译/链接旗标（--target/--sysroot/-resource-dir/-L）。

        主包同理：-print-sysroot 在包装 clang 上 exit 1，故从
        -print-resource-dir 与驱动祖先反推 native/sysroot；找不到即返回
        空串并如实警告，由调用方决定是否继续（链接无 sysroot 必缺
        Scrt1.o，故 test() 侧找不到时直接判环境错）。
        """
        target = "--target=aarch64-unknown-linux-ohos"
        try:
            env = os.environ.copy()
            resource = subprocess.run(
                [clang, "-print-resource-dir"], check=False, env=env,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=30).stdout.strip()
            resource = os.path.realpath(resource) if resource else ""
            if resource and not os.path.isdir(resource):
                resource = ""
        except Exception as e:
            self.output.warning("HMBS diag test resource probe failed: %s" % e)
            resource = ""
        sysroot = ""
        anchors = [p for p in (resource, os.path.realpath(clang)) if p]
        for anchor in anchors:
            cur = anchor if os.path.isdir(anchor) else os.path.dirname(anchor)
            for _ in range(10):
                for cand in (os.path.join(cur, "sysroot"),
                             os.path.join(cur, "native", "sysroot")):
                    if os.path.isdir(cand):
                        sysroot = os.path.realpath(cand)
                        break
                if sysroot:
                    break
                if os.path.basename(cur) == "native":
                    cand = os.path.join(cur, "sysroot")
                    if os.path.isdir(cand):
                        sysroot = os.path.realpath(cand)
                        break
                parent = os.path.dirname(cur)
                if parent == cur:
                    break
                cur = parent
            if sysroot:
                break
        unwind = ""
        for base in ([os.path.join(os.path.dirname(sysroot), "llvm", "lib",
                                   "aarch64-linux-ohos")] if sysroot else []):
            if os.path.isfile(os.path.join(base, "libunwind.a")):
                unwind = base
                break
        if not unwind and resource:
            cand = os.path.normpath(os.path.join(
                resource, "..", "..", "..", "aarch64-linux-ohos"))
            if os.path.isfile(os.path.join(cand, "libunwind.a")):
                unwind = cand
        self.output.info(
            "HMBS diag test flags sysroot=%s resource=%s unwind=%s"
            % (sysroot, resource, unwind))
        compile_flags = [target]
        if sysroot:
            compile_flags.append("--sysroot=%s" % sysroot)
        if resource:
            compile_flags.append("-resource-dir=%s" % resource)
        link_flags = list(compile_flags)
        if unwind:
            link_flags.append("-L%s" % unwind)
        return (" ".join(compile_flags), " ".join(link_flags))

    def build(self):
        (flang, _clang, _runtime, _decimal, include_dir, _lib,
         _flang_lib) = self._tools()
        # flang 编译同样需要 target/sysroot/resource，否则 .o 与主包 ABI
        # 不一致且后续 clang 链接缺启动文件（Scrt1.o 教训）。
        compile_flags, _link_flags = self._ohos_flags(_clang)
        src = os.path.join(self.source_folder, "test_libpsml_consumer.f90")
        obj = os.path.join(self.build_folder, "test_libpsml_consumer.o")
        self.run(
            '"{fc}" {flags} -O2 {incs} "{src}" -c -o "{obj}"'.format(
                fc=flang,
                flags=compile_flags,
                incs=self._mod_include_flags(include_dir),
                src=src,
                obj=obj,
            ),
            env="conanbuild",
        )

    def _hmbs_emit(self, line):
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: build verified, runtime skipped")
            return
        (_flang, clang, fortran_runtime, fortran_decimal, include_dir,
         library_dir, flang_lib) = self._tools()
        obj = os.path.join(self.build_folder, "test_libpsml_consumer.o")
        binary = os.path.join(self.build_folder, "test_libpsml_consumer")
        fixture = os.path.join(self.source_folder, "fixtures", "14_Si.psml")
        if os.path.getsize(fixture) == 0:
            raise RuntimeError("fixture is empty: %s" % fixture)
        # 证伪 guard：被测二进制与参照文件非空（toybox tar 事故教训）。
        _cflags, link_flags = self._ohos_flags(clang)
        if "--sysroot=" not in link_flags:
            raise ConanInvalidConfiguration(
                "无法确定 OHOS sysroot，消费者链接必缺 Scrt1.o；属环境故障")
        self.run(
            '"{cc}" {flags} "{obj}" -L"{lib}" -lpsml -lxmlf90 '
            '"{runtime}" "{decimal}" -lm -o "{bin}"'.format(
                cc=clang,
                flags=link_flags,
                obj=obj,
                lib=library_dir,
                runtime=fortran_runtime,
                decimal=fortran_decimal,
                bin=binary,
            ),
            env="conanbuild",
        )
        if os.path.getsize(binary) == 0:
            raise RuntimeError("test binary is empty: %s" % binary)
        log_path = os.path.join(self.build_folder,
                                "test_libpsml_consumer.log")
        # 主包同理：xmlf90 find_eor_eof 的探测文件需要可写临时目录
        #（STATUS=SCRATCH 在 OHOS 上不可用，补丁回退到 $TMPDIR/当前目录）。
        # build 目录可写，os.environ 直接继承给被测进程。
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = self.build_folder
        # shared 产物运行时需要包内 lib；静态则无害（netcdf-fortran 口径，
        # 用完复原，避免污染后续步骤）。
        previous_ld_path = os.environ.get("LD_LIBRARY_PATH")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            dict.fromkeys([library_dir, flang_lib,
                           previous_ld_path or ""]))
        run_ok = True
        try:
            # L0c 薄包装器：经 POSIX sh 转调真实 Fortran 消费者二进制
            #（ceni/2.33 成功先例；Fortran .f90 不被 L0c 计为测试源）。
            # 包装器内仅 exec，不含任何断言；计数源仍为程序自身汇总行。
            wrapper = os.path.join(self.source_folder, "run_consumer.sh")
            # Windows 检出可能带回 CRLF，OHOS /bin/sh 遇 `set -eu\r` 报
            # `set: - : unknown option`（本轮真机实证）。运行前归一化
            # 为 LF，保证 POSIX 语义；只改换行，不改断言逻辑。
            try:
                with open(wrapper, "rb") as _wf:
                    _wdata = _wf.read()
                if b"\r" in _wdata:
                    _wdata = _wdata.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                    with open(wrapper, "wb") as _wf:
                        _wf.write(_wdata)
                    self.output.info("HMBS diag wrapper CRLF normalized to LF")
            except OSError as _we:
                self.output.warning("HMBS diag wrapper normalize failed: %s" % _we)
            sh = shutil.which("sh") or "/bin/sh"
            self.run('"{sh}" "{wrapper}" "{bin}" "{fixture}" "{log}"'.format(
                sh=sh, wrapper=wrapper, bin=binary, fixture=fixture,
                log=log_path),
                env="conanrun")
        except Exception as e:
            run_ok = False
            self.output.warning("consumer run failed: %s" % e)
        finally:
            if previous_ld_path is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = previous_ld_path
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8",
                      errors="replace") as f:
                out = f.read()
        except OSError as e:
            self.output.warning("cannot read test log %s: %s" % (log_path, e))
        for line in out.splitlines()[-20:]:
            self.output.info("[consumer] %s" % line)
        if not out.strip():
            self.output.warning("consumer produced empty output")
        # 单一确定源：程序自身的汇总行（禁止 stdout 数数/算术修补）。
        m = re.search(r"LIBPSML_CONSUMER\s+(\d+)/(\d+)\s+CHECKS PASSED", out)
        if not m:
            fail_marker = {
                "executed": True,
                "passed": False,
                "command": "sh run_consumer.sh ./test_libpsml_consumer fixtures/14_Si.psml",
                "discovered": 4,
                "passedCount": 0,
            }
            self._hmbs_emit("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(
                fail_marker, separators=(",", ":")))
            raise RuntimeError(
                "consumer left no parseable summary line; searched for "
                "'LIBPSML_CONSUMER N/M CHECKS PASSED' in %s" % log_path)
        passed_count = int(m.group(1))
        discovered = int(m.group(2))
        # 自检恒等式（只诊断，不改数字）。
        if not (0 <= passed_count <= discovered == 4 and discovered > 0):
            self.output.warning(
                "HMBS diag count identity broken: passedCount=%d "
                "discovered=%d" % (passed_count, discovered))
        ok = run_ok and passed_count == discovered == 4
        marker = {
            "executed": True,
            "passed": bool(ok),
            "command": "sh run_consumer.sh ./test_libpsml_consumer fixtures/14_Si.psml",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self._hmbs_emit("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(
            marker, separators=(",", ":")))
        # 主包携带的真实上游结果（cache-hit 轮同样给出证据）。
        self._reemit_upstream()
        if not ok:
            raise RuntimeError(
                "consumer failed: %d/%d passed (run_ok=%s)"
                % (passed_count, discovered, run_ok))

    def _reemit_upstream(self):
        try:
            dep_name = self.tested_reference_str.split("/")[0]
        except Exception:
            dep_name = "libpsml"
        try:
            dep = self.dependencies[dep_name]
        except Exception as e:
            self.output.warning("upstream re-emit lookup failed: %s" % e)
            raise RuntimeError("no dep %s" % dep_name)
        cand = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
        if not os.path.isfile(cand):
            raise RuntimeError(
                "hmbs_upstream.json absent from package res/; upstream "
                "marker left to the main build (cache-miss rounds)")
        with open(cand, "r", encoding="utf-8") as f:
            up = json.load(f)
        ok_shape = (
            isinstance(up, dict)
            and up.get("framework") == "ctest"
            and isinstance(up.get("discovered"), int)
            and isinstance(up.get("executed"), int)
            and isinstance(up.get("passed"), int)
            and isinstance(up.get("failed"), int)
            and isinstance(up.get("skipped"), int)
            and up["passed"] + up["failed"] == up["executed"]
            and up["executed"] + up["skipped"] <= up["discovered"]
        )
        self._hmbs_emit("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
            up, separators=(",", ":")))
        if not ok_shape:
            raise RuntimeError("upstream test evidence invalid: %s" % up)
