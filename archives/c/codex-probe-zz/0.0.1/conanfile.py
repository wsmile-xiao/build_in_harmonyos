from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches

import os
import sys


class CodexProbeZzConan(ConanFile):
    name = "codex-probe-zz"
    version = "0.0.1"
    description = (
        "OpenAI-compatible endpoint black-box purity audit CLI "
        "(pure Python, zero-dependency)"
    )
    license = "MIT"
    homepage = "https://github.com/leiMizzou/codex-probe"
    url = "https://github.com/leiMizzou/codex-probe"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # CI worker 无法直连 github.com（预下载 curl 缺失时镜像 fallback 会被还原），
        # 参照 archives/a/afdko/4.0.1 先例：官方 URL 优先，失败时探测 gh-proxy 镜像。
        data = self.conan_data["sources"][0]
        url = data["url"]
        sha256 = data["sha256"]
        candidates = [url]
        if url.startswith("https://github.com/"):
            candidates.insert(0, "https://gh-proxy.com/" + url)
        last_err = None
        for candidate in candidates:
            try:
                self.output.info("Downloading source from: " + candidate)
                get(self, candidate, sha256=sha256, strip_root=True)
                return
            except Exception as e:
                last_err = e
                self.output.warning("Download failed from {}: {}".format(candidate, e))
        raise ConanException("All source download candidates failed: {}".format(last_err))

    def build(self):
        apply_conandata_patches(self)
        # ── 层1: 上游官方测试套件 (docs/TEST_QUALITY_SPEC.md 必做) ──
        # 纯 Python 零依赖项目, 上游测试即 unittest discover;
        # monkey-patched urlopen, 无真实网络访问, 与平台无关。
        # `python -m` 会将 cwd (source_folder) 加入 sys.path, 模块导入无需 PYTHONPATH。
        tests_dir = os.path.join(self.source_folder, "tests")
        if os.path.isdir(tests_dir):
            self.run(
                '"{}" -m unittest discover -s tests -t . -v'.format(sys.executable),
                cwd=self.source_folder,
            )

    def package(self):
        src = self.source_folder
        lib_dir = os.path.join(self.package_folder, "lib")
        # CLI 入口与模块
        copy(self, "codex_probe.py", src=src, dst=lib_dir)
        copy(self, "provider_probe.py", src=src, dst=lib_dir)
        # 基线数据包
        copy(self, "*",
             src=os.path.join(src, "codex_probe_data"),
             dst=os.path.join(lib_dir, "codex_probe_data"))
        # 文档与许可证
        copy(self, "*.md", src=src,
             dst=os.path.join(self.package_folder, "share", "codex-probe-zz"),
             keep_path=False)
        copy(self, "LICENSE", src=src,
             dst=os.path.join(self.package_folder, "share", "codex-probe-zz"),
             keep_path=False)

    def package_info(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        self.runenv_info.prepend_path("PYTHONPATH", lib_dir)
        self.buildenv_info.prepend_path("PYTHONPATH", lib_dir)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["lib"]
