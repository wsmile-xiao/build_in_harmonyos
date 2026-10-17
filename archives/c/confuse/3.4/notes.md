# confuse 3.4 适配笔记

## 编译环境
- 构建系统: autotools（release tarball 自带 configure）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，/data/service/hnp/bin，ohos-sdk 26）
- conan 2.29.1，profile `ci/conan/profiles/ohos-aarch64`（build==host 原生构建）
- 状态: built（conan-verify 全绿）

## 编译步骤

1. `conan create archives/c/confuse/3.4 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`（经 `ohc-run.py conan-verify`）
2. 关键 configure 参数：`--enable-static --disable-shared`（R26 默认静态）、`--disable-nls`（OHOS 无宿主 gettext）
3. `make -j1` + `make check -j1`（上游 29 项测试真实执行，见五维账本）
4. package() 内 ELF 自签（llvm-objcopy + binary-sign-tool，跳软链；本包默认静态无 .so 时为空操作）
5. 消费者测试：裸 clang 编译 `test_confuse.c` → `test_confuse`，链接 libconfuse 断言真实解析行为

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `working directory cannot be determined`（E386 家族） | profile buildenv 把 SHELL/CONFIG_SHELL 指到 hnp bash 5.3，其在 HMDFS 构建目录下 getcwd 必挂；配方级 Environment 压不过 profile buildenv | build() 内以命令行内联 env 前缀手动调 configure：`CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh configure <args>`（abx/0.1 合入先例，经验汇总 §12.38①） |
| 2 | configure 报 `Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'` | 2019 年版 support/config.sub 不识别 ohos 三元组 | 移植补丁 `patches/0002-config-sub-ohos.patch`：config.sub 参数校验后短路放行 `aarch64-*-linux*|aarch64-*-ohos*`（a52dec/0.7.4 合入补丁同款手法） |
| 3 | config.status 报 `can't create ./confXXXX/subs1.awk: Permission denied` | autoconf 内嵌模板用 umask 077 建临时目录，HMDFS setgid 语义下不可写（E011/E114 家族） | `patches` 前置脚本化去除 configure 中 umask 077 包裹（保留真实 mktemp/mkdir；abx/0.1 `_make_config_status_tmp_writable` 同款，经验汇总 §12.1） |
| 4 | make check 4 项失败：quote_before_print / print_filter / int_types / json_lists | 四者共因：`tmpfile()` 返回 NULL——设备 `/tmp` 只读（AGENTS §4 事实），musl tmpfile() 固定 /tmp 不读 TMPDIR（runner 已预置 TMPDIR 仍复现，排除该变量） | 环境限制非库缺陷：保留 make check 全量执行与日志，容错捕获退出码，逐项归因记录于此 |

## 依赖版本

无外部第三方依赖（--disable-nls 后仅 libc）。

## 测试统计（五维账本）

- `N_static`：**29**（tests/Makefile.am `TESTS` 注册项，check_confuse 套件）
- `N_registered`：**29**（automake check 全部注册）
- `N_executed`：**29/29 真实执行**，25 通过 / 4 失败（86.2%，失败逐项归因见上表 #4）
- 未执行分类：**0**
- `N_consumer`：**1** 个消费者程序 `test_confuse`，**10 项断言**全过（cfg_init/cfg_parse/str/int/bool/float/list/默认值回退）

## 知识库使用记录

- E386（HMDFS getcwd / capability-tested shell）：命中并采用其方案（内联 env 路由），同族先例 abx/0.1
- E011/E114（umask 077 临时目录 × HMDFS，经验汇总 §12.1）：命中并采用
- a52dec/0.7.4 合入补丁（config.sub 短路放行 aarch64/ohos 三元组）：手法复用
- B 判定：**hit**——本任务三项适配点均被既有条目/先例完整覆盖（症状一致、解法一致），无新增机制，按路径 A 申报
---

**编译结束**: 2026-09-22 00:56
**最终状态**: built
