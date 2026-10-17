# lcmaps-plugins-voms 1.7.1 — OHOS (aarch64/musl) 适配笔记

## 探索结论

configure.ac 实证（1.7.1 tarball）编译期依赖仅两项：

1. `AC_CHECK_LIB([dl],[dlsym])` — musl 下 dl* 在 libc，探针实测通过（知识 E013）。
2. `AC_LCMAPS_INTERFACE([basic])` → PKG_CHECK_MODULES(lcmaps-basic-interface)。
   lcmaps/1.6.7 已发布制品仓，包内自带 lcmaps-basic-interface.pc ✓。

**无 voms 库编译期依赖**（反直觉但证据确凿）：configure.ac 全文无 voms 库检查
（宏 AC_VOMS 仅被 REQUIRE 引用且无定义，展开为空）；src/Makefile.am 的
plugin_LTLIBRARIES 无 voms LIBADD；插件源码 include 的仅 lcmaps/*.h。
插件运行期消费的是 LCMAPS 框架委托链中已解析好的 VOMS 凭证数据
（FQAN/poolindex 等），由上游插件（如 voms server 侧）填充。
W0 制品仓实测：voms/{2.1.0,2.1.1,2.1.2,2.1.3,3.0.0}、libvomsapi/* 均
不存在（conan download 报 "system acceleration policy not enabled"，
与明显不存在的 zzzz-fake-pkg 报错一致，对照实验确认语义=包不存在）。
不构成 dependency_missing——因为根本不需要。

## 平台补丁（3 个，均为构建辅助，无源码条件宏）

- `0001-config-guess-harmonyos.patch`：2014 版 config.guess 不识别
  `uname -s`=HarmonyOS → 编译回退路径在 OHOS 存储失败。主 case 分支顶部
  插入 HarmonyOS 识别返回 aarch64-unknown-linux-ohos。与 lcmaps/1.6.7
  patches/0001 同源同因（hunk 上下文不同：本包 2014 版为
  `${UNAME_MACHINE}:...` 花括号形式）。
- `0002-config-sub-ohos.patch`：2014 版 config.sub 无 kernel-os 二级 case
  结构，改在两处 OS 模式列表（118-119 行主列表与 1379 行 -linux-* 前缀
  列表）插入 linux-ohos*。实测 aarch64-unknown-linux-ohos 校验通过。
- `0003-config-status-mktemp-hmdfs.patch`：**新发现平台陷阱**。
  autoconf 生成的 config.status 用 `(umask 077 && mktemp -d ./confXXXXXX)`
  创建临时目录；toybox mktemp -d 固定 mkdir(0700)，在 HMDFS 上产出
  drwx--S--- 目录 → 内部写 subs1.awk 报 "can't create ...: Permission
  denied"，且 chmod 事后补救无效（E046 chmod 不生效）。而普通 mkdir 走
  HMDFS 归一化得 drwxrws--x 可写。修复：configure 内该行 mktemp -d
  改为 mktemp_ohos_fallback（不存在的命令），强制走 autoconf 自带的
  fallback 路径 `tmp=./conf$$-$RANDOM; (umask 077 && mkdir "$tmp")`。
  config.status 由 configure 生成，故只需改 configure 一处。

## 依赖注入（R49 模式）

- lcmaps 1.6.7 包内 lcmaps-basic-interface.pc 的 prefix 写死为 `/`
  （上游适配包瑕疵，本包是首个 pkg-config 下游消费者）。generate() 在
  build_folder/prefix/lib/pkgconfig 生成修正版 pc（prefix 指向依赖包
  package_folder），PKG_CONFIG_PATH 前置该目录，configure 的
  PKG_CHECK_MODULES 即可解析出正确 -I。
- 插件 LIBADD 仅 $(DL_LIBS)，无 lcmaps 链接面 → 无需 -L 注入。
- E075：显式 unset C_INCLUDE_PATH/CPLUS_INCLUDE_PATH/LIBRARY_PATH。

## 其他要点

- E089：tarball 自带完整 configure/aclocal.m4/project 宏，不跑 autoreconf。
- 产物：6 个插件 .so（-avoid-version 无版本号）装 lib/lcmaps/ + 上游
  install-data-hook 建 lcmaps_*.mod 软链接（上游已是 rm -f && ln -s，符合
  HMDFS 软链接要求）+ man8 man 页。无可执行文件 → 不需要 commands.json（R38）。
- 上游测试（NO_UPSTREAM_TESTS，R51 申报）：
  - 清点：顶层/doc/src Makefile.am 均无 check 目标、TESTS、check_PROGRAMS；
    tarball 无 tests/ 目录（ls 实证）。
  - 结论：上游零自动化测试；以 test_package 的 OHOS 冒烟用例
    （dlopen 插件 + dlsym 插件入口符号 + 安装清单断言）真实执行代替。
- 知识检索记录：E013（dl 在 libc）、E046（HMDFS chmod/未签名 ELF）、
  E075（C_INCLUDE_PATH）、E089（勿 autoreconf）；
  mktemp/HMDFS 陷阱为本包新发现，待入库。

## 上游测试实测（R51 三步法）

- 上游测试用例数 N=0（清点证据如上），实跑 N′=0。
- 100% 通过率口径：上游无测试可跑；以本包 test_package 冒烟
  （6/6 插件 dlopen+dlsym 全部 PASS，0 skip）作为验证面。

## test_package 关键设计（新知识）

插件引用框架内部符号（lcmaps_log 等，liblcmaps_without_gsi.so 的 dynsym
不导出这些内部符号，nm -D 实证）。LCMAPS 生产形态是引擎**静态嵌入**消费
程序，插件 dlopen 时从主程序全局命名空间解析。因此 test_package 的测试
二进制必须：--whole-archive 静态拉入 liblcmaps_without_gsi.a + -rdynamic
导出符号 → 精确镜像 LCMAPS 引擎进程映像 → 6/6 插件真实 dlopen+dlsym 通过。

## 本机 conan-verify 踩坑记录（配方自包含修复，均已入 conanfile.py）

1. **HMDFS execve 限制（新发现，待入库）**：由 conan python 运行时出生的
   进程链，execve() HMDFS 用户区文件一律 EACCES（mode 0o777 也拒；
   /system/bin/sh 解释模式不受影响；fork+execv 与 posix_spawn 行为一致）。绕法：
   - configure 用解释模式：`sh <abs>/configure <args>`（不用 autotools.configure()）；
   - MKDIR_P=mkdir -p（autoconf 探测会把 MKDIR_P 设为 install-sh，make exec
     它同样被拒）；automake 的 install_sh/libtool 本身带 ${SHELL} 前缀无需处理。
2. **conan generate() env 陷阱**：tc.generate() 无参调用会在内部重建
   Environment，丢弃 tc.environment() 上的 unset()/prepend()。必须
   tc.generate(env=env) 显式传回。
3. **HMDFS chmod 静默失效**（conan 进程内，E490 变体）：patch 重写后的脚本
   chmod 无效且 exec 拒绝；/system/bin/chmod 二进制可生效；另有 kernel attr
   缓存延迟（chmod 后需 sleep）。配方用「删除+重建+chmod 0o777+
   /system/bin/chmod 兑底」恢复执行位。
4. **conanrunenv 聚合范围**：仅直接 require 的 libdirs 进 LD_LIBRARY_PATH；
   test() 手动构造 LD_LIBRARY_PATH（框架 lib + 插件 lib/lcmaps）。
5. **test_package 传递依赖**：CMakeDeps 只为直接 requires 生成 config；
   显式 self.requires("lcmaps/1.6.7")（与主配方同步）+ find_package(lcmaps)。
---

**编译结束**: 2026-10-02 04:47
**最终状态**: built
