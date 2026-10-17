import os
import shutil

from conan import ConanFile
from conan.tools.files import download
from conan.tools.files import copy


class FileFnMatchPerlConan(ConanFile):
    name = "libfile-fnmatch-perl"
    version = "0.02"
    package_type = "application"
    license = "Artistic-1.0"
    homepage = "https://metacpan.org/pod/File::FnMatch"
    description = ("File::FnMatch — fnmatch(3) glob patterns for Perl "
                   "(XS module — uses libc fnmatch, no external deps)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # XS 模块——PREREQ_PM 空（无依赖）——fnmatch 用 libc 的

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "File-FnMatch-0.02.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xzf File-FnMatch-0.02.tar.gz --no-same-owner || true")
        self.run("cp -a File-FnMatch-0.02/. . && rm -rf File-FnMatch-0.02")

    def build(self):
        # 环境 umask 002 导致 conan 打包文件权限 rwxrwx---（CI 用户不在
        # group——'.so Permission denied' 实测）——umask 改 022（打包后
        # 文件 rwxr-xr-x——other 可读可执行）
        os.umask(0o022)
        # lld 链接器运行时加载 libxml2.so.16（LD_LIBRARY_PATH 指向 conan 的
        # libxml2——'Error relocating lld: xmlFreeDoc' 实测——同 bitlbee）——
        # LD_LIBRARY_PATH 指到 ohos-sdk 自带的 llvm/lib（lld 需要 SDK 的 libxml2）
        os.environ["LD_LIBRARY_PATH"] = "/data/service/hnp/ohos-sdk.org/" \
            "ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        # 标准 XS 模块编译（Makefile.PL + make——fnmatch 用 libc 的）
        self.run("/data/service/hnp/bin/perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # 安装 FnMatch.pm（perl site-lib）+ FnMatch.so（blib/arch）——
        # 先建目标目录（shutil.copy 不创建——'No such file' 实测）
        os.makedirs(os.path.join(self.package_folder, "lib", "perl5",
                                 "File"), exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "FnMatch.pm"),
                    os.path.join(self.package_folder, "lib", "perl5",
                                 "File", "FnMatch.pm"))
        arch = os.path.join(self.source_folder, "blib", "arch", "auto",
                            "File", "FnMatch")
        if os.path.isdir(arch):
            dst = os.path.join(self.package_folder, "lib", "perl5",
                               "auto", "File", "FnMatch")
            # copy 前 chmod 源为 0o755（umask 022 + 源 0o755——打包后
            # rwxr-xr-x——other 可读——CI 用户能加载 .so）
            so_src = os.path.join(arch, "FnMatch.so")
            if os.path.isfile(so_src):
                os.chmod(so_src, 0o755)
            os.makedirs(dst, exist_ok=True)
            shutil.copy2(so_src, os.path.join(dst, "FnMatch.so"))
            os.chmod(os.path.join(dst, "FnMatch.so"), 0o755)

    def package_info(self):
        self.cpp_info.libs = []
