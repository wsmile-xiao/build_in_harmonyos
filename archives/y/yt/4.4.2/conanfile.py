#!/usr/bin/env python3
"""Conan recipe for yt 4.4.2 (OHOS aarch64).

yt (https://yt-project.org) is a Python toolkit for analysing astrophysical
simulation data.  Upstream ships 54 Cython extension sources (the wheel carries
53 compiled extension modules), but the HarmonyOS PC
community PyPI index publishes an official ``cp312-cp312-ohos_aarch64`` wheel,
so this recipe packages that prebuilt OHOS artifact instead of compiling the
Cython/numpy stack from source (rationale and evidence in notes.md).

Two platform adaptations are applied at packaging time:

1. **CPython extension suffix normalisation.**  The wheel is built against a
   CPython whose ``SOABI`` is ``cpython-312-aarch64-linux-ohos``, while the
   interpreter shipped in the image (HNP Python) reports
   ``EXTENSION_SUFFIXES == ['.cpython-312.so', '.abi3.so', '.so']``.  Extension
   modules are therefore renamed to the local ``EXT_SUFFIX`` after installation;
   without this step every compiled submodule fails to import.
2. **numpy cap.**  The only scipy available on the community index (1.14.1)
   requires ``numpy<2.3``, whereas the index resolves numpy to 2.5.x by
   default.  numpy is capped at ``<2.3`` so the platform stack stays coherent
   (2.2.6 is the newest version satisfying yt's ``numpy<3`` and scipy's cap).

The package is self-contained: yt and its whole runtime dependency closure live
under ``lib/python3.12/site-packages`` and ``bin/yt`` is a relocatable launcher,
so ``conan install yt/4.4.2`` yields a working ``yt`` CLI with no further
network access.
"""

import os
import re
import shlex
import shutil
import sys
import sysconfig

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches


# E212 的「加载器上下文」措辞：只有动态加载器（dlopen 阶段）才会打印这些词。
_E212_LOADER_CONTEXT = (
    "Error loading shared library",     # musl 加载器（OHOS/CI 实测措辞）
    "Error relocating",                 # musl 重定位失败，仍属 dlopen 阶段
    "cannot open shared object file",   # glibc 加载器措辞
)

# 与上述上下文**同现**才采信的 errno 后缀（用于区分 ENOENT「缺库」与
# EACCES「拒绝」）。
_E212_ERRNO_SUFFIXES = (": Permission denied", ": EACCES")


def _is_e212(text):
    """CI worker 的 hmmac 标签拒绝 dlopen 用户目录 .so（知识 E212/E502）。

    与 ELF 代码签名无关：即便 .so 已正确签名，沙箱仍报 Permission denied。

    判定采用**双条件同现**，二者缺一不成立：

    * 条件一（加载器上下文）：同一行含 :data:`_E212_LOADER_CONTEXT` 之一，
      证明这是 dlopen 阶段的加载失败，而非普通文件读写/目录遍历被拒。
    * 条件二（errno 后缀）：同一行含 ``: Permission denied`` 或 ``: EACCES``。

    只留条件二（旧实现）会**过宽**：真机上任何「权限类」缺陷（如包内数据文件
    模式位错误、构建期目录被拒）只要日志里出现裸 ``Permission denied``，就会被
    误判成 E212 而走静态回退，从而**把真实缺陷静默洗成 PASS**。
    反过来只留条件一也不够：真正「缺库」时加载器打印
    ``Error loading shared library <lib>: No such file or directory``（ENOENT），
    与 E212 共享该措辞，单看措辞会把「依赖缺失」误判为 E212。
    实测 CI 原文即两者同行：
    ``Error loading shared library <path>.so: Permission denied``。
    """
    for line in str(text).splitlines():
        if not any(ctx in line for ctx in _E212_LOADER_CONTEXT):
            continue
        if any(sfx in line for sfx in _E212_ERRNO_SUFFIXES):
            return True
    return False


class YtConan(ConanFile):
    name = "yt"
    version = "4.4.2"
    description = "yt 4.4.2 - astrophysical data analysis toolkit (Python; wraps the official OHOS aarch64 wheel)"
    license = "BSD-3-Clause"
    url = "https://github.com/yt-project/yt"
    homepage = "https://yt-project.org"
    topics = ("python", "astrophysics", "visualization", "harmonyos")
    package_type = "application"
    # 预编译 wheel 封装，无编译步骤。
    # L0p: CI 门禁要求 settings 四项齐全（compiler/build_type 仅参与 package_id）
    settings = "os", "compiler", "build_type", "arch"

    # CPython 扩展在 wheel 内使用完整平台 ABI 后缀（…-aarch64-linux-ohos.so），
    # 目标解释器只认 EXT_SUFFIX；仅在后缀与本机不一致时重命名。
    _OHOS_ABI_RE = re.compile(r"\.cpython-\d+-[^.]+\.so$")
    _COMMUNITY_INDEX = "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple"
    _PLATFORM_TAG = "ohos_aarch64"
    _NUMPY_CAP = "numpy<2.3"

    # ── helpers ──────────────────────────────────────────────────────────────

    @property
    def _python_tag(self):
        return "cp%d%d" % sys.version_info[:2]

    @property
    def _py_version(self):
        return "python%d.%d" % sys.version_info[:2]

    @property
    def _site_dir(self):
        return os.path.join("lib", self._py_version, "site-packages")

    @property
    def _wheel(self):
        """(file name, conandata entry) of the OHOS wheel to package."""
        name, src = next(iter(self.conan_data["sources"].items()))
        return name, src

    # ── steps ────────────────────────────────────────────────────────────────

    def export_sources(self):
        # conandata.yml 声明补丁时导出（当前适配路径无补丁，保持标准钩子）。
        export_conandata_patches(self)

    def source(self):
        name, src = self._wheel
        self.output.info("downloading OHOS wheel: %s" % name)
        download(self, url=src["url"],
                 filename=os.path.join(self.source_folder, name),
                 sha256=src.get("sha256"))

    def build(self):
        apply_conandata_patches(self)
        staging = os.path.join(self.build_folder, "staging")
        name, _ = self._wheel
        wheel = os.path.join(self.source_folder, name)
        if not os.path.isfile(wheel):
            raise ConanException("packaged wheel not found: %s" % wheel)

        self._pip_install(staging, [self._NUMPY_CAP, wheel])
        self._normalize_extension_suffixes(staging)
        self._sign_ohos_libraries(staging)
        self._self_check(staging)

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        site = os.path.join(self.package_folder, self._site_dir)
        os.makedirs(site, exist_ok=True)
        # bin/ 内是 pip 生成的入口脚本（shebang 指向构建机解释器 + 其它包的
        # 附带入参），不入包；仅重新生成自包含的 yt 启动器。
        copy(self, "*", src=staging, dst=site, excludes=["bin", "bin/*"])
        self._write_cli_wrapper()

    def package_info(self):
        site = os.path.join(self.package_folder, self._site_dir)
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        # 消费者 / test_package 通过 PYTHONPATH 找到 yt 与全部运行时依赖。
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info("yt PYTHONPATH: %s" % site)
        self.output.info("yt CLI: %s" % os.path.join(self.package_folder, "bin", "yt"))

    # ── implementation details ───────────────────────────────────────────────

    def _pip_install(self, target, requirements):
        """Install the OHOS wheels of yt + its runtime closure into `target`."""
        os.makedirs(target, exist_ok=True)
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--no-cache-dir", "--no-warn-script-location", "--disable-pip-version-check",
            # 交叉解析：只接受与本机 ABI 匹配或纯 Python 的 wheel。
            "--only-binary=:all:",
            "--platform", self._PLATFORM_TAG,
            "--python-version", "%d.%d" % sys.version_info[:2],
            "--implementation", "cp",
            "--abi", self._python_tag,
            "--target", target,
            "--index-url", self._COMMUNITY_INDEX,
            "--trusted-host", "pypi.cnb.cool",
        ]
        cmd.extend(requirements)
        self.output.info("pip install -> %s" % target)
        self.run(" ".join(shlex.quote(part) for part in cmd))

    def _normalize_extension_suffixes(self, root):
        """Rename *.cpython-<N>-<platform>.so to the local EXT_SUFFIX and fix perms."""
        ext_suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
        renamed = 0
        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in filenames:
                if not filename.endswith(".so"):
                    continue
                path = os.path.join(dirpath, filename)
                new_name = self._OHOS_ABI_RE.sub(ext_suffix, filename)
                if new_name != filename:
                    os.rename(path, os.path.join(dirpath, new_name))
                    path = os.path.join(dirpath, new_name)
                    renamed += 1
                os.chmod(path, 0o755)
        self.output.info("normalised %d extension module(s) to %s" % (renamed, ext_suffix))

    def _sign_ohos_libraries(self, root):
        """OHOS 只允许加载已代码签名的 ELF。

        设备侧工具链包装器会自动签名编译产物，但 CI worker 不会；轮子里的 .so
        由发行方签名，沙箱同样可能拒绝（实测 CI 报
        ``ImportError: Error loading shared library ..._multiarray_umath...so: Permission denied``，
        即 EACCES，而非缺符号/缺文件）。因此打包前用 SDK 的 binary-sign-tool
        重新自签名一遍（先剥掉既有 .codesign 段，避免重复签名导致校验失败）。
        与 archives/n/numpy/1.26.4 配方同一做法。
        """
        if str(self.settings.os) != "OHOS":
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy_tool = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign_tool):
            # 非设备环境（如纯 Linux 构建机）没有该工具，跳过而不是失败。
            self.output.warning("OHOS code signing skipped: %s not found" % sign_tool)
            return
        signed = 0
        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in filenames:
                if not (filename.endswith(".so") or ".so." in filename):
                    continue
                path = os.path.join(dirpath, filename)
                try:
                    if os.path.isfile(objcopy_tool):
                        # 已有 .codesign 段会让重复签名失败，先剥掉（缺段时非致命）。
                        self.run('"%s" --remove-section .codesign "%s"' % (objcopy_tool, path),
                                 ignore_errors=True)
                    self.run('"%s" sign -inFile "%s" -outFile "%s.signed" -selfSign 1'
                             % (sign_tool, path, path))
                    if not os.path.isfile(path + ".signed"):
                        raise ConanException("binary-sign-tool produced no output for %s" % path)
                    shutil.move(path + ".signed", path)
                    os.chmod(path, 0o755)
                    signed += 1
                except Exception as exc:
                    raise ConanException("OHOS code signing failed for %s: %s" % (path, exc))
        self.output.info("code-signed %d shared object(s) for OHOS" % signed)

    def _self_check(self, staging):
        """Fail the build early if the staged package cannot be imported.

        先在真实环境（真机/本地）上真正 `import yt`；CI worker 的任务域安全标签
        （hmmac）会拒绝对用户目录下任何 .so 的 dlopen，与 ELF 代码签名无关
        （知识条目 E212/E502），此时改为对 staging 内全部 .so 做静态 ELF/
        .codesign 校验并让 `conan create` 成功，而非报错；任何非 E212 的自检
        失败仍然抛错。仓库先例：archives/b/bpytop/1.0.68 test_package、
        archives/c/catfishq/1.4.0 `_verify_pysam_elf`、archives/a/aetos/2.0.0
        `run_upstream.py`。
        """
        import subprocess

        script = (
            "import yt, numpy\n"
            "print('SELFCHECK yt=' + yt.__version__ + ' numpy=' + numpy.__version__)\n"
            "assert yt.__version__ == '" + str(self.version) + "', yt.__version__\n"
        )
        env = dict(os.environ)
        old = env.get("PYTHONPATH")
        env["PYTHONPATH"] = staging + (os.pathsep + old if old else "")
        # 用 subprocess 捕获输出：conan 的 self.run 失败时抛出的异常不含
        # 子进程输出，无法据以识别 E212。
        proc = subprocess.run([sys.executable, "-c", script],
                              capture_output=True, text=True, env=env, timeout=600)
        if proc.returncode == 0:
            if proc.stdout:
                self.output.info(proc.stdout.rstrip())
            return
        stderr = proc.stderr or ""
        if _is_e212(stderr):
            # E212：CI hmmac 标签拒 dlopen 用户目录 .so，重签名无法修复。
            self.output.info(
                "yt/4.4.2: E212 fallback - CI hmmac denies dlopen of "
                "user-path .so (signing cannot fix); running static "
                "ELF/codesign verification")
            self._e212_static_verify(staging)
            return
        raise ConanException(
            "yt self-check (import yt) failed:\n%s"
            % ((proc.stdout or "") + stderr).strip())

    def _e212_static_verify(self, staging):
        """E212 fallback: 对 staging 内每个 .so 做静态 ELF/.codesign 校验。

        CI worker 的 hmmac 标签拒绝对用户目录 .so 的 dlopen，真实 import 无法
        进行；改查每个 .so 是否为合法 ELF 且含 .codesign 段（签名步骤已重新
        自签名）。零个 .so 视为包损坏；非 ELF 或缺 .codesign 段则失败——此时
        才抛错，否则打印 PASS 让 `conan create` 继续。
        """
        import subprocess

        sos = []
        for dirpath, _dirnames, filenames in os.walk(staging):
            for filename in filenames:
                # 与签名步骤 (filename.endswith(".so") or ".so." in filename)
                # 完全一致：凡是签名覆盖的 .so / versioned .so.* 都要静态校验。
                if filename.endswith(".so") or ".so." in filename:
                    sos.append(os.path.join(dirpath, filename))
        if not sos:
            raise ConanException(
                "E212 static verification: no .so found under %s "
                "(package is broken)" % staging)
        # 稳健探测工具：llvm-objdump（-h 打印节头，含 .codesign）优先，其次
        # 固定设备路径，最后 readelf；都缺失则退化为纯 Python 字节扫描。
        tool = (shutil.which("llvm-objdump")
                or ("/data/service/hnp/bin/llvm-objdump"
                    if os.path.isfile("/data/service/hnp/bin/llvm-objdump")
                    else None)
                or shutil.which("readelf"))
        # llvm-objdump 用 -h 即打印节头（含 .codesign）；readelf 的 -h 只打印
        # ELF 文件头、不列节，必须改用 -S 才会列出节，否则 .codesign 检测永远失败。
        tool_flag = "-S" if (tool and tool.endswith("readelf")) else "-h"
        checked = 0
        for path in sos:
            with open(path, "rb") as handle:
                if handle.read(4) != b"\x7fELF":
                    raise ConanException(
                        "E212 static verification: not ELF: %s" % path)
            signed = False
            if tool:
                try:
                    proc = subprocess.run([tool, tool_flag, path],
                                          capture_output=True, text=True,
                                          timeout=60)
                    signed = ".codesign" in proc.stdout
                except Exception:  # 工具不可用/超时：退回纯 Python 扫描
                    signed = False
            if not signed:
                # 工具缺失或输出不含节名时，补一次原始字节扫描作为兜底。
                with open(path, "rb") as handle:
                    signed = b".codesign" in handle.read()
            if not signed:
                raise ConanException(
                    "E212 static verification: %s lacks a .codesign section"
                    % path)
            checked += 1
        self.output.info(
            "yt/4.4.2: E212 static verification PASS - %d/%d shared objects "
            "are ELF with a .codesign section" % (checked, len(sos)))

    def _write_cli_wrapper(self):
        """Self-contained `yt` launcher (relative site-packages, no build paths)."""
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        cli = os.path.join(bin_dir, "yt")
        with open(cli, "w", encoding="utf-8") as handle:
            handle.write("#!/usr/bin/env python3\n")
            handle.write("import os\n")
            handle.write("import sys\n\n")
            handle.write("# 自包含启动器：以相对路径定位包内 site-packages。\n")
            handle.write("_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n")
            handle.write("_site = os.path.join(_root, 'lib', %r, 'site-packages')\n" % self._py_version)
            handle.write("if _site not in sys.path:\n")
            handle.write("    sys.path.insert(0, _site)\n\n")
            handle.write("from yt.utilities.command_line import run_main\n\n")
            handle.write("if __name__ == '__main__':\n")
            handle.write("    sys.exit(run_main())\n")
        os.chmod(cli, 0o755)
