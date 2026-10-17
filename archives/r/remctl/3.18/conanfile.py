# remctl 3.18 —— 配方草稿（hw-7，2026-09-27）。未经验证，勿提审。见文末"待验证清单"。
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches, mkdir, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
import os

REQUIRED_KRB5 = "1.22.1"   # 1.22.2 在 remote 不存在（实测 Unable to find），只能 pin 1.22.1


class RemctlConan(ConanFile):
    name = "remctl"
    version = "3.18"
    description = "Remote authicated command execution environment (kerberized remote command runner)"
    license = "MIT"
    url = "https://www.eyrie.org/~eagle/software/remctl/"
    homepage = "https://www.eyrie.org/~eagle/software/remctl/"
    topics = ("kerberos", "gssapi", "remote-exec", "remctld")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if not self.options.shared:
            self.options.rm_safe("fPIC")
        # 上游 perl/php/python/ruby 绑定默认即关闭（build_perl/build_php/... 只在 --enable-* 时置 yes），无需 --disable

    def requirements(self):
        self.requires("krb5/" + REQUIRED_KRB5)      # RRA_LIB_GSSAPI / KRB5：client 与 server 都需要
        # libevent 只服务 server/remctld* —— 实测 Makefile.am:185 `client_libremctl_la_LIBADD`
        # 只含 util/portable + $(GSSAPI_LIBS) $(KRB5_LIBS)，且 client/*.c 里 event_* 出现 0 次。
        # 若按普通 requires 传播，消费者（test_package）会被 CMakeDeps 连上 libevent 的 .so，
        # 运行期报 Error loading shared library libevent-2.1.so.7（而 VirtualRunEnv 又按"运行期
        # 依赖"裁剪只带出 krb5 的 libdir，两边不一致 ⇒ 必红）。private=True 表达的就是
        # "本包构建/交付物需要，但不传播给 libremctl 的使用者"。
        # conan 2.29 的 requires() 没有 private= 这个关键字（实测 TypeError），等价表达是
        # visible=False（conan/internal/model/requires.py:10 的签名里有 visible，无 private）。
        self.requires("libevent/2.1.12", visible=False)
        # 不含 popt：官方 3.18 全树 grep -rl popt 零命中（候选登记写的"依赖=popt"是误记）

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("remctl 依赖 GSSAPI/KRB5 与 libevent，仅在 Linux/OHOS 路径验证")

    def export_sources(self):
        # G1 硬要求：必须有 export_sources() 方法，只有类属性 exports_sources 不算（实测报
        # "conanfile.py 缺少: export_sources() 方法"）。与 archives/r/rgb/1.1.1 同源写法。
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        # G1 要求显式的 export_sources() 方法（rgb 1.1.1 同源写法）；光有类属性
        # exports_sources = "patches/*" 不算，conan-verify 会以"缺少 export_sources() 方法"判 FAIL。
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], destination=self.source_folder, strip_root=True)

    def generate(self):
        # 顺序是硬要求（实测坐实）：conanbuild.sh 按"各脚本保存的先后"串接 source，而 profile
        # 的 [buildenv]（CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash）由 VirtualBuildEnv 写进
        # conanbuildenv-<id>.sh。若先存自己的路由脚本、后跑 VirtualBuildEnv，则 conanbuildenv
        # 排在最后把 /bin/sh 覆盖回 hnp bash，E386 复现（本窗 build-03 即此）。故必须先
        # VirtualBuildEnv(self).generate()，再存 e386 脚本，让它排在最后胜出。
        VirtualBuildEnv(self).generate()
        # E386：ci/conan/profiles/ohos-aarch64 的 [buildenv] 把 CONFIG_SHELL/SHELL 指向 hnp
        # bash，其在 HMDFS 下 getcwd() 必挂（实测活目录里也报 "Not supported"）=> configure
        # 报 "working directory cannot be determined"。profile 是框架件、配方 PR 不得改，
        # 故在 build 作用域把两者路由到 /bin/sh（本机 /bin/sh 的 getcwd 实测正常）。
        sh_env = Environment()
        sh_env.define("CONFIG_SHELL", "/bin/sh")
        sh_env.define("SHELL", "/bin/sh")
        sh_env.vars(self, scope="build").save_script("e386_shell_routing")
        # E386b（同族、不同根因）：make check 里 53 个测试集全部 ABORTED (exit status 127)。
        # 逐个实测坐实不是"未签名 ELF 不可执行"：直接 exec tests/portable/asprintf-t 打印的是
        #   Error loading shared library libkrb5.so.3 / libk5crypto.so.3 / libcom_err.so.3 /
        #   libkrb5support.so.0
        # 即 test 二进制是正常 ELF（dynamic /lib/ld-musl-aarch64.so.1），只是 conan 的
        # AutotoolsToolchain 只把依赖 libdir 做成 -L（链接期），不写 rpath，而 conanbuild 环境
        # 里也没有 LD_LIBRARY_PATH ⇒ 运行期解析不到。libevent 因 libtool 自动加了 -Wl,-rpath
        # 才没报。这里把 host 依赖的 lib 目录前置进 build 作用域的 LD_LIBRARY_PATH，
        # 只影响 build() 内的测试执行，不改交付产物的 rpath。
        # 必须排在 VirtualBuildEnv 之后（同上条顺序理由），且用 prepend_path 保住 profile
        # 里原有的 LD_LIBRARY_PATH（其中含 lld 需要的 libxml2.so.16 路径）。
        rt_env = Environment()
        for dep in ("krb5", "libevent"):
            # 不用 cpp_info.lib_paths：krb5 声明了 components，self.dependencies[dep].cpp_info
            # 在该形态下返回 _Component 对象，没有 lib_paths（实测 AttributeError 直接炸 generate）。
            # 两个依赖的实际目录都是 <package_folder>/lib（本次链接行里就是它），按存在性取用。
            libdir = os.path.join(self.dependencies[dep].package_folder, "lib")
            if os.path.isdir(libdir):
                rt_env.prepend_path("LD_LIBRARY_PATH", libdir)
        rt_env.vars(self, scope="build").save_script("test_runtime_lib_path")
        tc = AutotoolsToolchain(self)
        # E007 家族（实测定档，不走 OHC_SKILL_ROOT 那条路）：随包 build-aux/config.guess
        # timestamp='2022-01-09'，全文 grep OHOS/HarmonyOS **0 命中**，且它在自己 mktemp 出来
        # 的目录里写 dummy.c 被 HMDFS 权限挡（"can't create .../dummy.c: Permission denied"），
        # 最终 configure: error: cannot guess build type。框架的 patch-autotools-ohos.pl 在 CI
        # worker 上拿不到（REPO_ROOT 不 export，lksctp 已证），所以按经验汇总口径显式传交叉三元组：
        # build 侧给 gnu、host 侧给 ohos（两边都写 ohos 会被 config.sub 误判）。
        arch = "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
        tc.configure_args.append("--build=%s-unknown-linux-gnu" % arch)
        tc.configure_args.append("--host=%s-unknown-linux-ohos" % arch)
        # 依赖可见性：本包 configure 走 krb5-config / AC_SEARCH_LIBS（RRA_LIB_KRB5 /
        # RRA_LIB_GSSAPI / RRA_LIB_EVENT），不是 PKG_CHECK_MODULES，因此 PkgConfigDeps 生成的
        # krb5.pc/libevent.pc 对它无效；实测 conanautotoolstoolchain.sh 里不带任何依赖 -I/-L，
        # 于是 configure 连报 krb5.h no / for krb5_init_context in -lkrb5... no /
        # cannot find usable GSS-API library。按仓库既有写法（arb 2.9.0、4ti2 1.6.10、
        # alpine 2.26 同形态）把依赖的 package_folder 作为 --with-* 前缀显式喂给 configure。
        krb5_root = self.dependencies["krb5"].package_folder
        tc.configure_args.append("--with-krb5=%s" % krb5_root)
        tc.configure_args.append("--with-gssapi=%s" % krb5_root)
        tc.configure_args.append("--with-libevent=%s"
                                 % self.dependencies["libevent"].package_folder)
        # libevent 的 -I 还必须是全局的：上游 Makefile.am 只把 $(LIBEVENT_CPPFLAGS) 挂在
        # server_remctld / server_remctl_shell 两个目标上（224/239 行），而测试目标复用同一批
        # 源文件 SERVER_FILES（422 行，含 portable/event-extra.c）时不带这个变量，于是
        # `make check` 编到 tests 就首错：
        #   .../src/portable/event.h:23:14: fatal error: 'event2/buffer.h' file not found
        # 在 Linux 发行版上因为 libevent 头就在 /usr/include 而暴露不出来。这里把 -I/-L 提到
        # 全局编译标志，主件与测试件同口径，不改上游 Makefile.am（避免动测试面）。
        ev_root = self.dependencies["libevent"].package_folder
        tc.extra_cflags.append("-I" + os.path.join(ev_root, "include"))
        tc.extra_ldflags.append("-L" + os.path.join(ev_root, "lib"))
        # 选项集以随包 configure 实测为准（不是猜的）：可选依赖开关 = --with-gssapi /
        # --with-krb5 / --with-libevent / --with-pcre / --with-pcre2（各带 -include/-lib），
        # 绑定 --enable-perl|php|python|ruby 默认关闭。configure.ac 里 KRB5/GSSAPI 与
        # libevent(RRA_LIB_EVENT) 必需，PCRE2/PCRE 为 _OPTIONAL（缺则 server 少正则 ACL，不阻断）。
        # 因此这里不追加 --with-*，让 conan 的 pkg-config 与 env 正常被探测。
        tc.generate()
        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        apply_conandata_patches(self)
        # E114（HMDFS setgid + umask 077）：configure 自己建的安全临时目录在 HMDFS 上落成
        # drwx--S---，owner 反而写不进去，config.status 首错逐字：
        #   ./config.status[1035]: can't create ./conf52vraT/subs1.awk: Permission denied
        #   config.status: error: could not setup config files machinery
        # 处置按仓库既有写法（archives/4/4ti2/1.6.10 同源）在 build() 内就地改 configure 文本、
        # 保留真实临时目录创建（不删 mkdir，只去掉 umask 077 前缀），未命中时告警不静默。
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.exists(cfg) and self.settings.os == "OHOS":
            with open(cfg, "r", encoding="utf-8", errors="ignore") as handle:
                text = handle.read()
            pairs = [
                ('  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
                 '  test -d "$tmp"',
                 '  tmp="./conf$$-$RANDOM"\n'
                 '  (mkdir "$tmp" 2>/dev/null)\n'
                 '  test -d "$tmp"'),
                ('  (umask 077 && mkdir "$tmp")',
                 '  (mkdir "$tmp")'),
            ]
            hits = 0
            for old, new in pairs:
                if old in text:
                    text = text.replace(old, new)
                    hits += 1
            if hits:
                with open(cfg, "w", encoding="utf-8") as handle:
                    handle.write(text)
                self.output.info("E114: 已去掉 configure 里 %d 处 umask 077 包裹" % hits)
            else:
                self.output.warn("E114: umask 077 模式未命中（上游文本可能已变），"
                                 "config.status 可能仍被 setgid 临时目录挡住")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])
        # 测试前置（不是改测试，是补上游要求的输入）：server/acl/localgroup 调
        # kerberos_generate_conf("EXAMPLE.ORG") → tests/data/generate-krb5-conf 先
        # test_file_path("config/krb5.conf")，找不到就回退读 /etc/krb5.conf 与
        # /usr/local/etc/krb5.conf；本机三个全不存在 ⇒ 该脚本 exit 1，测试报
        # 'no krb5.conf found, see test instructions'，16/16 失败。上游 tests/Makefile.am
        # 的 check-local 本来就从 tests/config/ 取 keytab/principal，这个目录就是留给测试
        # 环境放前置件的（见 tests/README 与 ci/kdc-setup-*）。这里只写一份最小
        # [libdefaults] default_realm（generate-krb5-conf 会用 sed 把它改写成各测试要的
        # realm），不需要 KDC、不发任何票据：localgroup 的 16 条断言全是纯 ACL 逻辑。
        krb5_conf_dir = os.path.join(self.source_folder, "tests", "config")
        krb5_conf = os.path.join(krb5_conf_dir, "krb5.conf")
        if self.settings.os == "OHOS" and not os.path.exists(krb5_conf):
            mkdir(self, krb5_conf_dir)
            save(self, krb5_conf,
                 "[libdefaults]\n"
                 "\tdefault_realm = EXAMPLE.ORG\n"
                 "\ndisable_rdns = false\n\n"
                 "[realms]\n"
                 "\tEXAMPLE.ORG = {\n"
                 "\t\tkdc = localhost\n"
                 "\t\tadmin_server = localhost\n"
                 "\t}\n\n"
                 "[domain_realm]\n"
                 "\t. = EXAMPLE.ORG\n")
            self.output.info("测试前置：已生成 tests/config/krb5.conf（上游要求的最小 realm 配置）")
        # §10 上游测试真实执行：已核 Makefile.am:609 `check-local: $(check_PROGRAMS)` →
        # `tests/runtests -l '$(abs_top_srcdir)/tests/TESTS'`（57 个注册项：47 个 C + 10 个脚本），
        # 因此本包不是 lksctp 那种"只有 check_PROGRAMS 的静默零执行"。逐条 TAP 结果留进日志。
        # ⚠ 执行子集待真机核定：server/*、client/* 多数需 KDC 与 remctld，属"条件/资源未执行"档，
        #   须逐项 test_skipped 附技术原因，不得静默删用例或缩分母。
        autotools.make(target="check", args=["-j1"])

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 上游 Makefile.am:191 nodist_pkgconfig_DATA = client/libremctl.pc => 文件名为 libremctl.pc
        self.cpp_info.set_property("pkg_config_name", "libremctl")
        self.cpp_info.libs = ["remctl"]
        self.cpp_info.includedirs = ["include"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
