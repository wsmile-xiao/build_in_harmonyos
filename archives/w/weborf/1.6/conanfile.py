import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, \
    get, load, replace_in_file, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps


class WeborfConan(ConanFile):
    name = "weborf"
    version = "1.6"
    description = ("Minimalist HTTP/1.1 web server written in C, with WebDAV, CGI "
                   "execution, TLS (openssl) and MIME detection (libmagic).")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/vsalvino/weborf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("http", "web-server", "webdav", "cgi", "cli")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游 configure 用裸 AC_CHECK_LIB 探测 magic/crypto/ssl；不挂依赖则 TLS 与
        # MIME 两条能力关死，上游 testsuite/site1https 与 site1mimetype 直接失败。
        self.requires("openssl/4.0.1")
        self.requires("libmagic/5.48")

    def build_requirements(self):
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        # build == source（刻意 in-source）：上游 TESTS 以 cwd 相对路径寻址——
        # testsuite/functions.sh 先 `cd $(dirname $0)`，再以 ../weborf 取被测二进制、
        # 以 site1/* 取语料。out-of-source 时 automake 在构建目录跑测试，这些相对
        # 路径全部落空。探针实测 in-source 形态下 15 条 TESTS 可真实执行。
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "conan_generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_flagdirs(self, ref_name, attr):
        dep = self.dependencies[ref_name]
        return [os.path.join(dep.package_folder, d) for d in getattr(dep.cpp_info, attr)]

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        for ref_name in ("openssl", "libmagic"):
            for d in self._dep_flagdirs(ref_name, "includedirs"):
                tc.extra_cflags.append("-I" + d)
            for d in self._dep_flagdirs(ref_name, "libdirs"):
                tc.extra_ldflags.append("-L" + d)
        tc.generate()

    def _magic_db(self):
        """定位 libmagic 制品里的 magic.mgc（静态 libmagic.a 不会自己找到它）。"""
        try:
            root = self.dependencies["libmagic"].package_folder
        except Exception:
            return None
        if not root:
            return None
        for base, _dirs, files in os.walk(root):
            if "magic.mgc" in files:
                return os.path.join(base, "magic.mgc")
        return None


    def _test_env(self):
        """上游 15 条 TESTS 是 shell 脚本起的本机 HTTP 测试，OHOS 上需三处环境注入。"""
        env = Environment()
        # 1) 断言工具与 shell：curl 在 ~/.harmonybrew/bin、bash 在 ~/usr/local/bin，
        #    两者都不在 conan/CI 的非交互 PATH 里；不注入则 13/15 条 curl 断言全废。
        bins = [os.path.expanduser(p) for p in
                ("~/.harmonybrew/bin", "~/usr/local/bin", "/usr/local/bin", "/usr/bin", "/bin")]
        env.prepend_path("PATH", [b for b in bins if os.path.isdir(b)])
        # 2) 被测二进制在构建目录里运行，需能找到 openssl/libmagic 的 .so。
        ld = []
        for ref_name in ("openssl", "libmagic"):
            ld += self._dep_flagdirs(ref_name, "libdirs")
        env.prepend_path("LD_LIBRARY_PATH", ld)
        # 3) testsuite/cgi 的 CGI 解释器：OHOS 无 /usr/bin/python3（E037/E049），
        #    由补丁暴露的 WEBORF_CGI_PYTHON 注入本机真实 python3。
        python3 = shutil.which("python3") or shutil.which("python")
        if python3:
            env.define("WEBORF_CGI_PYTHON", python3)
        # 4) 静态 libmagic.a 只认编译期写死的系统路径，须显式指到制品内的 magic.mgc，
        #    否则 mime_init() 卡住、weborf 根本不进 listen()（HTTP 与 HTTPS 都无响应）。
        mgc = self._magic_db()
        if mgc:
            env.define("MAGIC", mgc)
        return env

    def build(self):
        apply_conandata_patches(self)

        # E011 家族：HMDFS 上 (umask 077 && mktemp -d "./confXXXXXX") 产出 2700 目录，
        # 连属主都写不进 → config.status: could not setup config files machinery。
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure, "umask 077", "umask 022")

        autotools = Autotools(self)
        autotools.configure()
        config_status = os.path.join(self.build_folder, "config.status")
        if os.path.isfile(config_status):
            replace_in_file(self, config_status, "umask 077", "umask 022", strict=False)
        autotools.make()

        if not cross_building(self):
            with self._test_env().vars(self, scope="build").apply():
                autotools.make(target="check",
                             args=["-j1", "LOG_COMPILER=bash"])

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "weborf.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "man", "man1"))
        copy(self, "weborf.conf", src=self.source_folder,
             dst=os.path.join(self.package_folder, "conf"))
        # 静态 libmagic.a 只认编译期写死的系统数据库路径；把实际可用的 magic.mgc
        # 位置登记进本包，供运行期与 test_package 读取（避免依赖图未展开时取不到）。
        mgc = self._magic_db()
        if mgc:
            save(self, os.path.join(self.package_folder, "res", "magic.path"), mgc + "\n")

    def package_info(self):
        # 本包是 application（bin_PROGRAMS = weborf），不产出库与头。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        # 消费方（手工运行、test_package、conan run）同样需要 MAGIC，见 notes.md 已知限制
        marker = os.path.join(self.package_folder, "res", "magic.path")
        if os.path.isfile(marker):
            mgc = load(self, marker).strip()
            if mgc and os.path.isfile(mgc):
                self.runenv_info.define_path("MAGIC", mgc)
                self.buildenv_info.define_path("MAGIC", mgc)
