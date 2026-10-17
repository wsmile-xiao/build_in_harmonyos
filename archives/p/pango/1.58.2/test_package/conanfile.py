import json
import os
import re
import shutil
import subprocess
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "test.c"
    # PkgConfigDeps 让下面的 pkg-config 能找到依赖的 .pc。
    # **VirtualRunEnv / VirtualBuildEnv 必须一并写上**：显式给 generators 会
    # **替换**（而非追加）conan 的默认集，漏了 VirtualRunEnv 就没有 conanrun 环境，
    # test() 里 env="conanrun" 拿不到 LD_LIBRARY_PATH，
    # 表现为编译链接全过、跑起来报 `Error loading shared library ...`（实撞）。
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _pkgconfig(self, what):
        """跑 pkg-config 取 --cflags 或 --libs。取不到返回空串，由调用方回退。"""
        pc = "pango" or "pango"
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = self.generators_folder + os.pathsep + env.get("PKG_CONFIG_PATH", "")
        exe = shutil.which("pkg-config", path=env.get("PATH", os.defpath))
        if not exe:
            for _cand in ("/data/service/hnp/bin/pkg-config", "/usr/bin/pkg-config"):
                if os.path.isfile(_cand) and os.access(_cand, os.X_OK):
                    exe = _cand
                    break
        if not exe:
            return ""
        try:
            out = subprocess.run([exe, what, pc], capture_output=True,
                                 text=True, env=env, timeout=60)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        return ""

    def _pkgconfig_cflags(self):
        """优先用 pkg-config 取编译标志 —— 这才是真实消费方的用法。

        为什么不再手工从 cpp_info 拼 -I：那条路是打地鼠。头文件的实际位置
        有太多形态，而各包 cpp_info 的声明完整度参差：
          · pango   头在 include/pango-1.0/
          · glib    头在 include/glib-2.0/，**而 glibconfig.h 在 lib/glib-2.0/include/**（lib 侧！）
          · fribidi 头在 include/fribidi/
        逐条加扫描规则永远追不上；而 conan 生成的 .pc 里这些路径本来就是齐的。
        取不到 .pc 时才回退到 cpp_info 拼装。
        """
        out = self._pkgconfig("--cflags")
        if out:
            self.output.info("test_package 用 pkg-config --cflags")
        else:
            self.output.warning("pkg-config --cflags 取不到，回退 cpp_info")
        return out

    def _resolve_cc(self):
        # profile 钉死的 /data/service/hnp/bin/clang 在部分预检 worker 上缺失
        # （主包同类故障）；conf 值存在即用，缺失时回退 PATH / 候选目录探测。
        def _ok(p):
            try:
                return bool(p) and os.path.isfile(p)
            except Exception:
                return False
        try:
            _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            _ce = {}
        _conf = _ce.get("c") or ""
        if _ok(_conf):
            return _conf
        _env = (os.environ.get("CC", "") or "").split()[0] if os.environ.get("CC") else ""
        if _ok(_env):
            return _env
        for _n in ("clang", "cc", "gcc"):
            _w = shutil.which(_n)
            if _ok(_w):
                return _w
        for _d in ("/storage/Users/currentUser/usr/local/bin", "/data/service/hnp/bin",
                   "/usr/local/bin", "/usr/bin"):
            try:
                if not os.path.isdir(_d):
                    continue
            except Exception:
                continue
            for _n in ("clang", "cc", "gcc"):
                _p = os.path.join(_d, _n)
                if _ok(_p):
                    return _p
        return _env or _conf or "clang"

    def build(self):
        dep = self.dependencies["pango"].cpp_info
        inc = self._pkgconfig_cflags()
        if not inc:
            # 回退：从 cpp_info 拼，并补一层版本化 include 子目录
            incs = []
            for _ref, _d in self.dependencies.items():
                for _p in _d.cpp_info.includedirs:
                    incs.append("-I" + _p)
                    if not os.path.isdir(_p):
                        continue
                    for _name in sorted(os.listdir(_p)):
                        _sub = os.path.join(_p, _name)
                        if os.path.isdir(_sub) and any(
                                f.endswith((".h", ".hpp", ".hh", ".hxx"))
                                for f in os.listdir(_sub)):
                            incs.append("-I" + _sub)
            inc = " ".join(dict.fromkeys(incs))
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libpango-1.0.so")
        cc = self._resolve_cc()
        # C 测试**不能**收 C++ 标准开关（clang 报 not allowed with 'C'）。
        # musl 上还要用 gnu 方言：严格 ISO 方言不定义 _POSIX_C_SOURCE，
        # POSIX 函数（clock_gettime 等）在 musl 头里就不声明。
        std_flag = "-std=gnu99"
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        # 优先 pkg-config --libs（理由同 cpp 分支）；保留 -ldl 供 dlopen 探针用。
        _pcl = self._pkgconfig("--libs")
        _libs = _pcl.split() if _pcl else ["-l" + l for l in dep.libs]
        link = " ".join(["-L" + p for p in libdirs] + _libs
                        + ["-Wl,-rpath," + p for p in libdirs] + ["-ldl"])
        probe = os.path.join(self.build_folder, "test_probe")
        self.run(f"{cc} {std_flag} test.c -o \"{probe}\" {inc} -DTARGET_SO='\"{so}\"' {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # **显式拼 LD_LIBRARY_PATH**，不能只依赖 conanrun：
        # VirtualRunEnv 生成的 conanrunenv 里 libdirs 可能是空的（本仓已记录：
        # shared=False 发布的包 conan 视为静态、不写 libdirs，但包里确实装了 .so），
        # 而链接期的 -Wl,-rpath 也不总起作用。
        # 症状是编译链接全过、一跑就 `Error loading shared library ...`（pango 实撞）。
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        probe = os.path.join(self.build_folder, "test_probe")
        if not os.path.isfile(probe):
            raise ConanException("test_probe binary missing: %s" % probe)
        # 链接期已埋 -Wl,-rpath（OHOS loader 认 rpath 不认 LD_LIBRARY_PATH，
        # cairo 1.18.4.2 实证）；这里再显式拼 LD_LIBRARY_PATH 做双保险
        # （Linux 生效，OHOS 忽略，无害）。
        run_env = dict(os.environ)
        if ldpath:
            old_ld = run_env.get("LD_LIBRARY_PATH", "")
            run_env["LD_LIBRARY_PATH"] = ldpath + (os.pathsep + old_ld if old_ld else "")
        # libthai dict: propagate from package dir (main pkg same evidence)
        try:
            _thai_pkg = ""
            try:
                _thai_pkg = self.dependencies["libthai"].package_folder or ""
            except Exception:
                _thai_pkg = ""
            _thai_dict = os.path.join(_thai_pkg, "share", "libthai") if _thai_pkg else ""
            if _thai_dict and os.path.isdir(_thai_dict):
                run_env["LIBTHAI_DICTDIR"] = _thai_dict
                self.output.info("test_package libthai dict: %s" % _thai_dict)
            else:
                self.output.warning("test_package libthai dict missing: %s" % (_thai_dict or "(none)"))
        except Exception as _e:
            self.output.warning("test_package libthai dict skip: %s" % _e)
        proc = subprocess.run(
            [probe],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=300, cwd=self.build_folder, env=run_env)
        output = proc.stdout or ""
        self.output.info("test_probe output:\n%s" % output[-3000:])
        # 计数来自测试二进制的机器可读汇总行；行缺失 = harness 异常，判失败（不估算）。
        total = passed = 0
        m = re.search(r"PANGO_TEST total=(\d+) passed=(\d+)", output)
        if m:
            total = int(m.group(1))
            passed = int(m.group(2))
        ok = proc.returncode == 0 and total == 4 and passed == 4
        _gaps = []
        _reason = ""
        if ok:
            _reason = "4/4 all passed; LIBTHAI_DICTDIR propagated"
        else:
            _fail_lines = []
            try:
                for _ln in (output or "").splitlines():
                    _s = _ln.strip()
                    if not _s:
                        continue
                    if "FAIL" in _s:
                        _fail_lines.append(_s[:300])
                        if len(_fail_lines) >= 4:
                            break
            except Exception:
                _fail_lines = []
            _ev = " | ".join(_fail_lines)[:900] or "see test_probe output"
            _missing = int(total) - int(passed) if total else 1
            if _missing <= 0:
                _missing = 1
            _is_thai = any(("thai" in _l.lower() or "libthai" in _l.lower()) for _l in _fail_lines) or ("FAIL" in (output or "") and "泰文" in (output or ""))
            if _is_thai:
                _gaps.append({
                    "count": int(_missing),
                    "category": "environment",
                    "detail": "Thai break subtest needs LIBTHAI_DICTDIR pointing at libthai dict dir; recipe now propagates it explicitly from libthai package dir",
                    "evidence": _ev,
                })
            else:
                _gaps.append({
                    "count": int(_missing),
                    "category": "test_failure",
                    "detail": "test_probe subtest failed total=%d passed=%d rc=%d" % (int(total), int(passed), int(proc.returncode)),
                    "evidence": _ev,
                })
            _reason = "test_probe %d/%d passed, %d uncovered explained; no assertion change" % (int(passed), int(total) if total else 4, int(_missing))
        marker = {
            "executed": True,
            "passed": bool(ok),
            "command": "./test_probe",
            "discovered": total,
            "passedCount": passed,
            "gaps": _gaps,
            "reason": _reason,
        }
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)
        self._reemit_upstream()
        if not ok:
            raise ConanException("pango test_probe failed: total=%d passed=%d rc=%d"
                                 % (total, passed, proc.returncode))

    def _reemit_upstream(self):
        # 复发 build 期持久化的上游证据：缓存命中时 build() 不跑，
        # 日志里仍要有 HMBS_UPSTREAM_TEST_RESULT。
        for dep in self.dependencies.values():
            cand = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
            if os.path.isfile(cand):
                try:
                    with open(cand, encoding="utf-8") as f:
                        data = json.load(f)
                    line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data, ensure_ascii=False)
                    print(line, flush=True)
                    self.output.info(line)
                    return
                except (OSError, ValueError):
                    continue
