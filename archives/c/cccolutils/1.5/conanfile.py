#!/usr/bin/env python3
"""Conan recipe — cccolutils 1.5 (Kerberos5 凭据缓存集合工具, 单文件 CPython 扩展).

setuptools build_ext 等价的 CPython 扩展(设备 cc 直接编译, CI 不依赖 setuptools);
唯一编译依赖 krb5/1.22.1(本仓)。
CI 修复: HNP python 的 sysconfig INCLUDEPY/LIBDIR 损坏(空值/指向不存在目录,
Python.h not found 即此), 改用 cpython-tkinter 已 CI 验证的探测策略——
get_paths()['include'] + Python.h 真实存在性校验; libpython 用 /proc/self/maps
问解释器本进程实际加载的文件(ground truth), 完整路径直接喂链接器
(OHOS/musl 下 Py* 不进全局符号表, 不链 libpython 则 import 段错误, ML-0008)。
产物 .so 按目标解释器 EXT_SUFFIX 命名(setuptools 语义, import 才能命中)。
E002: TMPDIR 落可写目录; E077/ML-0043: 扩展 .so 构建后 binary-sign-tool 重签
(沙箱 dlopen 强校验 .codesign); 运行期 LD_LIBRARY_PATH 补 libpython 目录双保险。
上游 unittest(3 用例)build() 内真实执行, 计数写 res/; test_package 读取输出
HMBS_UPSTREAM_TEST_RESULT(gate 只扫 test_package stdout; 命中缓存二进制时 build()
被跳过)。E212 沙箱退化静态校验, 如实 failed, 不伪造。
"""
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get


class CccolutilsConan(ConanFile):
    name = "cccolutils"
    version = "1.5"
    package_type = "library"
    license = "GPL-2.0-or-later"
    description = "Kerberos5 Credential Cache Collection Utilities (CPython extension)"
    homepage = "https://pagure.io/cccolutils"
    url = "https://pagure.io/cccolutils"
    settings = "os", "arch", "compiler", "build_type"
    # Conan2 硬性要求: package_type=library 必须声明 shared(产物是扩展 .so, 无静/共之分)
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def requirements(self):
        self.requires("krb5/1.22.1")

    # --- 找目标 python3（PATH 无关：CI 构建环境常不把 python3 放进 PATH，但 HOME 有设）---
    def _py(self):
        for c in (os.environ.get("HMBS_PYTHON3"), shutil.which("python3"),
                  os.path.expanduser("~/usr/local/bin/python3"),
                  "/usr/local/bin/python3", "/usr/bin/python3"):
            if c and os.path.isfile(c):
                return c
        raise ConanInvalidConfiguration(
            "cccolutils: 找不到 python3: 设 HMBS_PYTHON3=<带 dev 头的 python 路径>")

    # --- 自发现目标 Python 的 dev 环境（cpython-tkinter 已 CI 验证的策略）---
    # CI 的 HNP python sysconfig INCLUDEPY 损坏(空值/不存在 → Python.h not found);
    # 改用 get_paths()['include'] + 真实存在性校验; libpython 用 /proc/self/maps 问
    # 解释器本进程实际加载的文件(ground truth, 比 sysconfig LIBDIR/LDLIBRARY 可靠)。
    def _pyinfo(self):
        cached = getattr(self, "_pyinfo_cache", None)
        if cached:
            return cached
        py = self._py()
        code = ("import sysconfig,sys,json,os;"
                "d=dict(inc=sysconfig.get_paths()['include'] or '',"
                "ext=sysconfig.get_config_var('EXT_SUFFIX') or '',"
                "libdir=sysconfig.get_config_var('LIBDIR') or '',"
                "libpl=sysconfig.get_config_var('LIBPL') or '',"
                "prefix=getattr(sys,'base_prefix','') or '',"
                "ver='%d.%d'%sys.version_info[:2]);"
                "m=[l.split()[-1] for l in open('/proc/self/maps') "
                "if 'libpython' in l] if os.path.exists('/proc/self/maps') else [];"
                "d['libpython']=m[0] if m else '';"
                "print(json.dumps(d))")
        r = subprocess.run([py, "-c", code], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise ConanException("cccolutils: python3 探测失败: %s"
                                 % ((r.stderr or r.stdout or "").strip()[-400:]))
        info = json.loads(r.stdout.strip().splitlines()[-1])
        if not (info.get("inc") and os.path.isfile(os.path.join(info["inc"], "Python.h"))):
            raise ConanInvalidConfiguration(
                "cccolutils: Python.h 不存在(inc=%s)——需带 dev 头的 python3, "
                "或设 HMBS_PYTHON3=<带 dev 头 python 路径>" % (info.get("inc") or "?"))
        ext = info.get("ext") or ""
        info["ext"] = ext if ext.endswith(".so") else ".so"
        info["py"] = py
        info["libpython"] = self._libpython_file(py, info)
        self.output.info("cccolutils: python3=%s ver=%s inc=%s ext=%s libpython=%s"
                         % (py, info["ver"], info["inc"], info["ext"], info["libpython"]))
        self._pyinfo_cache = info
        return info

    # 定位一个可链接的 libpython 完整文件(直接喂给链接器, 不走 -L/-l, 免去「目录里
    # 要有 .so 软链」的依赖; 链接器读其 DT_SONAME 记成 NEEDED=libpythonX.Y.so.Z,
    # 运行期按 SONAME 解析)。优先解释器自报的实际加载路径。
    def _libpython_file(self, py, info):
        lp = info.get("libpython") or ""
        if lp and os.path.isfile(lp):
            return lp                            # 解释器实际加载的 libpython —— ground truth
        ver = info["ver"]                        # 如 "3.12"
        checked = []
        for d in [info.get("libpl"), info.get("libdir"),
                  os.path.join(info.get("prefix", ""), "lib"),
                  os.path.join(os.path.dirname(os.path.dirname(py)), "lib"),
                  os.path.expanduser("~/usr/local/lib"), "/usr/local/lib"]:
            if not d or d in checked:
                continue
            checked.append(d)
            hits = (glob.glob(os.path.join(d, "libpython%s.so" % ver))
                    or glob.glob(os.path.join(d, "libpython%s.so.*" % ver)))
            if hits:
                return sorted(hits)[0]
        for r in [info.get("prefix"), os.path.dirname(os.path.dirname(py)),
                  os.path.expanduser("~/usr/local")]:
            if r and os.path.isdir(r):
                try:
                    out = subprocess.check_output(
                        ["find", r, "-name", "libpython%s.so*" % ver],
                        stderr=subprocess.DEVNULL, timeout=60).decode().split()
                except Exception:
                    out = []
                if out:
                    return out[0]
        raise ConanInvalidConfiguration(
            "cccolutils: 找不到 libpython%s.so(扩展须链 libpython, OHOS/musl 下 Py* 不进"
            "全局符号表, 不链则 import 段错误)。python=%s; /proc/self/maps 未见 libpython; "
            "查过 %s; prefix 下 find 亦空" % (ver, py, checked))

    def _pyver(self, name=""):
        m = re.search(r"cpython-(\d)(\d+)", name)
        if m:
            return "%s.%s" % (m.group(1), m.group(2))
        try:
            return self._pyinfo()["ver"]
        except Exception:
            return "%d.%d" % sys.version_info[:2]

    def _tmpdir(self):
        # E002: OHOS /tmp erofs 只读
        for d in (os.environ.get("TMPDIR"), "/tmp"):
            if d and os.access(d, os.W_OK):
                return d
        d = os.path.join(os.path.join(os.path.expanduser("~"), "tmp"))
        os.makedirs(d, exist_ok=True)
        return d

    def _sign(self, p):
        # E077/ML-0043: AppSpawn 沙箱 dlopen 强校验 .codesign
        oc = "/data/service/hnp/bin/llvm-objcopy"
        sg = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(oc) and os.path.isfile(sg)):
            self.output.warning("cccolutils: signer missing; %s 未签名" % p)
            return
        subprocess.run([oc, "--remove-section", ".codesign", p],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        r = subprocess.run([sg, "sign", "-inFile", p, "-outFile", p, "-selfSign", "1"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            os.chmod(p, 0o755)  # 签名后权限归零
            self.output.info("cccolutils: signed %s" % os.path.basename(p))
        else:
            self.output.warning("cccolutils: sign failed: %s" % (r.stderr or "")[-300:])

    def _check_so(self, p):
        # E212 静态校验: ELF 魔数 + .codesign 段 + PyInit_cccolutils 入口
        try:
            d = open(p, "rb").read()
        except OSError:
            return False
        return d.startswith(b"\x7fELF") and b".codesign" in d and b"PyInit_cccolutils" in d

    def build(self):
        info = self._pyinfo()
        os.environ["TMPDIR"] = self._tmpdir()
        krb5 = self.dependencies["krb5"]
        pf = krb5.package_folder
        incs = [info["inc"]] + [os.path.join(pf, d) for d in krb5.cpp_info.includedirs]
        cflags = " ".join("-I" + d for d in incs)
        lflags = " ".join("-L" + os.path.join(pf, d) for d in krb5.cpp_info.libdirs)
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or os.environ.get("CC") or shutil.which("cc") or "cc"
        out = os.path.join(self.source_folder, "cccolutils" + info["ext"])
        # 等价上游 setup.py build_ext: 同一 C 源, -shared -fPIC;
        # libpython 完整路径直接进链接行(musl 下 Py* 不进全局符号表, 必须显式链)。
        # CI 修复: subprocess 列表形式不经过 shell, 含空格的 cflags/lflags 字符串
        # 若作为单个元素传入, clang 会把整串当一个参数 → 全部 -I/-L 失效
        # (Python.h not found), 必须 shlex.split 拆成独立 argv 元素。
        cmd = [cc, "-shared", "-fPIC", "-O2"] + shlex.split(cflags) + \
              [os.path.join(self.source_folder, "cccolutils.c"), "-o", out] + \
              shlex.split(lflags) + \
              ["-lkrb5", "-lk5crypto", "-lcom_err", info["libpython"]]
        r = subprocess.run(cmd, cwd=self.source_folder, capture_output=True, text=True)
        if r.returncode != 0:
            raise ConanException("cccolutils: compile failed: %s"
                                 % (r.stderr or r.stdout or "").strip()[-2000:])
        self._sign(out)
        self._upstream_tests(info, [out])

    def _upstream_tests(self, info, sos):
        # 上游 unittest 真实执行并解析计数(数字来自真机输出, 不伪造)
        py = info["py"]
        env = dict(os.environ)
        env["PYTHONPATH"] = self.source_folder
        ld = [os.path.join(self.dependencies["krb5"].package_folder, d)
              for d in self.dependencies["krb5"].cpp_info.libdirs]
        # libpython 目录用解释器实际加载文件的目录(ground truth), 不信 sysconfig LIBDIR
        lpdir = os.path.dirname(info["libpython"])
        if lpdir:
            ld.append(lpdir)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(ld) + os.pathsep + env.get("LD_LIBRARY_PATH", "")
        try:
            r = subprocess.run([py, "-m", "unittest", "tests.cccolutils_test", "-v"],
                               cwd=self.source_folder, env=env, capture_output=True,
                               text=True, timeout=600)
            out = (r.stdout or "") + "\n" + (r.stderr or "")
        except Exception as exc:
            r, out = None, str(exc)
        m = re.search(r"Ran (\d+) tests", out)
        discovered = int(m.group(1)) if m else 0
        m = re.search(r"FAILED \(failures=(\d+)(?:,\s*errors=(\d+))?\)", out)
        failed = (int(m.group(1)) + (int(m.group(2)) if m.group(2) else 0)) if m else 0
        m = re.search(r"OK \(skipped=(\d+)\)", out)
        skipped = int(m.group(1)) if m else 0
        ok = bool(r) and r.returncode == 0 and bool(re.search(r"^OK(\s|$)", out, re.M))
        summary = {
            "status": "passed" if ok else "failed",
            "framework": "unittest",
            "command": "python3 -m unittest tests.cccolutils_test -v",
            "discovered": discovered, "executed": discovered,
            "passed": max(0, discovered - failed - skipped) if ok else 0,
            "failed": failed, "skipped": skipped,
            "note": "test_get_user_from_realm 断言体仅 Python2 生效(Python3 空操作通过); "
                    "真实断言为 unknown realm→None 与 has_creds→False(空 DIR: 缓存)"}
        if not ok and "Permission denied" in out:
            # E212: hmmac 拒绝用户路径 dlopen(与签名无关), 退化静态校验
            self.output.warning("cccolutils: E212 hmmac blocks dlopen; static verification")
            for so in sos:
                self.output.info("cccolutils artifact check [%s] %s"
                                 % ("PASS" if self._check_so(so) else "FAIL", os.path.basename(so)))
            summary["reason"] = "E212 hmmac: user-path dlopen Permission denied; static only, no live count"
        with open(os.path.join(self.source_folder, "upstream_test_summary.json"),
                  "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        self.output.info("cccolutils: upstream summary: %s"
                         % json.dumps(summary, ensure_ascii=False))

    def package(self):
        sos = sorted(glob.glob(os.path.join(self.source_folder, "cccolutils*.so")))
        if not sos:
            raise ConanException("cccolutils: no extension .so to package")
        pyver = self._pyver(os.path.basename(sos[0]))
        site = os.path.join(self.package_folder, "lib", "python" + pyver, "site-packages")
        os.makedirs(site, exist_ok=True)
        for so in sos:
            shutil.copy2(so, os.path.join(site, os.path.basename(so)))
        dist = os.path.join(site, "cccolutils-%s.dist-info" % self.version)
        os.makedirs(dist, exist_ok=True)
        with open(os.path.join(dist, "METADATA"), "w", encoding="utf-8") as f:
            f.write("Metadata-Version: 2.1\nName: cccolutils\nVersion: %s\n"
                    "Summary: Kerberos5 Credential Cache Collection Utilities\n"
                    "License: GPL-2.0-or-later\nHome-page: %s\n"
                    % (self.version, self.homepage))
        # 许可证(tarball 内 COPYING 或 LICENSE)
        for lic in ("COPYING", "LICENSE"):
            if os.path.isfile(os.path.join(self.source_folder, lic)):
                copy(self, lic, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
                break
        # 上游测试计数拷入包内 res/, test_package 读取输出 HMBS marker
        src = os.path.join(self.source_folder, "upstream_test_summary.json")
        if os.path.isfile(src):
            os.makedirs(os.path.join(self.package_folder, "res"), exist_ok=True)
            shutil.copy2(src, os.path.join(self.package_folder, "res",
                                           "upstream_test_summary.json"))

    def package_info(self):
        # Python 扩展绑定: 不给 C/C++ 消费者提供链接库
        self.cpp_info.libs = []
        sos = glob.glob(os.path.join(self.package_folder, "lib", "python*",
                                     "site-packages", "cccolutils*.so"))
        pyver = self._pyver(os.path.basename(sos[0]) if sos else "")
        site = os.path.join("lib", "python" + pyver, "site-packages")
        # 让 test_package/下游经 PYTHONPATH 直接 import cccolutils
        self.runenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, site))
        # E004 双保险: 运行期补 libpython 实际加载文件的目录(不信可能损坏的 sysconfig LIBDIR)
        lpdir = ""
        try:
            lpdir = os.path.dirname(self._pyinfo()["libpython"])
        except (ConanInvalidConfiguration, ConanException):
            lpdir = ""
        if lpdir and os.path.isdir(lpdir):
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", lpdir)
