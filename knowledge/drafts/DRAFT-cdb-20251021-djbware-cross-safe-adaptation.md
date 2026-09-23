# DRAFT-cdb-20251021-djbware-cross-safe-adaptation：djbware 构建系统 OHOS 适配四步法

> **Contributor**: gcw_6YxinkyD | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-08
> **Source event**: cdb 20251021 HarmonyOS PC 适配（PR #8907，真机验证通过）
> 对应：knowledge/drafts/DRAFT-cdb-20251021-djbware-cross-safe-adaptation.kv

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。只进入 `knowledge/drafts/**`，
不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则；是否提升由知识库
维护者和赛事评审决定。

## 现象

djbware 包（cdb.cr.yp.to 系）首次适配时的典型障碍：无 configure / config.guess，
`make` 默认目标报找不到生成脚本或直接开始执行 `./compile`；真机上
`make: ./compile: Permission denied`；`make setup` 会运行 `./instcopy` /
`./instcheck`（原生执行刚构建的二进制）失败；上游不安装库文件，消费者无
`.a` 可链。

## 根因

djbware 构建系统约定（与 autotools 完全正交）：

1. 编译器 / flags / 安装前缀由 `conf-cc`、`conf-ld`、`conf-home` 三个文件的
   **首行**指定，Makefile 读取后生成 `./compile`、`./load`、`./makelib` 三个
   `#!/bin/sh` wrapper 并直接 exec（真机 hmdfs 拒绝脚本 exec，见
   DRAFT-cdb-20251021-hmdfs-shebang-script-exec-refusal）；
2. 默认目标 `it/setup/install` 运行 `./instcopy`（拷贝产物进 conf-home）与
   `./instcheck`（校验安装），**需要原生执行构建产物**，交叉/受限环境不可行；
3. 上游只安装命令、不安装库（cdb 文档明说 "the library per se is not
   installed"），而链接命令实际需要 `cdb.a buffer.a unix.a byte.a` 四个静态库。

## 修复：四步法（cdb 实证）

1. **conf-\* 首行注入**（配方 build() 内做，不进补丁）：conf-cc/conf-ld 首行写
   `exec <CC> <CFLAGS>`，CC 取 Conan conf `tools.build:compiler_executables`
   （P-TOOLCHAIN-001：ar/ranlib 同理走 llvm-\*）；Linux/OHOS flags 加
   `-D_XOPEN_SOURCE=500`（暴露 mmap/lseek 原型，pkgsrc 同款）；conf-home 指向
   package_folder——生成的 `cdbmake-12` 脚本内嵌 `<conf-home>/bin` 绝对路径，
   Conan 缓存包目录稳定可解析（上游行为如此，pkgsrc 同样内嵌 /usr/bin）。
2. **`make prog -j1`**：纯构建目标（全部二进制 + 静态库），不运行
   instcopy/instcheck，交叉安全；产物安装由配方 package() 承担。
3. **两个补丁**：①`0001` 让 makelib 尊重 `${AR}`/`${RANLIB}`（默认
   `ar cr`/`ranlib` → llvm-ar 交叉归档可注入）；②`0002` 把 Makefile 中 68 处
   `\t./compile|./load|./makelib` 调用改为 `\tsh ./xxx`（hmdfs 脚本 exec 限制，
   对 Linux 等价）。Makefile 改动补丁化（P-PATCH-001）。
4. **多静态库合并**：package() 用 `ar x` 解开 `cdb.a cdb64.a buffer.a unix.a
   byte.a`，`ar cr` 合并为单一自包含 `libcdb.a` 后 `ranlib`；cdb64 变体的全部
   符号经 `#define CDB64` 宏重命名（cdb_* → cdb64_*），与 32 位符号无冲突，
   同包双变体可共存；`cpp_info.libs = ["cdb"]`。

## 验证（真实证据）

真机 OHOS aarch64（10.62.134.118），conan 2.29.1 + clang 15.0.4，
`conan create --user=ohpcd --channel=stable` 全绿：14 个 bin、4 个头、
`lib/libcdb.a`（五归档合并）；test_package 32 位 API 回环（4 断言）+ cdb64
API 回环（3 断言）+ cdbmake/cdbget CLI 断言（4 断言）全过；上游 rts 套件
47/55（8 失败均为平台错误注入限制）。

## 与已有知识的差异（查重关键）

- 四范围查重（knowledge/graph/\*.kv、index.tsv、knowledge/drafts/、graph
  engine）：**无任何 djbware 条目**（conf-cc/conf-home/make prog 关键词零命中）；
  本条目是该构建系统家族的首条。
- 与 E339 无关（该条目是 GDBus IPC 测试问题，关键词误命中）。
- tinycdb/0.81（已发布）是**重写式**路线（配方里直接编源文件列表），本条目是
  **保 Makefile 式**路线（补丁最小化、上游结构可追溯），两者互补。

## 禁止做法

- `make setup/install/it`——运行 instcopy/instcheck，原生执行构建产物必挂，
  且污染 conf-home 指向目录；
- 运行时 sed 改 Makefile 不留补丁——distclean 后丢失，CI 无法复现
  （P-PATCH-001）。

## 适用边界

- djbware 家族（cdb / djbdns / ucspi-tcp / daemontools / fastqueue 等）首次适配；
- "宏重命名同源双变体"（CDB64 模式）的单包多变体打包可跨库复用；
- cdb64 打包前提是符号真的全部重命名（无符号冲突），合并前需 nm 复核。
