import os
from conan import ConanFile
from conan.tools.files import download, copy


class KernelHooksConan(ConanFile):
    name = "kernel-hooks"
    version = "0.3"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    no_copy_source = True

    def source(self):
        for src in self.conan_data["sources"]:
            download(self, url=src["url"], filename=src["filename"], sha256=src["sha256"])

    def package(self):
        # README 安装到 etc/kernel-hooks.d/
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "etc", "kernel-hooks.d"))
        # trigger 脚本安装到 share/kernel-hooks/ 并设置可执行权限
        dst_trigger = os.path.join(self.package_folder, "share", "kernel-hooks")
        copy(self, "kernel-hooks.trigger", src=self.source_folder, dst=dst_trigger)
        os.chmod(os.path.join(dst_trigger, "kernel-hooks.trigger"), 0o755)

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/kernel-hooks"]
