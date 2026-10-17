# gap 4.16.0 编译笔记（HarmonyOS PC · conan / autotools）
## 定位
计算离散代数系统（群论为主）— gap 交互/批处理可执行文件 + libgap 共享库 + GAP 包树
产出库：`libgap.so`。
产出命令行工具：`gap`。

## 源码
- URL：https://github.com/gap-system/gap/releases/download/v4.16.0/gap-4.16.0.tar.gz
- sha256：`aaa296b32a5d7bf25fd80f241d23ec1f58b74e991ae730fafe40e54eb3af6e7e`

## conan 依赖

- `gmp/6.3.0`
- `zlib/1.3.1.1`

## 关键适配

- `--without-readline`：`--with-readline` 的链接测试在设备上过不去（还要 ncurses/tinfo）。readline 只影响 GAP **交互式 REPL 的行编辑**，passagemath 走 libgap 与管道，接口层面无损 —— 这是有意的取舍，不是没接上
- GAP 的 `make install` 把 GAP root **拆成两半**：架构无关的（lib/init.g、grp/、doc/）进 `share/gap`，架构相关的（sysinfo.gap）进 `lib/gap`。GAP 包必须装进 **`share/gap/pkg`**；位置放错就报 `gap: hmm, I cannot find 'lib/init.g'`。测试要用**分号分隔的双 root** `share/gap;lib/gap`
- GAP root 路径被烤进二进制 —— 与 ECL 的 `SYS:`、Singular 的 libexec 同类问题：conan 化后必须找到它的环境变量出口
- 删除 `lib/*.la`：里面烤死 libdir 绝对路径（conan 按 prefix=/ 构建 → 写的是 `/lib`），下游 libtool 会去找 `//lib/libxxx.la` 而失败
- 修 configure 的 `umask 077` → `022`（HMDFS 上 077 会让后续步骤读不到自己刚建的临时文件）

## 真机验证（2026-08-17）

设备：HUAWEI MateBook（HAD-W32 / 2in1），OHOS aarch64。
`conan create . -pr ohos-native` 通过，test_package 断言：

1. SymmetricGroup(5) 的阶 = 120 ✅
2. 小群库 smallgrp 可用（NrSmallGroups(8) = 5） ✅
3. 本原群库 primgrp 可用 ✅

> 这个包一共重跑了 3 轮才通过，每轮换一个不同的真因（详见上面「关键适配」）。

## 状态

built —— 真机已验证；制品**尚未上传**（上传须单独过闸）。
