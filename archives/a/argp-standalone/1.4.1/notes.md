# argp-standalone 1.4.1 适配笔记

## 基本信息
- 上游：https://github.com/ericonr/argp-standalone（ericonr fork，tag 1.4.1）
- 与已归档 1.5.0 的关系：**不同上游**（1.5.0 来自 argp-standalone org；
  1.4.1 来自 ericonr fork——Niels Möller 原始 1.0~1.3 的延续维护线）。
  1.4.1（2021-02）是 1.5.0（2023+）的前身版本，无 GPLv2 LICENSE 文件
  差异问题，LGPL-2.1-or-later。
- 构建系统: autotools（仅 configure.ac，需自举）
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, musl)
- 日期: 2026-09-04
- 状态: built（conan create + conan-verify G0-G4 全过）

## 为什么 OHOS 需要这个包
OHOS 用 musl libc，**musl 不提供 argp(3)**（glibc 专属命令行解析 API）。
大量 GNU 软件（coreutils 系、elfutils、gnulib 生态）用 argp 解析命令行。
argp-standalone 把 glibc 的 argp 抽成独立静态库 libargp.a + argp.h，
补齐 musl/OHOS 的 API 缺口。下游消费范例：elfutils/0.195、execstack。

## 编译步骤（模式 B 探索 → 固化配方）
1. `autoreconf -fi` 自举生成 configure（设备无 automake/aclocal，
   用 conan `tool_requires automake/1.18 + libtool/2.5.4` 提供）
2. 修补 configure 内嵌 `umask 077` → `umask 022`（HMDFS 兼容，见坑 1）
3. `./configure --build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-musl ac_cv_header_libintl_h=no`
4. `make -j1` → libargp.a + testsuite/{ex1,ex3,ex4}
5. `make check` → 上游测试 2/2 全过
6. package() 手工安装 argp.h + libargp.a（上游 noinst 设计，见坑 4）

## 遇到的问题与解决方案（本次实测）
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 写 `./confXXXXXX/subs1.awk` 报 Permission denied | **HMDFS mktemp+umask 陷阱**：configure/config.status 内嵌 `umask 077 && mktemp -d ./confXXXXXX`，HMDFS（hmmac=genfs）下 umask 077 建出的目录为 `drwx--S---`，**组执行位缺失导致目录内无法写任何文件**（chmod 修正也被忽略，E046 同源）。实测 umask 扫描：077/027 不可写，022/002/007 可写（规律=组执行位 g+x 必须存在） | configure 生成后 sed 替换 `umask 077`→`umask 022`（build() 内 glob 修补，必须在 autoreconf 之后——自举会重新生成 configure） |
| 2 | HAVE_LIBINTL_H → `__dcgettext` 未定义（编译警告+链接失败） | OHOS musl 的 libintl.h 是空壳（宏在、函数符号不在）。configure 探测到头就定义 HAVE_LIBINTL_H，argp-help.c 走 `__dcgettext` 分支——glibc 内部符号 musl 没有 | `ac_cv_header_libintl_h=no` 强制探测为假 → 走 `#define dgettext(d,m) (m)` 直通分支（继承 1.5.0 经验） |
| 3 | test_package 首版（CMake）运行报 `Error relocating ./test_argp: _ZdlPv: symbol not found` | C++ 二进制动态链 libc++_shared.so，OHOS 搜索路径/LD_LIBRARY_PATH 问题 | test_package 改 elfutils/0.195 同款模式：直接 clang++ 编译探针 + `-static-libstdc++` 静态链 C++ 运行时（运行期只依赖系统 libc.so） |
| 4 | `make install` 什么都不装 | 上游 Makefile.am 全是 noinst_*（设计为被内嵌编译） | package() 手工拷 argp.h + libargp.a（Alpine APKBUILD 同法） |

## 与 1.5.0 历史归档的差异
- 上游仓库不同（ericonr vs argp-standalone org）——conandata URL 指各自官方源
- 1.5.0 有 GPLv2 拷贝问题在 org 版本被处理；1.4.1 直接 LGPL-2.1-or-later
- 两者适配坑完全同构（libintl 空壳、noinst、umask），解法可互相印证
- 1.5.0 的 test_package 遗留了对 libargp.so 的探测（其实只产 .a）；1.4.1 版修正为纯静态

## 上游测试结果（2026-09-04 实测）
```
srcdir="." ./run-tests  ex1-test permute-test
PASS: ex1
PASS: permute
==================
All 2 tests passed
==================
```
- ex1-test：无参成功/带参失败/--help 输出 Usage:/非 long-only 的 -help 失败（5 断言）
- permute-test：6 组 -v/位置参数排列组合下 ex3 输出与期望 diff 一致
- **通过率 2/2 = 100%**

## test_package 消费者验证（R34）
test_probe 直接 clang++ 编译链接 libargp.a，运行断言 8/8：
- argp_program_version 设置读回、长/短选项识别、-o 取值、--output= 取值、
  位置参数 ARGP_KEY_ARG、多位置参数、未知选项非零返回
- **8/8 全过**（conan-verify G2 日志实证）

## 知识沉淀（路径 B 素材）
本包是 **musl/OHOS 缺失 glibc API 补齐**模式的典型样本：
- argp 与 musl-fts/musl-obstack/musl-argp 同属"glibc 有 musl 无"补齐库家族
- 下游消费写法（elfutils/0.195 实证）：`self.requires("argp-standalone/x.y.z")`
  （host 依赖而非 tool_requires——argp 是目标机运行时 API）
- 已按 SKILL graph add --draft 记录知识草稿（见 DRAFT 编号）

## 源码修改
- 无源码 patch（conandata patches: {}）——configure 的 umask 修补在
  build() 运行期完成（autoreconf 之后 glob 替换），不落 .patch 文件
  （patch 文件 9014 行的 configure 生成物不可维护，历史 1.5.0 的
  0001-configure.patch 就是整份 configure，本次改用运行期修补更干净）

## 交付物
- archives/a/argp-standalone/1.4.1/{conanfile.py, conandata.yml, test_package/, manifest.yaml, notes.md}
- conan 产物：libargp.a + argp.h（package_type=static-library）

**编译结束**: 2026-09-04
**最终状态**: built（conan-verify PASS，G2 conan create 成功）
---

**编译结束**: 2026-09-04 02:21
**最终状态**: built
