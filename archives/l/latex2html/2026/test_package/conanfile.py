#!/usr/bin/env python3
import os, shutil
from conan import ConanFile
from conan.tools.build import can_run
class Latex2HtmlTestConan(ConanFile):
    settings = "os","arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    def requirements(self):
        self.requires(self.tested_reference_str)
    def test(self):
        if can_run(self):
            # 非-TeXLive 构建中 l2hconf.pm 将 $TMP 固化为 @TMPSPACE@（configure 检测
            # temporary disk space 的结果）。test_latex2html.sh 从自身运行时环境
            # TMPDIR 读取目录并用 latex2html 正式参数 -tmp 覆盖 $TMP，避免
            # Python 创建子目录与 Perl 运行时判定在 Worker 上下文不一致。
            pkg = self.dependencies["latex2html"]
            lb = None
            for r,d,f in os.walk(pkg.package_folder):
                if "latex2html" in f:
                    lb = os.path.join(r,"latex2html")
                    # Both shared and unshared lib dirs needed for latex2html modules
                    share = os.path.join(pkg.package_folder,"share","lib","latex2html")
                    lib = os.path.join(pkg.package_folder,"lib","latex2html")
                    perllib = ":".join(p for p in [share, lib] if os.path.isdir(p))
                    if perllib:
                        os.environ["PERL5LIB"] = perllib + ":" + os.environ.get("PERL5LIB", "")
                    if os.path.isdir(share):
                        os.environ["LATEX2HTMLDIR"] = share
                    break
            if not lb: raise Exception("binary not found")
            sp = os.path.join(self.source_folder,"test_latex2html.sh")
            if os.path.isfile(sp):
                bp = os.environ.get("SHELL") or shutil.which("bash") or "/bin/sh"
                self.run(f'cd "{self.source_folder}" && "{bp}" ./test_latex2html.sh "{lb}"', env="conanrun")
            else:
                tmpdir = os.environ.get("TMPDIR") or ""
                if not (tmpdir and os.path.isabs(tmpdir) and os.path.isdir(tmpdir) and os.access(tmpdir, os.W_OK)):
                    raise Exception(f"no writable runtime TMPDIR: {tmpdir!r}")
                self.run(f'"{lb}" -tmp "{tmpdir}" --version', env="conanrun")
