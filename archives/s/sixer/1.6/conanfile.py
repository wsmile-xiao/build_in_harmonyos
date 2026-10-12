from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout
import os
import sys


class SixerConan(ConanFile):
    name = "sixer"
    version = "1.6"
    description = "Python 2 至 Python 3 代码迁移命令行工具"
    license = "Apache-2.0"
    homepage = "https://github.com/haypo/sixer"
    url = "https://github.com/haypo/sixer"

    package_type = "application"
    # L0p 要求声明全部四项；package_id() 仍清空，纯 Python 包不按 ABI 重复。
    settings = "os", "compiler", "build_type", "arch"

    def package_id(self):
        self.info.clear()

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("sixer/1.6 is packaged for HarmonyOS only.")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def _fetch_sources(self):
        # codeload URL 末段是标签名，没有 .tar.gz 后缀，必须显式 filename。
        get(
            self,
            filename="sixer-1.6.tar.gz",
            destination=self.source_folder,
            strip_root=True,
            **self.conan_data["sources"][self.version],
        )

    def source(self):
        self._fetch_sources()

    def build(self):
        # create 偶发跳过 source()；关键源文件缺失时按同一 URL 再取一次。
        if not os.path.isfile(os.path.join(self.source_folder, "sixer.py")):
            self._fetch_sources()
        apply_conandata_patches(self)
        self.output.info(
            f"Python runtime: {sys.executable} ({sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro})"
        )
        self.run(
            f'"{sys.executable}" -Werror::SyntaxWarning -m py_compile sixer.py',
            cwd=self.source_folder,
        )
        self.run(
            f'"{sys.executable}" tests.py',
            cwd=self.source_folder,
        )

    def package(self):
        site_packages = os.path.join(
            self.package_folder, "lib", "python", "site-packages"
        )
        os.makedirs(site_packages, exist_ok=True)
        copy(self, "sixer.py", src=self.source_folder, dst=site_packages, keep_path=False)

        bin_directory = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_directory, exist_ok=True)
        launcher = os.path.join(bin_directory, "sixer")
        save(
            self,
            launcher,
            "#!/usr/bin/env python3\n"
            "from sixer import main\n\n"
            "if __name__ == '__main__':\n"
            "    main()\n",
        )
        os.chmod(launcher, 0o755)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        site_packages = os.path.join(
            self.package_folder, "lib", "python", "site-packages"
        )
        bin_path = os.path.join(self.package_folder, "bin")

        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.append_path("PYTHONPATH", site_packages)
        self.runenv_info.append_path("PATH", bin_path)
        self.buildenv_info.append_path("PYTHONPATH", site_packages)
        self.buildenv_info.append_path("PATH", bin_path)
