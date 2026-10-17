#!/usr/bin/env python3
"""Conan recipe for samba 4.21.0 on HarmonyOS PC (aarch64).

samba 使用 waf 构建系统（顶层 wscript + ./configure wrapper）。

本配方要点（CI 可迁移，无个人绝对路径）：
- 消费器件仓 gnutls/3.8.10、zlib/1.3.1（waf configure 强制检查
  GnuTLS>=3.6.13、zlib>=1.2.3）；perl tool_requires 制品仓拉取。
- 编译器 CC/CXX/AR/RANLIB 从 conan profile 的
  tools.build:compiler_executables 读取（CI profile 注入），避免 waf
  compiler_c 探测相对名 clang 在 HMFS 上 PATH 解析失败。
- 所有 env 注入（编译器、PYTHONHASHSEED、PKG_CONFIG_PATH、依赖
  include/lib、vendored PERL5LIB）统一在一个 Environment() 对象里，
  每次调用 waf 时 `with env.vars(self).apply():` 包裹——与仓库
  jack/1.9.22、adql/2.0 验证过的范式一致，保证一次全部生效。
- PIDL 需要 Parse::Yapp::Driver(>=1.05) + yapp：perl 由 tool_requires
  提供；Parse::Yapp::Driver 通过 vendored parse-yapp/（export_sources
  复制进源树）注入 PERL5LIB；yapp 二进制缺失时 pidl/wscript 补丁降级
  为警告（release tarball 已带预生成解析器）。
- --without-ad-dc 裁剪 AD DC、--without-ldap 取消 LDAP（无 openldap）。
  默认变体保留 --disable-python（鸿蒙无 python embedding，同 ldb 2.9.2
  适配）；with_selftest=True 启用 python 绑定（selftest python 管线
  依赖 samba/_glue、_ldb、param 等编译扩展）：waf python 检查走
  python_cross_compile 环境变量旁路（python3-config --ldflags --embed
  输出 -lintl/-ldl，OHOS/musl 无 libintl，链接实测失败），cryptography/
  pyasn1 缺失降级见 0010 补丁。selftest 默认关闭（with_selftest=False）；
  with_selftest=True 时 --enable-selftest：
  5 个 cwrap wrapper 走制品仓系统包（配方内 .pc shim 注入 PKG_CONFIG_PATH，
  绕过 OHOS 无 libtirpc/rpc.h 的 bundled 编译死结；uid minversion 1.3.1→
  1.2.5 见 0006 补丁），并引入 libarchive/3.8.7（source3/wscript 对
  selftest 的硬依赖），全量 selftest 真实执行、TAP 日志落构建树
  selftest-tap.log（详见 notes.md）。
"""

import os
import subprocess

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class SambaConan(ConanFile):
    name = "samba"
    version = "4.21.0"
    description = "Samba — the standard Windows interoperability suite (file/print server)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.samba.org/"
    url = "https://github.com/samba-team/samba"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "with_selftest": [True, False]}
    default_options = {"shared": True, "with_selftest": False}

    def export_sources(self):
        export_conandata_patches(self)
        # vendored Parse::Yapp::Driver.pm（pidl 运行时必需，纯 perl 模块）
        copy(self, "parse-yapp/**", self.recipe_folder, self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # waf configure 强制依赖（mandatory=True）：
        #   - GnuTLS >= 3.6.13（wscript_configure_system_gnutls）
        #   - zlib >= 1.2.3（wscript 顶层 CHECK_CFG package='zlib'）
        #   force=True：libarchive/3.8.7（selftest 硬依赖）钉死
        #   zlib/1.3.1.1，与本配方 zlib/1.3.1 版本冲突——force 统一整图
        #   zlib/1.3.1（zlib 补丁级 ABI 兼容；默认变体图不含 libarchive，
        #   该 force 对其为无操作，CI 行为不变）
        self.requires("gnutls/3.8.10")
        self.requires("zlib/1.3.1", force=True)
        # selftest（R51 第二段）：5 个 cwrap wrapper。waf configure 经
        # CHECK_BUNDLED_SYSTEM_PKG（纯 pkg-config 探测）：命中系统包且版本达
        # minversion 则 USING_SYSTEM_*=1，跳过 bundled 编译（OHOS musl 无
        # libtirpc/rpc.h，bundled socket_wrapper 不可编，详见 notes.md）。
        # uid-wrapper 1.2.5 < minversion 1.3.1 → 版本检查不通过，自动回退
        # bundled uid_wrapper（deps 仅 dl pthread，OHOS 可编）。
        if self.options.with_selftest:
            self.requires("socket-wrapper/1.5.2")
            self.requires("nss-wrapper/1.1.16")
            self.requires("resolv-wrapper/1.1.8")
            self.requires("uid-wrapper/1.2.5")
            self.requires("pam-wrapper/1.1.8")
            # selftest 硬依赖：source3/wscript:204 在 --without-libarchive 且
            # selftest 开启时直接 raise WafError；制品仓 3.8.7 包设置与本
            # profile 一致（armv8/clang15/cppstd17/OHOS6.0/Release）
            self.requires("libarchive/3.8.7")

    def build_requirements(self):
        # pidl 是 perl 脚本，构建期需要 perl 可执行（制品仓拉取，CI 可迁移）
        self.tool_requires("perl/5.42.2")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # waf pkg-config 探测名（下划线）→ 制品仓包名（连字符）
    _WRAPPER_PC = {
        "socket-wrapper": "socket_wrapper",
        "nss-wrapper": "nss_wrapper",
        "resolv-wrapper": "resolv_wrapper",
        "uid-wrapper": "uid_wrapper",
        "pam-wrapper": "pam_wrapper",
    }

    def generate(self):
        # 生成依赖 .pc（gnutls/zlib）与 VirtualBuildEnv（perl tool_requires
        # 的 PERL/PERL5LIB、profile 的 PATH 等落盘 conanbuild 环境）
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        # selftest：制品仓 wrapper 包自带 .pc 的 Libs 指向发布者机器绝对
        # 缓存路径（本机/CI 不存在），在 generators_folder 写本地 .pc shim
        # 覆盖（waf CHECK_BUNDLED_SYSTEM 纯 pkg-config 探测，读到 shim 即
        # 命中系统 wrapper 分支，跳过 bundled 编译）。
        if self.options.with_selftest:
            self._write_wrapper_pc_shims()

    def _write_wrapper_pc_shims(self):
        for dep_name, pc_name in self._WRAPPER_PC.items():
            dep = self.dependencies.get(dep_name)
            if dep is None:
                continue
            pf = dep.package_folder
            text = (
                "prefix={}\n"
                "Name: {}\n"
                "Version: {}\n"
                "Description: {} wrapper (local shim; publisher .pc "
                "Libs has foreign absolute cache path)\n"
                "Cflags: -I${{prefix}}/include\n"
                "Libs: -L${{prefix}}/lib -l{}\n"
            ).format(pf, pc_name, dep.ref.version, pc_name, pc_name)
            save(self, os.path.join(self.generators_folder, pc_name + ".pc"), text)

    def _python_cross_info(self):
        """设备 python（python3）sysconfig 一次性查询（缓存）：selftest 变体
        的 waf python 检查走 python_cross_compile 环境变量旁路（模块
        docstring），旁路变量需匹配本机 python 真实路径（构建期动态查询，
        CI 可迁移，无硬编码绝对路径）。"""
        if getattr(self, "_pyinfo", None) is None:
            code = (
                'import os,sys,sysconfig as s;'
                'print("%d.%d" % sys.version_info[:2]);'
                'print(s.get_config_var("INCLUDEPY") or "");'
                'print(s.get_config_var("LIBDIR")'
                ' or os.path.join(s.get_config_var("prefix") or "", "lib"));'
                'print(s.get_config_var("EXT_SUFFIX")'
                ' or s.get_config_var("SO") or ".so");'
                'print(s.get_config_var("LDLIBRARY") or "")'
            )
            # conan 2.29.1 ConanFile.run 无 output 参数，直接 subprocess 捕获
            # （继承 conanbuild 已应用的 PATH/env，与 waf 所见一致）
            p = subprocess.run(
                "python3 -c '{}'".format(code), shell=True,
                capture_output=True, text=True, check=False)
            out = p.stdout
            lines = [ln.strip() for ln in out.strip().splitlines()[:5]]
            while len(lines) < 5:
                lines.append("")
            version, inc, libdir, ext_suffix, ldl = lines
            libname = "python" + version.replace(".", "")
            if ldl.startswith("lib") and ldl.endswith(".so"):
                libname = ldl[3:-3]
            self._pyinfo = {
                "version": version,
                "inc": inc,
                "libdir": libdir,
                "ext_suffix": ext_suffix,
                "libname": libname,
            }
        return self._pyinfo

    def _build_env(self):
        """构建期需要暴露给 waf 的环境，全部集中在这里（单一注入点）。"""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        ar = compilers.get("ar") or (os.path.join(bindir, "llvm-ar") if bindir else "")
        ranlib = compilers.get(
            "ranlib"
        ) or (os.path.join(bindir, "llvm-ranlib") if bindir else "")
        if ar:
            env.define("AR", ar)
        if ranlib:
            env.define("RANLIB", ranlib)

        # samba waf 强制 PYTHONHASHSEED=1（官方 ./configure 里 export）
        env.define("PYTHONHASHSEED", "1")

        # PkgConfigDeps 生成的 .pc 目录注入 PKG_CONFIG_PATH，供 waf CHECK_CFG
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)

        # 依赖 include/lib 目录（gnutls/zlib；selftest 时 + 5 wrapper）注入
        # CPATH/LIBRARY_PATH（wrapper libdir 同时供 LD_PRELOAD 裸名 .so 解析）
        _dep_names = ["gnutls", "zlib"]
        if self.options.with_selftest:
            _dep_names.extend(self._WRAPPER_PC.keys())
            # libarchive：CHECK_HEADERS('archive.h') + CHECK_LIB('archive')
            _dep_names.append("libarchive")
        incs, libs = [], []
        for _dep_name in _dep_names:
            if _dep_name in self.dependencies:
                _dep = self.dependencies[_dep_name]
                _pf = getattr(_dep, "package_folder", None) or ""
                incs.extend(
                    g if (os.path.isabs(g) or not _pf) else os.path.join(_pf, g)
                    for g in _dep.cpp_info.includedirs
                )
                libs.extend(
                    l if (os.path.isabs(l) or not _pf) else os.path.join(_pf, l)
                    for l in _dep.cpp_info.libdirs
                )
        if incs:
            env.append("CPATH", os.pathsep.join(incs))
        if libs:
            env.append("LIBRARY_PATH", os.pathsep.join(libs))
        # selftest 运行期：wrapper 裸名 .so（selftest.pl 拼进 LD_PRELOAD）
        # 与整图 host 依赖运行时库（python 扩展 .so 链接 gnutls，dlopen
        # 级联到 libtasn1.so.6 等传递依赖，实测）均经 LD_LIBRARY_PATH
        # 解析；TMPDIR 用构建树下可写目录（/tmp 只读 erofs，见 0001
        # 补丁与 E002）
        if self.options.with_selftest:
            for _dep_name, _dep in self.dependencies.host.items():
                _pf = getattr(_dep, "package_folder", None) or ""
                for _l in _dep.cpp_info.libdirs:
                    env.append_path(
                        "LD_LIBRARY_PATH",
                        _l if (os.path.isabs(_l) or not _pf)
                        else os.path.join(_pf, _l),
                    )
            env.define("TMPDIR", os.path.join(self.build_folder, "selftest-tmp"))
            # selftest python 管线（waf python 检查 + 测试子进程）：
            # ① python_cross_compile 旁路变量——常规路径经
            #    python3-config --ldflags --embed 取链接旗标（-lintl -ldl），
            #    OHOS/musl 无 libintl（ld.lld: unable to find library
            #    -lintl，实测）；旁路给干净 LDFLAGS 后 pyext/pyembed 检查
            #    均过（实测 yes）。
            # ② PYTHONPATH——bin/python 必须置前：构建期纯 python 全量
            #    复制进 bin/python/samba/ 并同置 86 个扩展 .so（有
            #    __init__.py，完整 samba 包；samba/__init__.py 硬 import
            #    _glue/_ldb/param 等扩展模块），源码目录 python/ 置前会
            #    让无 .so 的源码包胜出 → samba.param ModuleNotFoundError
            #    （实测）；python/ 仅作回退。
            _py = self._python_cross_info()
            env.define("PYTHON_VERSION", _py["version"])
            env.define("PYTAG", "cpython" + _py["version"].replace(".", ""))
            env.define("pyext_PATTERN", "%s" + _py["ext_suffix"])
            _pyflags = " ".join(
                part
                for part in (
                    "-I" + _py["inc"] if _py["inc"] else "",
                    "-L" + _py["libdir"] if _py["libdir"] else "",
                    "-l" + _py["libname"],
                    "-lm",
                )
                if part
            )
            env.define("PYTHON_PYEXT_LDFLAGS", _pyflags)
            env.define("PYTHON_PYEMBED_LDFLAGS", _pyflags)
            env.define(
                "PYTHONPATH",
                os.pathsep.join(
                    [
                        os.path.join(self.source_folder, "bin", "python"),
                        os.path.join(self.source_folder, "python"),
                        os.path.join(self.source_folder, "source4", "selftest"),
                        os.path.join(self.source_folder, "selftest"),
                    ]
                ),
            )

        # PIDL: vendored Parse::Yapp::Driver（export_sources 复制到源树
        # parse-yapp/），追加进 PERL5LIB 供 pidl/wscript 检查与运行
        _vendor = os.path.join(self.source_folder, "parse-yapp")
        if os.path.isdir(os.path.join(_vendor, "Parse", "Yapp")):
            env.append_path("PERL5LIB", _vendor)

        return env

    def _waf(self, command, *args):
        # 尊重 tools.build:jobs（conan 标准 conf，CI/本地均可限并发，
        # 防低内存机器上全核并行 clang 触发 OOM）
        jobs = self.conf.get("tools.build:jobs", default=None, check_type=int)
        if jobs and command in ("build", "test"):
            args = ("--jobs", str(jobs)) + args
        joined = " ".join(args)
        # 与 jack/adql 一致的注入方式：以 env.vars(self) 上下文包裹，
        # 把 CC/CXX/PYTHONHASHSEED/PKG_CONFIG_PATH/PERL5LIB 打进子进程 env
        with self._build_env().vars(self).apply():
            self.run(
                f"./buildtools/bin/waf {command} {joined}".strip(),
                cwd=self.source_folder,
                env=["conanbuild"],
            )

    def build(self):
        apply_conandata_patches(self)
        configure_args = [
            # --prefix=/ + --destdir=package_folder 得顶层干净安装布局
            # （wbclient.h 在 <pkg>/include/、库在 <pkg>/lib/）；Dynconfig
            # 记录的 //share/ 运行时配置路径为可接受 cosmetic，不阻塞。
            "--prefix=/",
            # 裁剪 AD DC（无需域控制器），保留文件服务器主体
            "--without-ad-dc",
            # LDAP 默认启用但无 libldap（openldap），裁剪之
            "--without-ldap",
            # JSON 审计日志依赖 jansson，无则裁剪
            "--without-json",
            # POSIX ACL（libacl）缺失且非核心文件服务器依赖，裁剪之
            "--without-acl-support",
            # ADS（LDAP 目录集成）依赖 LDAP，已裁剪之同步禁用
            "--without-ads",
            # PAM（可插拔认证模块）headers 缺失，裁剪之
            "--without-pam",
            # 磁盘配额：OHOS musl 的 struct dqblk 无 dqb_curblocks 成员，
            # legacy quota 代码无法编译，裁剪之
            "--without-quotas",
            # 避免 cups/systemd/lttng/gettext 等外设依赖
            "--disable-cups",
            "--without-systemd",
            "--without-lttng",
            "--without-gettext",
        ]
        if self.options.with_selftest:
            # R51 第二段：全量 selftest（waf configure 走 ENABLE_SELFTEST
            # 分支：pkg-config 命中系统 wrapper + RECURSE testsuite/unittests）。
            # libarchive 为 selftest 硬依赖（source3/wscript:204），不再传
            # --without-libarchive，autodetect 经 CPATH/LIBRARY_PATH 命中
            # 制品仓 libarchive/3.8.7
            configure_args.append("--enable-selftest")
            # 启用 python 绑定（不传 --disable-python）：selftest python 管线
            # 依赖 samba/_glue/_ldb/param 等编译扩展（见模块 docstring 与
            # _build_env 的 python 旁路）
        else:
            # 非 selftest 构建：libarchive 仅 smbclient tar 模式使用，裁剪之
            configure_args.append("--without-libarchive")
            # 鸿蒙无 python embedding：禁用 python 绑定（同 ldb 2.9.2 适配；
            # selftest 变体则启用 python，见上）
            configure_args.append("--disable-python")
        self._waf("configure", *configure_args)
        self._waf("build")
        if self.options.with_selftest:
            # 全量 selftest 真实执行：TAP 日志落构建树 selftest-tap.log
            # （末行 SELFTEST_EXIT=<code>）。R9：不强制通过——selftest 退出
            # 码传播到构建步：selftest 失败 = create 失败（selftest 变体是
            # 本地证据非发布变体，root 受限环境下其 create 失败为预期行为，
            # 结论如实回填 PR，不占位不冒充）。
            os.makedirs(os.path.join(self.build_folder, "selftest-tmp"),
                        exist_ok=True)
            jobs = self.conf.get("tools.build:jobs", default=None, check_type=int)
            job_opt = f"--jobs {jobs} " if jobs else ""
            with self._build_env().vars(self).apply():
                self.run(
                    f"./buildtools/bin/waf {job_opt}test > selftest-tap.log 2>&1; "
                    "ec=$?; echo \"SELFTEST_EXIT=$ec\" >> selftest-tap.log; exit $ec",
                    cwd=self.source_folder,
                    env=["conanbuild"],
                )

    def package(self):
        self._waf("install", "--destdir={}".format(self.package_folder))

    def package_info(self):
        # samba 是应用 + 库套件：核心库由私有库机制管理（lib/private），
        # 可执行文件在 bin/sbin。
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.set_property("pkg_config_name", "samba")
