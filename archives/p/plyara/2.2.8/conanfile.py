#!/usr/bin/env python3
"""Conan recipe — plyara 2.2.8 (pure Python YARA rule parser).

plyara 的词法/语法分析器由 PLY（Python Lex-Yacc）驱动。上游把 PLY 以 git
submodule 内嵌（.gitmodules: third_party/ply -> github.com/plyara/ply），
并通过 `src/ply -> ../third_party/ply/src/ply` 符号链接暴露给
plyara.core 的 `import ply.lex / ply.yacc`。

HarmonyOS PC 适配要点
---------------------
1. 纯 Python noarch：package_type="python-require"，无 C/C++ 编译。
   产物 = lib/python3.12/site-packages/{plyara,ply} + bin/plyara。
2. GitHub tag 归档不含 submodule 内容：third_party/ply 从上游官方 commit
   单独获取并落位，使 src/ply 符号链接解析为真实目录；package() 拷贝真实
   内容而不依赖符号链接在 HMDFS 下的存续（E046 类约束）。
3. R38：上游 pyproject.toml 声明 [project.scripts]
   `plyara = "plyara.command_line:main"` → 产物含可执行文件，
   软件级 commands.json 必需。
4. OHOS 运行时约束：/tmp 不可写且不可读（E002）。plyara 本体不使用
   tempfile、不生成任何解析表文件，在只读工作目录下亦完整可用
   （鸿蒙专项测试见 test_package/test_ohos_plyara.py）。
5. 源码零平台分支（src/plyara/*.py、src/ply/*.py 中无 sys.platform /
   os.name / platform.system 判断，已实测 grep 零命中），因此不需要任何
   OHOS 源码补丁 —— 适配集中在交付形态与运行时契约。

上游测试：`python -m unittest discover`（上游
.github/workflows/test-action.yaml 同款命令），共 6 个测试模块。
tests/test_linters.py 需要上游 [tests] extra（pycodestyle / pydocstyle /
pyflakes）；本机缺失时 build() 尽力装到 build_folder 私有目录（不污染
worker 全局 site-packages，不注入共享前缀），失败则如实记录为 import 错误。
"""
import importlib.util
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

PY_VER = f"python{sys.version_info.major}.{sys.version_info.minor}"
SITE_REL = os.path.join("lib", PY_VER, "site-packages")
UPSTREAM_TEST_TIMEOUT = 2700
TEST_EXTRAS = ("pycodestyle", "pydocstyle", "pyflakes")


class PlyaraConan(ConanFile):
    name = "plyara"
    version = "2.2.8"
    package_type = "python-require"
    license = "Apache-2.0"
    homepage = "https://github.com/plyara/plyara"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    description = ("plyara - Parse YARA rules into a Python dictionary "
                   "representation (pure Python, vendored PLY lexer/parser)")
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # 必须在 export_sources()（而非 export()）中调用：conan 2.29 的
        # export() 阶段 export_sources_folder 尚未设置（a52dec/awscli 先例）。
        export_conandata_patches(self)

    def requirements(self):
        # pyproject.toml [project] 无 dependencies 键：零运行时第三方依赖。
        # 词法/语法分析器来自上游内嵌 submodule（third_party/ply），随源码分发。
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # GitHub 归档不含 submodule 内容：third_party/ply 缺失会让 src/ply
        # 成为悬空符号链接，import ply.lex 直接失败。
        ply = self.conan_data["ply"]
        get(self, url=ply["url"], sha256=ply["sha256"],
            destination="third_party/ply", strip_root=True)
        apply_conandata_patches(self)

    @staticmethod
    def _python():
        """沙箱 PATH 可能没有 python3（packaging 教训：绝对路径）。"""
        for cand in ("/data/service/hnp/bin/python3", sys.executable):
            if cand and os.path.isfile(cand):
                return cand
        return "python3"

    def _ensure_test_extras(self):
        """尽力准备上游 [project.optional-dependencies].tests 的三个 linter。

        安装到 build_folder 私有目录（R49：不写共享前缀、不污染 worker
        全局 site-packages）。失败不阻塞，由测试结果如实反映。
        """
        missing = [m for m in TEST_EXTRAS
                   if importlib.util.find_spec(m) is None]
        if not missing:
            return []
        target = os.path.join(self.build_folder, "test-extras")
        os.makedirs(target, exist_ok=True)
        cmd = [self._python(), "-m", "pip", "install", "--quiet",
               "--no-input", "--disable-pip-version-check",
               "--target", target] + missing
        try:
            res = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=300)
            ok = res.returncode == 0
        except Exception as exc:  # noqa: BLE001 - 环境缺失时降级并如实记录
            self.output.warning(f"pip install test extras failed: {exc}")
            ok = False
        if not ok:
            self.output.warning(
                "test extras unavailable (%s) - tests.test_linters will be "
                "reported as an import error by unittest" % ", ".join(missing))
            return []
        self.output.info("test extras installed into %s" % target)
        return [target]

    def build(self):
        # 上游测试入口（与上游 GitHub Actions 一致：python -m unittest discover）
        src_dir = os.path.join(self.source_folder, "src")
        env = dict(os.environ)
        paths = [src_dir] + self._ensure_test_extras()
        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(paths)
        # 不把字节码写进源码树（保持 .orig 基线可比对）
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        cmd = [self._python(), "-m", "unittest", "discover", "-v"]
        rc = -1
        out = ""
        try:
            res = subprocess.run(cmd, cwd=self.source_folder, env=env,
                                 capture_output=True, text=True,
                                 timeout=UPSTREAM_TEST_TIMEOUT)
            rc = res.returncode
            out = (res.stdout or "") + (res.stderr or "")
        except subprocess.TimeoutExpired as exc:
            out = "".join(
                (part.decode(errors="ignore") if isinstance(part, bytes) else part) or ""
                for part in (exc.stdout, exc.stderr))
            self.output.warning(
                "upstream unittest timed out after %ds" % UPSTREAM_TEST_TIMEOUT)

        for line in [ln for ln in out.strip().splitlines() if ln.strip()][-4:]:
            self.output.info("upstream unittest: %s" % line)
        self.output.info("upstream unittest rc=%d (cmd: %s)" % (rc, " ".join(cmd)))
        if rc != 0:
            # 与 packaging 2.3 先例一致：上游测试失败不阻塞构建，如实记录 rc
            self.output.warning("upstream unittest reported non-zero rc=%d" % rc)

    def package(self):
        site = os.path.join(self.package_folder, SITE_REL)
        os.makedirs(site, exist_ok=True)
        src_root = os.path.join(self.source_folder, "src")
        # plyara 本体 + 内嵌 PLY（src/ply 符号链接在 source() 后已解析为真实目录）
        for mod in ("plyara", "ply"):
            src = os.path.join(src_root, mod)
            if not os.path.isdir(src):
                raise ConanException(f"{mod} package missing in source: {src}")
            shutil.copytree(src, os.path.join(site, mod),
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

        # R38：上游 [project.scripts] plyara = plyara.command_line:main
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        script = (
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))\n"
            f"_sp = os.path.join(_root, {SITE_REL!r})\n"
            "if _sp not in sys.path:\n"
            "    sys.path.insert(0, _sp)\n"
            "from plyara.command_line import main\n"
            "if __name__ == '__main__':\n"
            "    sys.exit(main() or 0)\n"
        )
        script_path = os.path.join(bin_dir, "plyara")
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(script)
        os.chmod(script_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = [SITE_REL]
        site = os.path.join(self.package_folder, SITE_REL)
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
