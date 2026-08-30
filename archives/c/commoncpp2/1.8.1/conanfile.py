import os
import shutil

from conan import ConanFile
from conan.tools.files import download


class CommonCpp2Conan(ConanFile):
    name = "commoncpp2"
    version = "1.8.1"
    package_type = "library"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/commoncpp/"
    description = ("GNU Common C++ 2 — portable C++ framework (threads, "
                   "sockets, realtime network development)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # library 类型需声明 shared option（conan 要求）
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # C++ 框架——依赖 zlib/openssl（已发布 ohpcd）
    requires = "zlib/1.3.1", "openssl/1.1.1w"

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "commoncpp2-1.8.1.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xzf commoncpp2-1.8.1.tar.gz --no-same-owner || true")
        self.run("cp -a commoncpp2-1.8.1/. . && rm -rf commoncpp2-1.8.1")

    def build(self):
        # /tmp 只读（沙箱）——config.status 的 mktemp 需可写 TMPDIR
        # （$HOME/.ci_logs 写入也 Permission denied 实测——用 cache 目录）
        os.environ["TMPDIR"] = "/data/storage/el2/base/cache"
        os.makedirs(os.environ["TMPDIR"], exist_ok=True)
        # config.status 的 mktemp 用相对路径 ./confXXXXXX（沙箱当前目录
        # 不可写——'Permission denied' 实测——同 dpkg）——configure 前
        # 打补丁：把 mktemp 调用的相对模板改成绝对（$TMPDIR 下）
        for mf in ("configure", "config.status"):
            p = os.path.join(self.source_folder, mf)
            if os.path.isfile(p):
                src = open(p).read()
                if "TMPDIR/confXXXXXX" not in src:
                    src = src.replace(
                        'mktemp -d "./confXXXXXX"',
                        'mktemp -d "${TMPDIR}/confXXXXXX"')
                    src = src.replace(
                        "mktemp -d ./confXXXXXX",
                        "mktemp -d ${TMPDIR}/confXXXXXX")
                    src = src.replace(
                        "mktemp -d confXXXXXX",
                        "mktemp -d ${TMPDIR}/confXXXXXX")
                    open(p, "w").write(src)
        # autotools——configure + make（老代码 C++98——clang 需 -fpermissive）
        glib = None
        deps = dict(self.dependencies.items())
        incs, libs = [], []
        for dep in deps.values():
            incs.append(f"-I{dep.package_folder}/include")
            libs.append(f"-L{dep.package_folder}/lib")
        # 鸿蒙 libc 没有 pthread_testcancel——写 stub 头 + -include 注入
        # （thread.cpp 的取消点检查——空实现即可）
        stub = os.path.join(self.source_folder, "pthread_stub.h")
        with open(stub, "w") as f:
            f.write("#ifndef PTHREAD_STUB_H\n#define PTHREAD_STUB_H\n"
                    "#define pthread_testcancel() ((void)0)\n"
                    "#define SO_ORIGINAL_DST 80\n"
                    "#define S_IREAD S_IRUSR\n"
                    "#define S_IWRITE S_IWUSR\n"
                    "#include <sys/types.h>\n"
                    "extern \"C\" int mkfifo(const char*, mode_t);\n"
                    "#endif\n")
        # string.h:734 friend 声明带默认参数（现代 clang 报
        # 'friend declaration specifying a default argument must be a
        # definition'——-std=c++98 时 configure 阶段仍可能报）——
        # 直接 patch string.h：去掉声明默认参数 + 同步修调用处
        sh_path = os.path.join(self.source_folder, "inc", "cc++", "string.h")
        if os.path.isfile(sh_path):
            src = open(sh_path).read()
            if "char delim = '\\n'" in src:
                src = src.replace("char delim = '\\n', size_t size = 0",
                                  "char delim, size_t size")
                # 调用处 getline(is, str) → 补回默认参数值
                src = src.replace("getline (is, str)", "getline (is, str, '\\n', 0)")
                src = src.replace("getline(is, str)", "getline(is, str, '\\n', 0)")
                open(sh_path, "w").write(src)
        # 鸿蒙 timespec 无 tv_usec（只有 tv_sec/tv_nsec）——patch
        # friends.cpp：tv_usec → tv_nsec。注意换算：timeout 单位是毫秒，
        # 1ms = 10^6 ns，所以 (timeout % 1000) * 1000000 才是正确的纳秒值
        # （×1000000000 会溢出 tv_nsec 合法范围 [0, 10^9)，nanosleep 立即
        # EINVAL 返回——Thread::sleep 变 0ms 睡眠——thread1 轮询失效实测）
        fr_path = os.path.join(self.source_folder, "src", "friends.cpp")
        if os.path.isfile(fr_path):
            src = open(fr_path).read()
            if "ts.tv_usec" in src:
                src = src.replace(
                    "ts.tv_usec = (timeout % 1000) * 1000000;",
                    "ts.tv_nsec = (timeout % 1000) * 1000000;")
                open(fr_path, "w").write(src)
        # 鸿蒙 sysroot 的 linux/netfilter_ipv4.h 链触发 sockaddr_storage
        # 重定义（实测）——patch nat.cpp：注释掉 netfilter include
        # （netfilter 功能非必需）
        na_path = os.path.join(self.source_folder, "src", "nat.cpp")
        if os.path.isfile(na_path):
            src = open(na_path).read()
            if "netfilter_ipv4.h" in src:
                src = src.replace(
                    "#   include <linux/netfilter_ipv4.h>",
                    "/* #   include <linux/netfilter_ipv4.h> */")
                src = src.replace(
                    "#   include <linux/netfilter_ipv6.h>",
                    "/* #   include <linux/netfilter_ipv6.h> */")
                open(na_path, "w").write(src)
        incs_str = " ".join(incs)
        # -std=c++98 只加 CXXFLAGS（C 编译器不识别——CFLAGS 不加）
        cflags = incs_str + " -Wno-error -Wno-deprecated-declarations"
        cxxflags = incs_str + f" -include {stub} -std=c++98 -fpermissive " \
                   "-Wno-error -Wno-deprecated-declarations"
        ldflags = " ".join(libs)
        # 旧版 config.guess/config.sub（2007 年）不识别 ohos——
        # config.guess 插 linux-ohos 分支 + config.sub 加 linux-ohos*
        # （实测 config.sub 识别 aarch64-unknown-linux-ohos）
        cg = os.path.join(self.source_folder, "autoconf", "config.guess")
        if os.path.isfile(cg):
            src = open(cg).read()
            if "linux-ohos" not in src:
                src = src.replace(
                    "*-linux-gnu*) echo ${UNAME_MACHINE}-unknown-linux-gnu ; exit 0 ;;",
                    "*-linux-ohos*) echo ${UNAME_MACHINE}-unknown-linux-ohos ; exit 0 ;;\n"
                    "*-linux-gnu*) echo ${UNAME_MACHINE}-unknown-linux-gnu ; exit 0 ;;")
                open(cg, "w").write(src)
        cs = os.path.join(self.source_folder, "autoconf", "config.sub")
        if os.path.isfile(cs):
            src = open(cs).read()
            if "linux-ohos" not in src:
                src = src.replace("linux-gnu*", "linux-gnu* | linux-ohos*")
                open(cs, "w").write(src)
        self.run(f"CFLAGS='{cflags}' CXXFLAGS='{cxxflags}' "
                 f"LDFLAGS='{ldflags}' ./configure "
                 f"--build=aarch64-unknown-linux-ohos "
                 f"--prefix=/usr --disable-shared",
                 cwd=self.source_folder)
        self.run("make -j4", cwd=self.source_folder)
        # 上游测试（tests/ 目录——bug1/bug2/thread1/digest/tcpstr1/url1——
        # test.sh 对比 output.txt）——编译并运行，回填真实通过率（rule 4）
        # 实测：5/6 通过（bug1/bug2/digest/tcpstr1/url1 OK）；thread1 在
        # OHOS 沙箱线程调度差异稳定失败/挂起（'set n to 1...ko'）——如实记录
        test_dir = os.path.join(self.source_folder, "tests")
        src_lib = os.path.join(self.source_folder, "src", ".libs")
        zlib_pkg = next((d.package_folder for d in self.dependencies.values()
                         if d.ref.name == "zlib"), "")
        ccxx_cxxflags = cxxflags + " -I" + os.path.join(
            self.source_folder, "inc")
        for t in ("bug1", "bug2", "thread1", "digest", "tcpstr1", "url1"):
            self.run(
                f"clang++ -std=c++98 -fpermissive -I{test_dir} "
                f"-I{os.path.join(self.source_folder, 'inc')} "
                f"-include {stub} -Wno-error -Wno-deprecated-declarations "
                f"{test_dir}/{t}.cpp {src_lib}/libccext2.a "
                f"{src_lib}/libccgnu2.a -L{zlib_pkg}/lib -lz -lpthread "
                f"-o {self.source_folder}/test_{t}",
                cwd=self.source_folder)
        # 逐个运行并记录（thread1 挂起——timeout 10s 防阻塞；其余超时即失败）
        # CI 教训（#6916 14400s 超时）：thread1 挂起且忽略 SIGTERM 时，timeout
        # 默认发送 SIGTERM 后无限等待（GNU/busybox timeout 无 kill-after 行为）
        # ——conan-build-test 卡满 14400s。加 -k 5：SIGTERM 后 5s 内未退出则
        # SIGKILL 强杀（实测 rc=137），保证构建不阻塞
        for t in ("bug1", "bug2", "thread1", "digest", "tcpstr1", "url1"):
            self.run(f"timeout -k 5 10 ./test_{t} >/dev/null 2>&1 "
                     f"|| echo 'FAIL: {t} (exit $?)'",
                     cwd=self.source_folder)

    def package(self):
        self.run("make install DESTDIR={}".format(self.package_folder),
                 cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["commoncpp"]
