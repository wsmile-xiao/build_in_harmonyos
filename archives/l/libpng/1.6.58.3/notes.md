# libpng 1.6.58.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-19
- 编译器: clang
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built；R20 exact-snapshot W3 通过并完成任务自有目录清理，尚未上传制品

## 编译步骤

autotools(非 CMake：避 CMake 在 OHOS 的无-SONAME 坑 ML-0035，libtool 自管 SONAME libpng16.so.16)。zlib 经 AutotoolsDeps 注入。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 不能直接执行，且 config.guess 不识别 uname 输出 | HMDFS 禁止临时目录 shell 脚本直接执行；平台名推断不可靠 | 用可用 POSIX shell 解释 configure，并以目标 C 编译器 `-dumpmachine` 的结果提供 native build triplet |
| 2 | AC_CHECK_LIB([z]) 找不到 zlib | 需注入 zlib 的 -I/-L/-lz | --autotools-deps(AutotoolsDeps+PkgConfigDeps)；native 编译 conftest 链接探测通过 |
| 3 | config.status 无法创建 subs1.awk | Autoconf 的 `umask 077` 与 HMDFS setgid 目录语义冲突 | 复制 `configure` 到 build 目录，仅在临时副本中将两个 `umask 077` 窄化为 `umask 022`，传入 `--srcdir` 后删除副本（E129） |
| 4 | 上游测试脚本和 libtool wrapper 报 Permission denied | HMDFS 禁止直接执行临时 shell 脚本；测试 ELF 还需稳定签名 | 用 `/system/bin/sh` 显式解释外层与嵌套脚本；shared 构建以重签后的 `.libs/*` ELF 覆盖顶层 wrapper，并注入 `.libs` 到 `LD_LIBRARY_PATH` |
| 5 | test_package 访问 `_Component.cpp_info` 失败 | 首个列表元素已是 `cpp_info`，却被当作依赖对象再次解引用 | 保持依赖对象列表，循环内统一取得 `dependency.cpp_info`，并维持 `png16` 在 `z` 前的链接顺序 |
| 6 | `libpng.pc` 含绝对包路径，config shell 在 HMDFS 不可直接执行 | 只处理了 `libpng16.pc`，且上游 install 保留 shell config 工具 | 同时重定位两个 `.pc`；移除两个 config shell；显式重签并保留 `pngfix`、`png-fix-itxt` ELF |
| 7 | test_package 从裸 `CC` 环境变量选择编译器 | release Worker 不保证 shell 环境变量存在或与 Conan profile 一致 | 从 `tools.build:compiler_executables` 解析绝对 C 编译器，签名工具沿用同一解析器 |
| 8 | 正式 1.6.58.1 PREV 含两个悬空 symlink | 删除真实 `libpng16-config`/`libpng16.la` 后，`Path.is_file()` 对悬空别名返回 false | 对真实文件和 `Path.is_symlink()` 都执行 unlink；test_package 拒绝两个别名路径的任何残留 |
| 9 | 冻结 runner 只核对 zlib RREV/PREV | 未把候选身份中的 Conan package ID 纳入运行门禁 | 从冻结身份精确核对 RREV/PID/PREV，并以只篡改 PID 的负测证明拒绝 |
| 10 | POSIX `sh` 的末端证据流水线可能掩盖上游失败 | `set -eu` 不提供 pipefail，`find | sed | sort` 只返回末端命令状态 | 将证据枚举、归一化和排序拆成逐步检查的无管线实现；任一步失败均删除 pending COMPLETE 且禁止发布 result |
| 11 | 设备 release controller 的回执可能早于 endpoint lease/lock 清理完成 | `remote-release-success.sh` 先写 `DEVICE_RELEASED` 再清理，失败时会留下虚假释放证据 | 每个 own-identity 清理步骤显式失败返回，核验 lease/lock 均不存在后才原子发布 `DEVICE_RELEASED`；清理失败非零、无回执且可安全重试 |

## 源码修改

无补丁（构建开关 + conanfile 适配即可）。

## 依赖版本

- zlib/1.3.2（fresh Conan home 下 OHOS 6.0/armv8 `--build=never` 安装通过）

## 版本策略

- 上游最新稳定版仍为 v1.6.58；v1.7.0beta89 是预发布版，不作为稳定升级。
- 现有 libpng/1.6.58 二进制绑定 zlib/1.3.1.1，无法满足使用 zlib/1.3.2 的下游闭包。
- 1.6.58.1 已正式发布，但其 PREV 含 `bin/libpng-config` 和 `lib/libpng.la` 两个悬空链接。
- 按适配修复后缀规则准备 1.6.58.3（libpng 包名，上游 v1.6.58），源码 URL 与 SHA256 保持官方 v1.6.58 不变；不得覆盖 libpng/1.6.58 系列。

## 验证结果

- 正式缺陷证据：1.6.58.1 RREV/PID/PREV 已绑定，两个别名均为 symlink 且目标不存在，`conanmanifest.txt` 同时记录二者。
- 本地定向回归：PASS；新实现正向 6 项，旧实现/旧包负向 3 项，精确复现 2 个悬空链接并由 test_package 拒绝。
- 本地 W0 graph：fresh E 盘 Conan home，2 个节点，`info_invalid=0`、`Missing=0`；zlib/1.3.2 RREV `73f9291bbbf6587c1b453f541f5debf7`、PID `6b129b068851896169fae42d399fa922d239ce8a`、PREV `fbb0afb34d16643c8b06ef23a0d003a4`。
- R20 上游测试：36/36 PASS，失败 0，跳过 0；完整 Automake 清单见 `reports/upstream-test-inventory.txt`。
- R20 test_package 消费者流：1/1 PASS，覆盖 4 条公开 API 与包内容断言。
- R20 frozen candidate tree：`7db177bc6b170867625d4d202703b87bc6d23869`；HEAD/tree/base：`9b94a603c1f031845a9aab68e360fd43443c62e6` / `f19f3423e3ad26f2cf58ca8b5e33224a0cb2043e` / `807fa2c350480cb15271d1891f23b2b991916fd5`。
- R20 独立 W4：`P0/P1/P2/P3=0/0/0/0`，33/33 requirements；结果 SHA256 `097b41814ce8b335d5e0b0f8d0f6f30727b7d4320713f094dc20ea534a9531c8`。
- R20 真机终态：`FORMAL_FINISH_PASS_CLEANED`，launch_count=1；上游 36/36、消费者 1/1、unexpected 0。
- 终端 archive SHA256：`73e44314a508f2093185a2c857900f7189093360470b6c8d37c840ecf919edb8`；自有 root 两次 clean scan，bound process、lock 和 lease 均为 0/absent。
- controller 外层在 durable PASS 写入后发生 PowerShell `Object[]` 到 `Int32` 转换错误；未重跑，按 `FINAL-RESULT.json`、终端 archive 和 cleanup readback 独立核验真机终态。

## 历史证据边界

- r46 terminal archive SHA256：`1ca57d85824f1ec07c8c7ec292393d8a99fdac50263dd40a7939db01e99ec350`。
- r46 FINAL-RESULT.json SHA256：`f32c505eb87fc6207f8be56d3fd006b182714cf7944bfb1d83f4c14a390c15b6`。
- r46 `launch_count=1`、`status=FORMAL_FINISH_FAIL_RELEASED`、上游 `0/36 PASS_NOT_PROVEN`；未执行第二次启动或任何制品上传。
---

**编译结束**: 2026-08-19 06:56
**最终状态**: built
