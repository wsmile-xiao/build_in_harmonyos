#!/usr/bin/env python3
"""Conan recipe — markdown 1.0.1（Markdown→HTML 转换工具，纯 Perl）

Daring Fireball 官方 Markdown 工具：Markdown.pl 为纯 Perl 单文件脚本，
零第三方依赖（仅核心模块 Digest::MD5），OHOS 系统 perl 5.42 可用（R36 满足）。
无编译：直接安装 Markdown.pl 为 bin/markdown（Perl shebang 原样保留）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class MarkdownConan(ConanFile):
    name = "markdown"
    version = "1.0.1"
    description = "markdown — text-to-HTML conversion tool（Daring Fireball，纯 Perl）"
    license = "BSD-3-Clause"
    homepage = "https://daringfireball.net/projects/markdown/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # Debian orig tar.gz 顶层仅 markdown-1.0.1/，strip_root=True 后
        # Markdown.pl 直接在 source_folder 下（原 zip 源已弃用）
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 Perl 脚本，无编译；校验 perl 可用即可
        pass

    def package(self):
        src = self.source_folder
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        # Markdown.pl shebang 为 #!/usr/bin/perl，而 OHOS perl 在
        # /data/service/hnp/bin/perl → 读内容替换 shebang，写新文件+chmod
        # （写新文件+chmod 同时绕开 HMDFS copy 丢执行位）
        with open(os.path.join(src, "Markdown.pl"), "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("#!/usr/bin/perl", "#!/data/service/hnp/bin/perl", 1)
        for name in ("markdown", "Markdown.pl"):
            dst = os.path.join(bin_dst, name)
            with open(dst, "w", encoding="utf-8") as f:
                f.write(content)
            os.chmod(dst, 0o755)
        # License
        copy(self, "License.text", src=src,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
