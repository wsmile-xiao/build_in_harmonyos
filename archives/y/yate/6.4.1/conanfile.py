#!/usr/bin/env python3
"""Conan recipe — yate 6.4.1 (Yet Another Telephony Engine)

HarmonyOS PC (OHOS aarch64) 适配要点（详见 notes.md）:
- configure-only bootstrap: 源码树无预生成 configure, build() 先跑 autogen.sh
  (autoconf/2.72 tool_requires; 零 AM_ 宏/零 .y 文件, 不需 automake/libtool/bison)
- v1 lean 范围: --disable-sctp --without-openssl --without-sqlite → 零 requires
- OHOS musl 无 glibc _res 全局解析器状态 → make DEFS=-DYATE_RES_NO_GLOBAL_STATE
  (Resolver.cpp 补丁配套宏; 命令行变量自然传播到子 make)
- OHOS 无 GNU install 命令 → _ensure_install_cmd 自举 busybox wrapper 到
  build_folder 私有 bin (R49 私有 prefix, 不污染共享路径; 系统有 install 则跳过)
- 7 个补丁: pthread 取消族/MUTEX_HACK __THROW/_res/IAX narrowing/
  miniwebrtc aarch64 分支/SIP camel_map 哨兵/install-api 条件化
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class YateConan(ConanFile):
    name = "yate"
    version = "6.4.1"
    description = ("Yate (Yet Another Telephony Engine): open-source VoIP PBX "
                   "engine with SIP/RTP stack")
    license = "GPL-2.0"
    homepage = "https://yate.null.ro/"
    url = ""  # CI fills this
    topics = ("voip", "sip", "rtp", "pbx", "telephony")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # 引擎主体产物为 libyate.so（.yate 模块经 dlopen 挂接, 动态库为产品形态）
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # v1 lean 范围: 零依赖（pthread/dl 为系统库, dlopen 缺失才 AC_MSG_ERROR）

    def build_requirements(self):
        # 源码树无 configure, 需 autoconf 经 autogen.sh 生成;
        # autoconf/2.72 为仓内唯一版本（本地 2.73 实测通过, 钉 2.72 保 CI 确定性）
        self.tool_requires("autoconf/2.72")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 仅生成构建环境（CC/CXX/CONFIG_SHELL/PATH/LD_LIBRARY_PATH, 来自 profile）;
        # configure/make 在 build() 中 in-source 手动执行——Autotools helper 的
        # out-of-source 布局与 yate 自研 configure 的子目录 Makefile 不兼容
        # （子目录 @srcdir@ 前置路径断裂 → No rule to make target）
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _ensure_install_cmd(self):
        """OHOS 无 GNU install 命令（make install → Error 127）。
        自举 busybox install wrapper 到 build_folder 私有 bin（R49: 私有 prefix,
        不注入共享 /usr/local; 系统已有 install 则跳过, CI clean 环境自适应）。
        返回 bindir（需注入 PATH）或 None。"""
        if shutil.which("install"):
            return None
        bindir = os.path.join(self.build_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        busybox = shutil.which("busybox")
        if busybox:
            script = '#!/bin/sh\nexec {bb} install "$@"\n'.format(bb=busybox)
        else:
            # 无 busybox 时的最小 GNU install 子集: -d / -m MODE / -s
            script = (
                "#!/bin/sh\n"
                "mode=''; mkdir_only=0\n"
                "while [ $# -gt 0 ]; do case \"$1\" in\n"
                "  -d) mkdir_only=1; shift;;\n"
                "  -m) mode=\"$2\"; shift 2;;\n"
                "  -s) shift;;\n"
                "  *) break;;\n"
                "esac; done\n"
                "if [ \"$mkdir_only\" = \"1\" ]; then mkdir -p \"$1\"; exit 0; fi\n"
                "dest=\"$1\"; shift\n"
                "mkdir -p \"$(dirname \"$dest\")\"\n"
                "for src in \"$@\"; do cp -f \"$src\" \"$dest\"; done\n"
                "if [ -n \"$mode\" ]; then chmod \"$mode\" \"$dest\"; fi\n"
            )
        path = os.path.join(bindir, "install")
        with open(path, "w") as f:
            f.write(script)
        self.chmod(path, 0o755)
        return bindir

    def _tool_path_prefix(self):
        """conan 工具链（autoconf/perl/m4）bin 显式前置 PATH。
        根因: 系统 autoconf（shebang 指向 hnp perl 5.42.0）在 PATH 中先于 conan 工具 bin,
        而 conanbuild 环境注入了 conan perl 5.42.2 的 PERL5LIB → 系统 autoconf 脚本加载
        conan perl 的 Cwd.so ABI 不匹配（Perl_my_cxt_init 符号缺失）; conan autoconf
        wrapper 内部经 PATH 解析 perl, 故工具链 bin 须一致前置（CI clean 环境无冲突
        时此前置无害, 双环境自适应）。"""
        parts = []
        for name in ("autoconf", "perl", "m4"):
            try:
                parts.append(os.path.join(self.dependencies.build[name].package_folder,
                                          "bin"))
            except Exception:
                pass
        return ":".join(parts)

    def _make_jobs(self):
        """make 并行度: 按可用内存封顶（约 700MB/clang 预算）。
        低内存机器上 -jN 全核编译会 OOM 杀进程（无日志痕迹, 任务静默丢失）;
        CI 内存充裕时自然回落到全核。非 Linux 环境退化为 min(cpu, 4)。"""
        cpu = os.cpu_count() or 4
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        avail_mb = int(line.split()[1]) // 1024
                        return max(1, min(cpu, avail_mb // 700))
        except Exception:
            pass
        return max(1, min(cpu, 4))

    def build(self):
        apply_conandata_patches(self)
        self._install_bindir = self._ensure_install_cmd()
        # 1. bootstrap（仅 autoconf; 零 AM_ 宏/零 .y → 不需要 automake/libtool/bison）
        # E490 防御: 适配路径可能丢失脚本可执行位（幂等）
        # 注: conan 2 self.run 默认 cwd 为进程工作目录, 必须显式 source_folder
        self.run("chmod +x autogen.sh", cwd=self.source_folder)
        autogen_cmd = "./autogen.sh"
        tool_prefix = self._tool_path_prefix()
        if tool_prefix:
            autogen_cmd = f'PATH="{tool_prefix}:$PATH" {autogen_cmd}'
        self.run(autogen_cmd, cwd=self.source_folder)
        # 2. configure（in-source 于源根执行: yate 自研 configure 不支持 out-of-source
        #    子目录构建——子目录 Makefile 的 @srcdir@ 前置路径断裂 → No rule to make
        #    target; 探索阶段 in-source 构建实测全绿）
        configure_args = ["--prefix={}".format(self.package_folder)]
        if self.options.shared:
            configure_args += ["--enable-shared", "--disable-static"]
        else:
            configure_args += ["--enable-static", "--disable-shared"]
        # v1 lean 范围（决策与理由见 notes.md）
        configure_args += ["--disable-sctp", "--without-openssl", "--without-sqlite"]
        self.run("./configure " + " ".join(configure_args), cwd=self.source_folder)
        # 3. make（DEFS 注入 = Resolver.cpp 补丁配套宏 YATE_RES_NO_GLOBAL_STATE;
        #    make 命令行变量自然传播到 engine/modules 子 make）
        self.run("make -j{} DEFS=-DYATE_RES_NO_GLOBAL_STATE".format(self._make_jobs()),
                 cwd=self.source_folder)

    def package(self):
        # configure 时 prefix 已指向 package_folder, 直接 make install 落包
        # （in-source 构建: Makefile 在源根, cwd=source_folder;
        #   install wrapper 经内联 PATH 前缀注入, 不动 env 参数以免遮蔽 conanbuild 环境）
        make_install = "make install"
        if getattr(self, "_install_bindir", None):
            make_install = f'PATH="{self._install_bindir}:$PATH" make install'
        self.run(make_install, cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "yate")
        # 头文件布局 <pkg>/include/yate/*.h（yate.pc Cflags: -I${includedir}/yate）
        self.cpp_info.includedirs = ["include/yate"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["yate"]  # 与上游 yate.pc 的 Libs 一致（-lyate）
        # yateclass.h 的 YATOMIC_OP 宏门控: 无 ATOMIC_OPS 时展开为 RLock lck(m_lock),
        # 而公共头只前向声明 RLock → 消费者编译 incomplete type 硬错误
        # （上游经 yate-config --cflags 向消费者传递 -DATOMIC_OPS, 此处对齐）
        self.cpp_info.defines = ["ATOMIC_OPS"]
        # .yate 模块目录（引擎 -m 参数指向; 供运行期 dlopen）
        self.cpp_info.bindirs.append(os.path.join("lib", "yate"))
