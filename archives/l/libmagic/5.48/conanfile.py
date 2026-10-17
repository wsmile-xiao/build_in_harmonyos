import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches

try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

import re
import json


class LibmagicConan(ConanFile):
    name = "libmagic"
    version = "5.48"
    description = "The file(1) command and libmagic library: identify file types from their signatures"
    license = "BSD-2-Clause"
    url = "https://gitcode.com/ffieldd22_-/build_in_harmonyos"
    homepage = "https://www.astron.com/pub/file/"
    topics = ("file", "libmagic", "file-type", "magic")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]
    exports_sources = "patches/*"

    def requirements(self):
        # 上游 5.48 的 83 个测试用例只依赖 magic 规则本身识别压缩格式
        # （tests/*.flags 不含 -z，check-local 不启用解压链路），
        # 且赛方 CI L0i 要求依赖必须已在 registry 发布——零依赖是硬约束。
        pass

    def source(self):
        from conan.tools.files import get
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # conan 2 默认把 source 复制进 build folder（日志 "Copying sources
        # to build folder"），源码树即 build folder 本身。
        pas = self.build_folder
        # HMFS: configure uses getcwd() which fails on symlink paths,
        # and umask 077 creates unwritable dirs. Patch both.
        # (与 lhasa 0.6.0 相同的仓库判例)
        self.run("sed -e 's/ac_pwd=`pwd`/ac_pwd=`echo \"$PWD\"`/g' "
                 "-e 's/umask 077/umask 0/g' -i configure",
                 cwd=pas, env="conanbuild")
        # Run configure with CONFIG_SHELL=/bin/sh (bash's getcwd() fails
        # on HMDFS symlink paths in the conan cache)
        # PATH 前置 hnp/bin：赛方 CI worker 的 PATH 不含 /data/service/hnp/bin，
        # clang 能被绝对路径调用但找不到同目录的 lld 链接器。
        # --host≠--build 进交叉模式：autoconf≥2.70 的 AC_PROG_CC 会运行测试程序，
        # 而赛方 CI 的 CONAN_HOME 在 .cache 下、HMFS 该路径禁止执行二进制，
        # 不加 --host 时「C compiler works」自检必失败（PR #6248 判例）。
        self.run("export PATH=/data/service/hnp/bin:$PATH && "
                 "CONFIG_SHELL=/bin/sh ./configure "
                 "--disable-shared --enable-static "
                 "--prefix=/ "
                 "--build=aarch64-unknown-linux-gnu "
                 "--host=aarch64-unknown-linux-musl "
                 "--disable-zlib --disable-bzlib --disable-xzlib "
                 "--disable-zstdlib --disable-lzlib --disable-lrziplib "
                 "--disable-libseccomp",
                 cwd=pas, env="conanbuild")
        # magic.mgc 由 file(1) 自身在构建期编译（magic/Makefile.am 的
        # FILE_COMPILE 规则）。交叉模式下上游默认用 PATH 上的系统 file，
        # 强制要求其版本与被构建版本一致。本机构建宿主是 HarmonyOS PC
        # （AArch64），构建出来的 target file(1) 可直接在宿主上运行：
        # 传带路径的 FILE_COMPILE 覆盖——路径含 '/' 时上游规则跳过版本
        # 检查，直接用刚构建出的同版本 target file(1) 编译 magic.mgc。
        # magic.mgc 本身是版本化二进制数据库、架构无关。
        self.run("export PATH=/data/service/hnp/bin:$PATH && "
                 "make -j1 FILE_COMPILE=$PWD/src/file",
                 cwd=pas, env="conanbuild")
        self._run_upstream_tests(pas)

    def _run_upstream_tests(self, pas):
        """跑上游 check-local 测试并输出 HMBS_UPSTREAM_TEST_RESULT。

        file 上游测试机制：tests/check-local 用刚链接好的 ./test 程序
        （链接 $(top_builddir)/src/libmagic.la）逐个比对 tests/*.testfile
        与 tests/*.result，MAGIC env 指向构建目录的 magic/magic.mgc。
        """
        buf = StringIO()
        try:
            self.run("export PATH=/data/service/hnp/bin:$PATH && make check",
                     cwd=pas, env="conanbuild",
                     stdout=buf, stderr=buf, ignore_errors=True)
        except Exception as exc:                     # noqa: BLE001
            buf.write("\nmake check raised: %s" % exc)
        out = buf.getvalue()

        # 失败时把差异倒进构建输出：check-local 比对失败的具体
        # result/expected 差异只在 stdout，没有单独 .log 文件可倒。
        print(out)

        # check-local 逐 testfile 打 "Running test: <name>"，全部跑完
        # 无 ERROR 即 pass。逐行统计，别把"解析不到"说成"没有测试"。
        total = len(re.findall(r"^Running test: ", out, re.M))
        failed = len(re.findall(r"^.*ERROR.*$", out, re.M))
        passed = total - failed
        status = "failed" if failed > 0 else ("passed" if total > 0 else "no_tests")
        result = {
            "status": status,
            "framework": "automake check-local (make check)",
            "command": "make check",
            "discovered": total,
            "executed": total,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "reason": ("conanfile.py build() 内执行上游 tests/ 的 check-local 套件："
                       "tests/ 下 83 个 *.testfile 由链接 $(top_builddir)/src/libmagic.la "
                       "的 ./test 程序逐个识别并与 *.result 比对，"
                       "MAGIC env 指向构建目录的 magic/magic.mgc"),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False),
              flush=True)
        if failed > 0:
            raise ConanInvalidConfiguration(
                "libmagic upstream tests failed: %d FAIL, %d PASS" % (failed, passed))

    def package(self):
        pas = self.build_folder
        self.run("export PATH=/data/service/hnp/bin:$PATH && "
                 "make install DESTDIR=" + self.package_folder,
                 cwd=pas, env="conanbuild")
        # pkg-config 文件里 libdir=/lib 是相对 prefix 的，conan 生态按
        # package_folder 绝对路径消费，改写为绝对路径。
        import glob
        for pc in glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")):
            with open(pc) as fh:
                content = fh.read()
            content = content.replace("libdir=/lib\n",
                                      "libdir=${pcfiledir}/..\n")
            with open(pc, "w") as fh:
                fh.write(content)

    def package_info(self):
        self.cpp_info.libs = ["magic"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libmagic")
        self.cpp_info.set_property("cmake_target_name", "libmagic::libmagic")
        self.cpp_info.set_property("pkg_config_name", "libmagic")
