from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class ClassadsConan(ConanFile):
    name = "classads"
    version = "1.0.10"
    description = "ClassAds - classified advertisement language and evaluation library from HTCondor"
    license = "Apache-2.0"
    url = "https://research.cs.wisc.edu/htcondor/classad/"
    homepage = "https://research.cs.wisc.edu/htcondor/classad/"
    topics = ("classad", "htcondor", "matching", "expression")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        exe = self.conf.get("tools.build:compiler_executables") or {}
        cc = exe.get("c", "clang")
        cxx = exe.get("cpp", "clang++")
        prefix = self.package_folder
        # 2013 年的 config.guess 不认识 uname -s 返回的 HarmonyOS；显式给 GNU
        # 三元组（config.sub 认识），编译器仍由 profile 的 compiler_executables
        # 指定为 OHOS clang，平台分支走 Linux（cityhash/1.1.1 先例同款）。
        # pcre 显式关闭：上游探测失败时回退 POSIX regex（musl 自带）。
        # 在源码目录原地 configure/make：conan 缓存 build-release 子目录在
        # HMDFS 上触发大面积 getcwd 失败（浅一层即正常）。
        shared_flag = "--enable-shared --disable-static" if self.options.shared \
            else "--disable-shared --enable-static"
        fpic = "-fPIC" if (not self.options.shared and self.options.fPIC) else ""
        # HMDFS 上 conan 以 cwd= 参数进入缓存目录后，子 shell 的 getcwd 间歇
        # 失败（job-working-directory 风暴导致 configure 内部文件操作错乱）。
        # 改为在正常工作目录启动 bash 后由 shell 内部 cd 进入（bash 按 PWD
        # 变量跟踪路径，绕开系统级 getcwd）。
        self.run(
            f'cd "{src}" && umask 000 && '
            f'CONFIG_SHELL=/bin/sh '
            f'CC={cc} CXX={cxx} '
            # OHOS SDK 26 的 libc++_shared.so 不导出 basic_string 的
            # ostream<< 显式实例化（_ZNSt4__n1lsIc...），-O2 下 libc++ 头的
            # extern template 声明把该符号抑制成 U 后链接必失败；关掉
            # extern template 让每个 TU 自带弱定义（实测验证）。
            f'CXXFLAGS="-O2 {fpic} -D_LIBCPP_DISABLE_EXTERN_TEMPLATE" '
            f'CFLAGS="-O2 {fpic}" '
            f"./configure --prefix={prefix} "
            f"--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu "
            f"{shared_flag} --with-pcre=no --disable-namespace --disable-dlopen-check "
            # 2011 libtool 不为 clang++ 补 C++ 运行库，链接测试程序缺
            # libc++ 符号（std::__n1 operator<< 等），以 make 变量补上。
            f"&& make -j1 LDFLAGS=-lc++"
        )

    def package(self):
        src = self.source_folder
        copy(self, "libclassad.so*", os.path.join(src, ".libs"),
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "libclassad.a", os.path.join(src, ".libs"),
             os.path.join(self.package_folder, "lib"), keep_path=False)
        # 头文件按上游 nobase_include_HEADERS 结构保留 classad/ 子目录
        copy(self, "classad/*.h", src,
             os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "LICENSE-2.0.txt", src,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "classads")
        self.cpp_info.set_property("pkg_config_name", "classads")
        self.cpp_info.libs = ["classad"]
