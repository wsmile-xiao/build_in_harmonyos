#!/usr/bin/env python3
"""Conan recipe — Asterisk 22.10.1（含 LDAP 支持）for HarmonyOS PC / OHOS aarch64.

平台适配要点：
- E114: HMDFS 上 `umask 077 && mktemp -d` 创建的 0700 目录不可写 →
  构建前 patch configure/config.status 为 umask 022 + TMPDIR。
- config.guess 无法识别 HarmonyOS → 显式 --build/--host 三元组。
- clang -fblocks 需要 BlocksRuntime（OHOS 无预编译）→ 配方内编译垫片库。
- E085: musl 不实现 pthread_cancel 线程取消族 → 垫片存根库 libohosshim。
- ASTMM_BLOCK 分配器陷阱宏污染 musl 系统头文件（sched.h）→ ASTMM_IGNORE 补丁。
- musl 无 glibc `_res` 全局解析器状态 → dns.c 返回空 nameserver 容器。
- make_xml_documentation 硬编码 /tmp（HMDFS 只读）→ TMPDIR。
"""
import os
import shlex
import shutil
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


required_conan_version = ">=2.0"

# clang -fblocks 运行时最小实现（仅覆盖本机执行所需的符号）
BLOCKS_RUNTIME_SHIM = textwrap.dedent("""\
    /* Minimal BlocksRuntime shim for OHOS musl (clang -fblocks support) */
    void *_NSConcreteGlobalBlock[32];
    void *_NSConcreteStackBlock[32];
    void *_NSConcreteMallocBlock[32];
    void *_NSConcreteAutoBlock[32];
    void *_NSConcreteFinalizingBlock[32];
    void *_NSConcreteWeakBlockVariable[32];

    void *_Block_copy(const void *src) { return (void *)src; }
    void _Block_release(const void *dst) { (void)dst; }

    /* clang -fblocks 的 RAII_VAR（__block 捕获）会为 block 字面量生成
       copy/dispose 辅助函数（__copy_helper_block_* / __destroy_helper_block_*），
       链接期引用 _Block_object_assign/_Block_object_dispose。本垫片与
       _Block_copy 的身份语义一致（block 从不被搬到堆上），故拷贝时仅搬运
       捕获槽指针、dispose 为空操作即可满足链接且不破坏运行期语义。 */
    void _Block_object_assign(void *dest, const void *object, const int flags) {
        (void)flags;
        *(const void **)dest = object;
    }
    void _Block_object_dispose(const void *object, const int flags) {
        (void)object;
        (void)flags;
    }
""")

# musl 不实现 POSIX 线程取消族（知识库 E085），提供存根避免链接失败；
# 调用方需自行用其他机制终止线程
PTHREAD_SHIM = textwrap.dedent("""\
    #include <pthread.h>
    #include <errno.h>

    int pthread_cancel(pthread_t thread) {
        (void)thread;
        return ENOSYS;
    }

    void pthread_testcancel(void) {
    }

    int pthread_setcancelstate(int state, int *oldstate) {
        if (oldstate) { *oldstate = PTHREAD_CANCEL_DISABLE; }
        (void)state;
        return 0;
    }

    int pthread_setcanceltype(int type, int *oldtype) {
        if (oldtype) { *oldtype = PTHREAD_CANCEL_DEFERRED; }
        (void)type;
        return 0;
    }
""")


class AsteriskConan(ConanFile):
    name = "asterisk"
    version = "22.10.1"
    description = "Asterisk open source PBX with LDAP directory support (res_config_ldap)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.asterisk.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    # 上游 in-tree 测试用例（tests/test_*.c，即 `/main/...`、`/res/...` 用例）
    # 全部声明 `<depend>TEST_FRAMEWORK</depend>`。默认关闭以保持交付制品的
    # 模块集合不变；需要执行上游用例时用
    # `-o asterisk/*:with_test_framework=True` 打开。
    options = {"with_test_framework": [True, False]}
    default_options = {"with_test_framework": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} 仅适配 Linux/OHOS 平台，当前 os={self.settings.os}")

    def requirements(self):
        self.requires("openldap/2.6.7")
        self.requires("libedit/20240808")
        self.requires("uuid/2.40.1")
        self.requires("jansson/2.15.1")
        self.requires("libxml2/2.15.3")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @property
    def _shim_dir(self):
        # The OHOS Makefile patch resolves this directory relative to
        # ASTTOPDIR, so keep generated libraries in the source tree.
        d = os.path.join(self.source_folder, "ohos-shim")
        os.makedirs(d, exist_ok=True)
        return d

    @property
    def _pc_dir(self):
        d = os.path.join(self.build_folder, "gen-pkgconfig")
        os.makedirs(d, exist_ok=True)
        return d

    def _compiler_executable(self, key, default_name, default_path):
        """Return a usable compiler while preserving profile precedence.

        Some workers publish a profile with an HNP path that is absent from the
        current device image but expose the same tool from the user prefix.
        Resolve that case locally in the recipe instead of changing the shared
        profile.
        """
        executables = self.conf.get("tools.build:compiler_executables") or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        if configured:
            resolved = shutil.which(os.path.basename(configured))
            if resolved:
                return resolved
        return shutil.which(default_name) or default_path

    @property
    def _clang(self):
        return self._compiler_executable("c", "clang", "/data/service/hnp/bin/clang")

    @property
    def _clangxx(self):
        return self._compiler_executable("cpp", "clang++", "/data/service/hnp/bin/clang++")

    @property
    def _shell(self):
        return shutil.which("bash") or shutil.which("sh") or "/bin/sh"

    def _dep_libdirs(self):
        """所有参与链接/运行的依赖库目录（垫片 + 各 host 依赖 libdirs）。

        conan 2.x 中 dependencies[].cpp_info.libdirs 为绝对路径（已按
        package_folder 解析），CI 与本地缓存路径不同也无碍——rpath 与 -L
        始终使用动态计算值，绝不硬编码。
        """
        libdirs = [self._shim_dir]
        for name in ("libedit", "uuid", "jansson", "libxml2", "sqlite3"):
            libdirs.extend(self.dependencies[name].cpp_info.libdirs)
        libdirs.extend(self.dependencies["openldap"].cpp_info.libdirs)
        return libdirs

    def generate(self):
        tc = AutotoolsToolchain(self)
        triplet = "aarch64-unknown-linux-gnu"
        ld = self.dependencies["openldap"]
        tc.configure_args.extend([
            f"--build={triplet}",
            f"--host={triplet}",
            f"--with-ldap={ld.package_folder}",
            "--without-pjproject",
            "--without-x11",
            "--without-gtk2",
        ])
        # configure 探测与链接需要 -L 指向各依赖库目录 + 垫片库目录
        libdirs = self._dep_libdirs()
        incdirs = []
        for name in ("libedit", "uuid", "jansson", "libxml2", "sqlite3"):
            dep = self.dependencies[name]
            incdirs.extend(dep.cpp_info.includedirs)
        incdirs.extend(ld.cpp_info.includedirs)
        for d in libdirs:
            tc.extra_ldflags.append(f"-L{d}")
        # PR#7656 修复：不再以 buildenv 全局注入 LD_LIBRARY_PATH（那会把 conan
        # 目标侧 libxml2.so.16 塞进宿主工具链进程的库搜索路径，导致 SDK 的 lld
        # 重定位 xmlFreeDoc 等 18 个符号失败）。改为把依赖库目录以 -Wl,-rpath
        # 内嵌进目标侧二进制（menuselect 等），运行期加载器按 RUNPATH 即可找到
        # conan 动态库；宿主 clang/lld 不受任何 LD_LIBRARY_PATH 污染。
        tc.extra_ldflags.append("-Wl,-rpath," + ":".join(libdirs))
        for d in incdirs:
            tc.extra_cflags.append(f"-I{d}")
        # 真机 clang wrapper 为链接阶段固定追加 --code-sign；在 configure
        # 的 -c 属性探测中该参数会触发 -Werror。只抑制此参数的未使用警告，
        # 不移除链接阶段的签名参数，产物仍由 package() 统一签名。
        if str(self.settings.os) == "OHOS":
            # Keep platform choices in the profile/recipe.  The source patches
            # use these capability/configuration macros so they remain
            # portable and do not key behavior on a vendor platform macro.
            tc.extra_cflags.extend([
                "-DAST_LOCK_TYPE_DEFAULT=AST_LOCK_TYPE_FLOCK",
                "-DAST_USE_ABSTRACT_SOCKET=1",
                # musl 没有可递归的静态互斥量初始值
                # （PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP 不可用），
                # Asterisk 的静态 mutex 会退化成普通 mutex，loader 在
                # module_list 上自死锁（启动停在 "Asterisk Dynamic Loader
                # Starting:"，module show 阻塞、用例只注册内置的 8 条）。
                # 该能力开关使 lock.h 走构造函数初始化（上游 SOLARIS/BSD 路径），
                # ast_mutex_init 会按 AST_MUTEX_KIND=PTHREAD_MUTEX_RECURSIVE 建锁。
                "-DAST_USE_MUTEX_CONSTRUCTOR_INIT=1",
            ])
            tc.extra_cflags.append("-Wno-unused-command-line-argument")
        # Override stale profile paths only when the recipe resolved a usable
        # compiler; shared ci/ profiles remain unchanged.
        tc_env = tc.environment()
        tc_env.define("CC", self._clang)
        tc_env.define("CXX", self._clangxx)
        tc.generate(env=tc_env)

        # .pc 垫片：asterisk 强制要求 pkg-config 找到 libedit 与 libxml2
        libedit = self.dependencies["libedit"]
        self._write_pc("libedit", libedit, ["-ledit"])
        xml2 = self.dependencies["libxml2"]
        self._write_pc("libxml-2.0", xml2, ["-lxml2"],
                       extra_cflags=["-I" + p for p in xml2.cpp_info.includedirs])
        pkg_config = os.path.join(self._pc_dir, "ohos-pkg-config")
        self._write_pkg_config_shim(pkg_config, libedit, xml2)

        buildenv = self.buildenv
        # The shared profile can point at an HNP bash absent from a device
        # image; configure only needs a usable POSIX shell.
        buildenv.define("CONFIG_SHELL", self._shell)
        buildenv.define("SHELL", self._shell)
        buildenv.define("PKG_CONFIG_PATH", self._pc_dir)
        buildenv.define("PKG_CONFIG", pkg_config)
        # 真机工具链未提供 pkg-config。Asterisk 的 libedit fallback 会无条件
        # 追加 HarmonyOS 不存在的 -ltermcap；使用 configure 官方 override
        # 变量直接提供 Conan 依赖，避免误入该 fallback。
        buildenv.define(
            "LIBEDIT_CFLAGS",
            " ".join(f"-I{d}" for d in libedit.cpp_info.includedirs),
        )
        buildenv.define(
            "LIBEDIT_LIBS",
            " ".join([
                *(f"-L{d}" for d in libedit.cpp_info.libdirs),
                "-ledit",
            ]),
        )
        # menuselect 的 libxml2 检测同样优先读取 configure override；真机
        # 没有 pkg-config/xml2-config 时，显式传 Conan 路径才能保留该依赖。
        buildenv.define(
            "LIBXML2_CFLAGS",
            " ".join(f"-I{d}" for d in xml2.cpp_info.includedirs),
        )
        buildenv.define(
            "LIBXML2_LIBS",
            " ".join([
                *(f"-L{d}" for d in xml2.cpp_info.libdirs),
                "-lxml2",
            ]),
        )
        # menuselect 编译行需要 libxml2 头文件路径（patch 0007）
        buildenv.define("OHOS_XML2_INCDIR",
                        os.path.join(xml2.cpp_info.includedirs[0], "libxml2"))
        # configure 中 LDAP 检查为 LIBS="-lldap ${pbxlibdir} $LIBS" 仅 -lldap，
        # 而 libldap.so NEEDED liblber.so.2；openldap package_info 为 components
        # ldap→lber，若初始 LIBS 不含 -llber 则需靠 DT_NEEDED 链间接解析，
        # 在 -L 顺序/Transient LLD 干扰下可能误判为缺 LDAP。显式追加 -llber
        # 使检查行变为 "-lldap -L... -llber"，与 pkg-config Requires: lber 一致。
        runtime_libs = (
            f"-L{self._shim_dir} -Wl,-rpath,{self._shim_dir} "
            "-lBlocksRuntime -lohosshim -luuid"
        )
        buildenv.define("LIBS", f"{runtime_libs} -llber")
        # Module link rules do not consume the main program's AST_LIBS.
        buildenv.define("OHOS_MODULE_LIBS", runtime_libs)
        # 链接期库搜索路径（仅影响 clang driver 的 -l 解析，不作用于运行期
        # 动态加载器，因此不会污染宿主 lld）：让裸 ${CC} 的 -fblocks 探测
        # 找到垫片库 libBlocksRuntime.so
        buildenv.define("LIBRARY_PATH", ":".join(libdirs))
        # PR#7656 第二轮：menuselect 的链接不由顶层 makeopts 的 LDFLAGS 控制，
        # 而是顶层 Makefile 的 MAKE_MENUSELECT 显式传 LDFLAGS="$(BUILD_LDFLAGS)"，
        # 该变量在 Makefile 中从未赋值 → menuselect 二进制不带任何 RUNPATH，
        # 运行期加载器找不到 conan libxml2.so.16，`menuselect --check-deps`
        # 直接报 xml* symbol not found（CI BUILD41895）。把同一个
        # -Wl,-rpath 经 BUILD_LDFLAGS 注入，使 menuselect 内嵌 RUNPATH；
        # 不影响宿主 clang/lld（仅作用于 menuselect 子 make 的链接命令行）。
        buildenv.define("BUILD_LDFLAGS", "-Wl,-rpath," + ":".join(libdirs))

    def _write_pc(self, name, dep, libs, extra_cflags=None):
        content = "\n".join([
            f"prefix={dep.package_folder}",
            "exec_prefix=${prefix}",
            f"libdir=${{prefix}}/{os.path.relpath(dep.cpp_info.libdirs[0], dep.package_folder)}",
            f"includedir=${{prefix}}/{os.path.relpath(dep.cpp_info.includedirs[0], dep.package_folder)}",
            "",
            f"Name: {name}",
            f"Description: {name} (conan package shim)",
            f"Version: {dep.ref.version}",
            f"Libs: -L${{libdir}} {' '.join(libs)}",
            f"Cflags: -I${{includedir}} {' '.join(extra_cflags or [])}",
        ]) + "\n"
        with open(os.path.join(self._pc_dir, f"{name}.pc"), "w") as handle:
            handle.write(content)

    def _write_pkg_config_shim(self, path, libedit, xml2):
        """Provide the small pkg-config interface required by menuselect.

        The device image has no pkg-config, while menuselect treats its
        presence as mandatory.  Keep the shim limited to Conan dependencies;
        unknown packages remain unavailable and use Asterisk fallbacks.
        """
        edit_cflags = " ".join(f"-I{d}" for d in libedit.cpp_info.includedirs)
        edit_libs = " ".join([
            *(f"-L{d}" for d in libedit.cpp_info.libdirs),
            "-ledit",
        ])
        xml_cflags = " ".join(f"-I{d}" for d in xml2.cpp_info.includedirs)
        xml_libs = " ".join([
            *(f"-L{d}" for d in xml2.cpp_info.libdirs),
            "-lxml2",
        ])
        script = textwrap.dedent(f"""\
            #!/bin/sh
            set -u
            edit_cflags={shlex.quote(edit_cflags)}
            edit_libs={shlex.quote(edit_libs)}
            xml_cflags={shlex.quote(xml_cflags)}
            xml_libs={shlex.quote(xml_libs)}
            package=
            for arg in "$@"; do
                case "$arg" in
                    -*) ;;
                    *) package="$arg" ;;
                esac
            done
            case "$1" in
                --atleast-pkgconfig-version|--version)
                    exit 0
                    ;;
                --exists)
                    case "$package" in
                        libedit*|libxml-2.0*) exit 0 ;;
                    esac
                    exit 1
                    ;;
                --cflags)
                    case "$package" in
                        libedit*) printf '%s\\n' "$edit_cflags"; exit 0 ;;
                        libxml-2.0*) printf '%s\\n' "$xml_cflags"; exit 0 ;;
                    esac
                    ;;
                --libs)
                    case "$package" in
                        libedit*) printf '%s\\n' "$edit_libs"; exit 0 ;;
                        libxml-2.0*) printf '%s\\n' "$xml_libs"; exit 0 ;;
                    esac
                    ;;
            esac
            exit 1
        """)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(script)
        os.chmod(path, 0o755)

    def _patch_configure_tmpdir(self):
        """E114：umask 077 动态临时目录不可写 → umask 022 + TMPDIR。"""
        replacements = {
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&':
                'tmp=`(umask 022 && mktemp -d "${TMPDIR:-.}/confXXXXXX") 2>/dev/null` &&',
            'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")':
                'tmp="${TMPDIR:-.}"/conf$$-$RANDOM\n  (umask 022 && mkdir -p "$tmp")',
            '"cannot create a temporary directory in ."':
                '"cannot create a temporary directory"',
        }
        for script in ("configure", os.path.join("menuselect", "configure")):
            path = os.path.join(self.source_folder, script)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            changed = False
            for old_text, new_text in replacements.items():
                if old_text in content:
                    content = content.replace(old_text, new_text)
                    changed = True
            if changed:
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(content)
                os.chmod(path, 0o755)
                self.output.info(f"Patched {script}: umask 077→022")

    def _build_shims(self):
        """在 configure 之前编译垫片库（BlocksRuntime + pthread 取消族存根）。"""
        shim = self._shim_dir
        blocks_c = os.path.join(shim, "blocksruntime.c")
        pthread_c = os.path.join(shim, "pthread_shim.c")
        with open(blocks_c, "w") as handle:
            handle.write(BLOCKS_RUNTIME_SHIM)
        with open(pthread_c, "w") as handle:
            handle.write(PTHREAD_SHIM)
        clang = self._clang
        self.run(f'"{clang}" -shared -fPIC -o "{shim}/libBlocksRuntime.so" "{blocks_c}"')
        self.run(f'"{clang}" -shared -fPIC -o "{shim}/libohosshim.so" "{pthread_c}"')

    def _link_dep_headers(self):
        """主源码树 include/ 缺少依赖头文件搜索路径（asterisk 的 Makefile
        不传播 CPPFLAGS 到所有子目标），按探索验证过的方式建立符号链接。"""
        include_dir = os.path.join(self.source_folder, "include")
        links = [
            ("sqlite3", "sqlite3.h"),
            ("jansson", "jansson.h"),
            ("jansson", "jansson_config.h"),
            ("libedit", "histedit.h"),
        ]
        for dep_name, header in links:
            src = os.path.join(self.dependencies[dep_name].cpp_info.includedirs[0], header)
            dst = os.path.join(include_dir, header)
            if os.path.lexists(dst):
                os.remove(dst)
            os.symlink(src, dst)
        uuid_inc = self.dependencies["uuid"].cpp_info.includedirs[0]
        dst = os.path.join(include_dir, "uuid")
        if not os.path.lexists(dst):
            os.symlink(os.path.join(uuid_inc, "uuid"), dst)

    def _run_configure_with_retry(self, cmd, cwd, attempts=5):
        """ld.lld 在高并发下偶发 `Interrupted system call`（EINTR），
        asterisk configure 中 ldap_initialize 检查会因链接器被信号打断而误判
        为缺 LDAP。本方法对含该特征的失败做指数退避重试，避免单次瞬时失败即判废。"""
        import time
        delay = 2
        last_exc = None
        for attempt in range(1, attempts + 1):
            try:
                self.run(cmd, cwd=cwd)
                if attempt > 1:
                    self.output.info(f"configure succeeded on attempt {attempt}/{attempts}")
                return
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                msg = str(exc)
                # 优先用本次 build 目录的 config.log 做瞬时错误判定；fallback 查历史 build
                transient = False
                try:
                    import glob as _glob
                    candidates = _glob.glob(os.path.join(self.build_folder or cwd, "**", "config.log"), recursive=True)
                    candidates += _glob.glob(os.path.join(cwd, "config.log"))
                    cfg = None
                    # 取最新修改的 config.log
                    if candidates:
                        candidates = sorted(candidates, key=lambda p: os.path.getmtime(p), reverse=True)
                        cfg = candidates[0]
                        if os.path.isfile(cfg):
                            with open(cfg, "r", errors="ignore") as handle:
                                tail = handle.read()[-20000:]
                            if "Interrupted system call" in tail and "ldap_initialize" in tail:
                                transient = True
                except Exception:  # noqa: BLE001
                    pass
                if "Interrupted system call" in msg:
                    transient = True
                is_transient = transient and attempt < attempts
                if is_transient:
                    self.output.warning(
                        f"configure transient failure (Interrupted system call) "
                        f"attempt {attempt}/{attempts}, retry in {delay}s: {msg[:400]}"
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, 20)
                    continue
                raise
        if last_exc is not None:
            raise last_exc

    def build(self):
        apply_conandata_patches(self)
        self._patch_configure_tmpdir()
        self._build_shims()
        self._link_dep_headers()
        src = self.source_folder
        # asterisk 的 configure/menuselect 依赖源码内相对路径
        # （third-party/versions.mak 等），必须 in-source 构建
        args = " ".join(f'"{a}"' for a in self._configure_args())
        self._run_configure_with_retry(f"./configure {args}", cwd=src)
        # 主 make 会按需重新生成 menuselect/makeopts，其调用的
        # menuselect/configure 不带 --build，config.guess 无法识别 HarmonyOS；
        # 预先配置好使 make 跳过该步骤（libxml2 检测走 buildenv 的
        # PKG_CONFIG_PATH）
        margs = " ".join(f'"{a}"' for a in [
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
        ])
        self.run(f"./configure {margs}", cwd=os.path.join(src, "menuselect"))
        # CI #36928：menuselect 二进制编译链接成功，但运行期加载器找不到 conan
        # libxml2.so.16（Error 127）。顶层 Makefile 的 MAKE_MENUSELECT 规则
        # 用 LDFLAGS="$(BUILD_LDFLAGS)" 链接 menuselect，而该变量在 Makefile
        # 中从未赋值；仅靠 buildenv 环境变量→make 变量的隐式导入在 CI 全新
        # 构建下不保证生效。这里用三重确定性通道，确保 rpath 一定进入 menuselect：
        #   1) 把 rpath 直接写进 menuselect/makeopts 的 OHOS_MENUSELECT_LDFLAGS
        #      （menuselect/Makefile include 该文件，链接行追加该变量，见
        #      patch 0008）；不依赖任何环境变量传递。
        #   2) 顶层 make 命令行显式传 BUILD_LDFLAGS（make 命令行变量优先级
        #      最高，必然被子 make 的 $(BUILD_LDFLAGS) 引用）。
        #   3) generate() 里 buildenv 注入 BUILD_LDFLAGS 保留兜底。
        rpath = "-Wl,-rpath," + ":".join(self._dep_libdirs())
        menuselect_makeopts = os.path.join(src, "menuselect", "makeopts")
        if os.path.isfile(menuselect_makeopts):
            with open(menuselect_makeopts, "a", encoding="utf-8") as handle:
                handle.write(f"\nOHOS_MENUSELECT_LDFLAGS = {rpath}\n")
        if self.options.with_test_framework:
            self._enable_test_framework(src, rpath)
        make_cmd = f"make --jobserver-style=pipe -j4 'BUILD_LDFLAGS={rpath}'"
        if self.options.with_test_framework:
            # 主构建关闭 dev-mode 的严格告警（-Werror/-Wunused/-Wundef，
            # Makefile L211），只保留 menuselect 的选择结果。
            make_cmd += " 'AST_DEVMODE=' 'DISABLE_XMLDOC=yes'"
        self.run(make_cmd, cwd=src)

    def _strip_makeopts_dev_mode(self, src):
        """把 AST_DEVMODE 从 makeopts 中去掉。

        `build_tools/make_buildopts_h` 直接 grep `makeopts` 决定是否写
        `#define AST_DEVMODE 1`，而 `include/asterisk/logger.h` 的 SCOPE_* 宏在
        dev-mode 下走 GCC 嵌套函数实现，clang 会直接编译失败
        （`tests/test_scope_trace.c`: illegal storage class on function）。
        因此主构建必须在没有 AST_DEVMODE 的前提下进行。
        """
        makeopts = os.path.join(src, "makeopts")
        if not os.path.isfile(makeopts):
            return False
        with open(makeopts, encoding="utf-8") as handle:
            lines = handle.readlines()
        kept = [
            line for line in lines
            if not line.startswith(("AST_DEVMODE=yes", "AST_DEVMODE_STRICT="))
        ]
        if kept == lines:
            return False
        with open(makeopts, "w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(kept)
        return True

    def _drop_dev_mode_artifacts(self, src):
        """删掉 dev-mode 期间生成的编译期产物，让主构建重新生成。

        只删产物、不改 makeopts 之外的输入：`menuselect-tree` 仍然保留
        dev-mode 的 cflags 段（这样 TEST_FRAMEWORK 成员存在），但这些头文件会按
        已去掉 AST_DEVMODE 的 makeopts 重新生成。
        """
        for relative in ("include/asterisk/buildopts.h",
                         "include/asterisk/build.h",
                         "main/version.c"):
            path = os.path.join(src, relative)
            if os.path.isfile(path):
                os.remove(path)

    def _enable_test_framework(self, src, rpath):
        """打开上游测试框架与测试模块（in-tree 用例的编译前提）。

        Asterisk 的 `tests/test_*.c` 每个用例模块都声明
        `<depend>TEST_FRAMEWORK</depend>`，MENUSELECT_TESTS 类别默认不在制品里；
        不打开该选项时设备上不存在任何 `/main/...`、`/res/...` 上游用例，
        也就无法执行上游测试套件。要点：

        1. `TEST_FRAMEWORK` 成员只在 `build_tools/cflags-devmode.xml` 中定义，
           而该文件仅当 `AST_DEVMODE=yes`（`configure --enable-dev-mode`）时才
           追加进 `menuselect-tree`；因此测试构建必须在 configure 阶段打开
           dev-mode，否则 `TEST_FRAMEWORK` 成员根本不存在。
        2. dev-mode 会把 `-Werror`/`-Wunused`/`-Wundef` 等加进 `_ASTCFLAGS`
           （Makefile L211），在 OHOS/musl 上无法整树通过，所以进入主构建时用
           命令行变量 `AST_DEVMODE=` 覆盖，只保留 menuselect 选择结果。
        3. `menuselect --enable` 只接受一个成员（long_options 为
           required_argument，menuselect.c L2048），必须重复给出。
        4. 顺序与上游 CI（`tests/CI/buildAsterisk.sh`）一致：
           `make menuselect.makeopts` → 逐个 `--enable ... TEST_FRAMEWORK` →
           `--enable-category MENUSELECT_TESTS` → `--check-deps`。
        5. 只启用 DONT_OPTIMIZE 与 TEST_FRAMEWORK：上游 CI 还会打开
           MALLOC_DEBUG 与 DO_CRASH，但在 HarmonyOS/musl 真机上，同时启用这两个
           选项构建出的二进制会在模块加载阶段死锁——设备实测 `Asterisk Dynamic
           Loader Starting:` 之后 `core waitfullybooted` 永不返回、`module show`
           阻塞（loader 持锁），而同一设备上未启用这两个选项的构建可以正常
           "Asterisk Ready."。因此测试构建保持与已验证基线一致的 cflags 组合。
        """
        menuselect = os.path.join(src, "menuselect", "menuselect")
        self.run(
            f"make --jobserver-style=pipe menuselect.makeopts 'BUILD_LDFLAGS={rpath}'",
            cwd=src,
        )
        # 注意：TEST_FRAMEWORK 在 dev-mode 的 menuselect 树中默认即为启用，
        # 这里显式再打开一次，保证与上游 CI 的语义一致（不依赖默认值）。
        enables = " ".join(
            f"--enable {name}" for name in ("DONT_OPTIMIZE", "TEST_FRAMEWORK")
        )
        self.run(f'"{menuselect}" {enables} menuselect.makeopts', cwd=src)
        self.run(
            f'"{menuselect}" --disable COMPILE_DOUBLE menuselect.makeopts',
            cwd=src,
        )
        self.run(
            f'"{menuselect}" --enable-category MENUSELECT_TESTS menuselect.makeopts',
            cwd=src,
        )
        self.run(f'"{menuselect}" --check-deps menuselect.makeopts', cwd=src)
        # makeopts 是 menuselect-tree 的前置依赖：去掉 AST_DEVMODE 后必须重新
        # 生成树，否则主构建会按"tree 比 makeopts 旧"重跑 menuselect.makeopts，
        # 而此时若树已不含 cflags-devmode 段，TEST_FRAMEWORK 成员消失、check-deps
        # 直接失败（Error 255）。这里用命令行变量把 dev-mode 只留给树的生成。
        self._strip_makeopts_dev_mode(src)
        self.run(
            f"make --jobserver-style=pipe 'AST_DEVMODE=yes' 'BUILD_LDFLAGS={rpath}' "
            f"menuselect-tree",
            cwd=src,
        )
        self._drop_dev_mode_artifacts(src)

    def _configure_args(self):
        ld = self.dependencies["openldap"]
        args = [
            f"--prefix={self.package_folder}",
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            f"--with-ldap={ld.package_folder}",
            "--without-pjproject",
            "--without-x11",
            "--without-gtk2",
        ]
        if self.options.with_test_framework:
            # 只为让 menuselect 树包含 build_tools/cflags-devmode.xml
            # （TEST_FRAMEWORK 成员定义所在）；dev-mode 的严格告警在主构建
            # 阶段被 AST_DEVMODE= 覆盖关闭。
            args.append("--enable-dev-mode")
        return args

    def _sign_elf(self, path):
        """E077 四步签名：remove-section → (无修改) → sign → chmod a+x。"""
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            raise ConanInvalidConfiguration("需要 llvm-objcopy 与 binary-sign-tool 签名产物")
        self.run(f'"{objcopy}" --remove-section .codesign "{path}"', ignore_errors=True)
        self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        os.chmod(path, 0o755)

    def _is_elf(self, path):
        with open(path, "rb") as handle:
            return handle.read(4) == b"\x7fELF"

    def _bundle_libs(self):
        """自包含打包：解析主程序与模块的 NEEDED 依赖，把依赖动态库复制进
        包内 lib/（二进制 RUNPATH 已指向包内 lib/），随后统一签名，使包在
        设备上无需任何 LD_LIBRARY_PATH 即可运行。含传递依赖闭包。"""
        import subprocess

        readelf = (
            shutil.which("llvm-readelf")
            or shutil.which("readelf")
            or shutil.which("llvm-readobj")
        )
        if not readelf:
            raise ConanInvalidConfiguration(
                "需要 llvm-readelf、readelf 或 llvm-readobj 解析 ELF 依赖")
        readelf_args = ["--dynamic-table"] if os.path.basename(readelf) == "llvm-readobj" else ["-d"]
        pkg_lib = os.path.join(self.package_folder, "lib")

        def read_needed(elf):
            result = subprocess.run(
                [readelf, *readelf_args, elf], capture_output=True, text=True,
            )
            names = []
            for line in result.stdout.splitlines():
                # 形如： 0x...0001 (NEEDED)   Shared library: [libedit.so.0]
                if "Shared library:" not in line:
                    continue
                names.append(line.split("[")[1].rstrip("]"))
            return names

        elf_files = []
        for sub in ("sbin", "bin", os.path.join("lib", "asterisk", "modules")):
            d = os.path.join(self.package_folder, sub)
            if os.path.isdir(d):
                for entry in sorted(os.listdir(d)):
                    p = os.path.join(d, entry)
                    if os.path.isfile(p) and self._is_elf(p):
                        elf_files.append(p)

        candidate_dirs = [self._shim_dir]
        for dep_name in ("openldap", "libedit", "uuid", "jansson", "libxml2", "sqlite3"):
            candidate_dirs.extend(self.dependencies[dep_name].cpp_info.libdirs)
        # SDK sysroot 与编译器运行时目录（libc++_shared.so 等）。
        # 真机工具链可能位于用户可写前缀，不能依赖固定的 HNP 路径；
        # 从 Conan 选择的 clang 路径动态推导其 runtime/sysroot 目录。
        clang_path = self._clang
        if os.path.isabs(clang_path):
            compiler_root = os.path.dirname(os.path.dirname(clang_path))
            candidate_dirs += [
                os.path.join(compiler_root, "lib", "aarch64-linux-ohos"),
                os.path.join(compiler_root, "lib", "aarch64-linux-ohos", "c++"),
                os.path.join(compiler_root, "lib"),
                os.path.join(compiler_root, "sysroot", "usr", "lib",
                             "aarch64-linux-ohos"),
            ]
        system_libs = {
            "libc.so", "libm.so", "libdl.so", "libpthread.so",
            "librt.so", "libresolv.so", "libutil.so", "libxnet.so",
        }

        queue = []
        for elf in elf_files:
            queue.extend(read_needed(elf))
        while queue:
            name = queue.pop()
            dst = os.path.join(pkg_lib, name)
            if (name in system_libs or name.startswith("ld-")
                    or os.path.exists(dst)):
                continue
            found = None
            for d in candidate_dirs:
                cand = os.path.join(d, name)
                if os.path.isfile(cand):
                    found = cand
                    break
            if not found:
                self.output.warning(f"bundled: {name} not found in candidates")
                continue
            shutil.copy2(found, dst)
            self.output.info(f"bundled {name}")
            # 传递依赖闭包
            queue.extend(read_needed(dst))

    def package(self):
        src = self.source_folder
        # configure --prefix 即 package_folder，直接 make install 落入包目录；
        # INSTALL=./install-sh -c 是相对路径，子目录 make install 会失败 →
        # 用命令行变量覆盖为绝对路径
        install_sh = os.path.join(src, "install-sh")
        # DISABLE_SOUNDS=yes（patch 0001）：CI 沙箱无外网，跳过声音包下载
        self.run(f'make install INSTALL="{install_sh} -c" DISABLE_SOUNDS=yes', cwd=src)
        # The upstream config-options test loads this file from the installed
        # configuration directory.  It is a test fixture, not a runtime
        # configuration, so install it only for the OHOS test artifact.
        if str(self.settings.os) == "OHOS":
            sample = os.path.join(src, "configs", "samples", "config_test.conf.sample")
            target_dir = os.path.join(self.package_folder, "etc", "asterisk")
            if os.path.isfile(sample):
                os.makedirs(target_dir, exist_ok=True)
                shutil.copyfile(sample, os.path.join(target_dir, "config_test.conf"))
        self._bundle_libs()
        # 全量 ELF 签名（E077 四步：remove-section → sign → chmod）：
        # OHOS 内核拒绝未签名可执行文件；dlopen 的模块同样需要签名
        for root, dirs, files in os.walk(self.package_folder):
            for entry in files:
                candidate = os.path.join(root, entry)
                if not (os.path.isfile(candidate) and not os.path.islink(candidate)):
                    continue
                if not self._is_elf(candidate):
                    continue
                base = os.path.basename(entry)
                if base.endswith((".a", ".la")) or ".a." in base:
                    continue
                try:
                    self._sign_elf(candidate)
                except Exception as exc:
                    self.output.warning(f"sign failed for {candidate}: {exc}")

    def package_id(self):
        del self.info.settings.compiler

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
