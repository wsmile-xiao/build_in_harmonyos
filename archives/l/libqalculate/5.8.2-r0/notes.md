# libqalculate 5.8.2-r0 适配笔记

## 编译环境
- 构建系统: autotools（自带 configure，无需 autoreconf）
- 编译日期: 2026-09-02
- 编译器: clang/clang++（SDK aarch64-linux-ohos）
- 状态: built（conan-verify 全门禁通过，CI upload 前）

## 依赖（制品仓均已发布，conan requires 管理）
| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| gmp | 6.3.0 | requires | configure AC_CHECK_LIB 硬检查 |
| mpfr | 4.2.2 | requires | configure AC_CHECK_LIB 硬检查 |
| libxml2 | 2.15.3 | requires | configure PKG_CHECK_MODULES 硬检查 |
| readline | 8.3 | requires | qalc CLI 增强（缺头不硬错误） |

可选依赖 libcurl/ICU 未发布 → configure 传 `--without-libcurl --without-icu`。

## 构建期工具（cmd-pkgs 预编译包，配方内自动安装）
- intltool 0.51.0（IT_PROG_INTLTOOL 硬错误）
- gettext 0.22.5（GNU gettext 三工具 xgettext/msgmerge/msgfmt 硬错误）

## 适配点（3 个补丁 + 运行时处理）

### 补丁 0001: config.guess（HarmonyOS 检测）
- `Linux|GNU|GNU/*)` → `Linux|GNU|GNU/*|HarmonyOS)`，LIBC 简化为 gnu
- 添加 `aarch64:HarmonyOS:*:*` → `aarch64-unknown-linux-gnu`

### 补丁 0002: configure
- 跳过 intltool XML::Parser 检查（`if test "x" = "xno-xml"`）：OHOS 无 XML::Parser perl 模块
- 移除 `umask 077 && mktemp/mkdir`（HMDFS 兼容）

### 补丁 0003: util.cc（pthread 守卫）
- `pthread_setcancelstate/setcanceltype/pthread_cancel` 在 OHOS musl 不可用
- 用 HAVE_PTHREAD_* 宏守卫 + `#include "pthread_compat.h"`
- pthread_compat.h 由配方 feature-detection 生成：
  ⚠️ 检测编译必须加 `-Werror=implicit-function-declaration`——OHOS 头文件无
  pthread_cancel 声明但 C 允许隐式声明（仅警告），不加 -Werror 会误判可用

### intltool-merge shim（配方 build() 内生成）
- data/*.xml.in → *.xml 需要 INTLTOOL_MERGE，但真工具运行时需要 XML::Parser
- shim 用 perl 去掉 `_` 翻译标记，PATH 前置让 configure AC_PATH_PROG 找到

## 关键踩坑（conan-verify 多轮修复）

### 1. 不用 AutotoolsDeps/VirtualRunEnv（cddlib 同坑）
- AutotoolsDeps 把 conan 依赖 -l 全塞进 LIBS → configure 早期 conftest
  （cross-compiling 检查）也链上依赖 → 运行期找不到 conan 缓存 .so → $?=127
- VirtualRunEnv(scope=build) 把 conan 依赖 lib 目录放 LD_LIBRARY_PATH →
  lld 链接器自身依赖 SDK libxml2.so.16 被 conan libxml2.so.16 劫持 →
  "Error relocating lld" 崩溃
- libqalculate configure 检查（AC_CHECK_LIB 仅链接、PKG_CHECK_MODULES 走
  pkg-config）不需要运行期依赖库 → 依赖路径用 include/lib flag 手动注入即可

### 2. LD_LIBRARY_PATH 必须显式注入（build() 内 os.environ）
- fixpo 等构建期 C++ 工具依赖 libc++_shared.so，conanbuild 沙箱不自动带
- 顺序：SDK llvm/lib（lld 用 SDK libxml2）→ /system/lib64（libc++）→ conan 依赖 lib
- 不注入则 "Error loading shared library libc++_shared.so: symbol not found"

### 3. 依赖 .la 文件路径修复（libgsf E236 同款）
- conan 包 .la 的 libdir='//lib'（prefix=/ 拼接错误）→ libtool 读依赖 .la 失败
- 必须**跨包全局映射**：mpfr.la 的 dependency_libs 引用 libgmp.la 应解析到
  **gmp 包**真实 lib 目录，不能一律替换成当前包自己的 lib 目录

### 4. test_package 显式声明传递依赖
- libqalculate 头文件 qalculate.h 直接 #include <gmp.h> 等
- CMakeDeps 只生成直接依赖配置 → test_package 必须 requires + find_package
  gmp/mpfr/libxml2/readline，否则 gmp.h not found

### 5. test_package 运行时注入 SDK libc++
- test 二进制 + libqalculate.so 是 SDK clang 编译 → 依赖新版本 libc++_shared.so
- 不加 LD_LIBRARY_PATH 会命中系统旧版 → Error relocating: symbol not found
- test() 内 os.environ 注入 SDK llvm/lib/aarch64-linux-ohos 路径

### 6. Calculator::calculate API 签名（5.8.2 vs 5.11.0）
- 5.8.2: `MathStructure calculate(std::string, ...)` 按值返回
- 5.11.0: `int calculate(str, MathStructure*)` 旧签名（历史 test.cpp 已过时）

### 7. 线程取消功能降级说明（R40）
OHOS musl 不提供 pthread_cancel/pthread_setcancelstate/pthread_setcanceltype，
util.cc 中 Thread::cancel() 与 Thread::enableAsynchronousCancel() 的对应调用被
HAVE_PTHREAD_* 宏守卫编译掉，线程取消功能在 OHOS 上静默降级为 no-op。
这是可接受的退化：qalc/libqalculate 正常计算流程不依赖线程取消（仅用于
超时中断辅助路径），不影响核心计算/单位换算功能。

## 验证结果
- make check: 上游 unittest 1/1 PASS（src/test-suite.log）
- conan-verify: G0-G4/L2/L4/L5 全 PASS
- test_package: 创建 Calculator 并计算 `1 + 2 * 6` = 13 验证库可用
- commands.json: 软件级声明（构建产物含 bin/qalc CLI 工具, R38）

## 产物
- libqalculate.so.23.3.9 / libqalculate.a
- qalc CLI（bin/）
- libqalculate.pc（Libs: -lqalculate）
---

**编译结束**: 2026-09-02 04:00
**最终状态**: built（conan-verify 全门禁通过，CI upload 前）
