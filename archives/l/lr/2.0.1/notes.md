# lr 2.0.1 适配笔记

## 编译环境
- 构建系统: makefile（raw POSIX Makefile，无 configure）
- 编译日期: 2026-09-20
- 编译器: clang（OHOS SDK）
- 状态: built

## 上游确认

- 上游: https://github.com/leahneukirchen/lr （Leah Neukirchen）
- 版本: v2.0.1（2025-09-05 发布）
- 性质: 单文件 C 程序（lr.c，约 1500 行），递归列目录/查找工具
- 许可证: MIT（部分代码衍生自 musl libc）
- 源码 SHA256: `c7c4a57169e1396f17a09b05b19456945c8bb5e55001c5a870b083c0b4a23cd8`
  （release tarball 与 codeload 双源核对一致）

## 上游测试清点（R51）

| 项 | 值 |
| --- | --- |
| 上游测试入口 | 无（Makefile 仅 all/clean/install/FRC 目标） |
| 注册测试数 | 0 |
| 运行环境 | HarmonyOS PC（aarch64 设备） |
| 修改上游测试 | 无（无测试可改） |
| 实测结果 | 0 项（上游无测试套件，tarball 与 GitHub 全量树均无测试文件） |

上游无测试，按规范补全 test_package 二进制级功能测试 + OHOS 专项 ELF/ABI 测试（见下）。

## 编译步骤

1. `conan create archives/l/lr/2.0.1 -pr:h ohos-aarch64 -pr:b ohos-aarch64`
2. source(): `get(..., strip_root=True, filename="lr-2.0.1.tar.gz")` 从 codeload 下载解压
   （tag 名 v2.0.1 无扩展名，须显式传 filename 让 Conan 选择 tar.gz 解码器）
3. build(): `make CC=<conf 中的 clang> -j1`（R9；R33——CC 取自
   `tools.build:compiler_executables` conf 字典而非 ${CC} 环境变量）
4. package(): OHOS 无 coreutils `install` 命令（E098/E108），用 Conan copy()
   拷贝 `lr` 二进制、`lr.1` manpage、`_lr` zsh 补全、`LICENSE` 到 package 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | codeload URL 末段 tag 名 `v2.0.1` 无扩展名，get() 按末段推断文件名误用 zip 解码器 | Conan get() 的文件名推断机制 | source() 显式传 `filename="lr-2.0.1.tar.gz"`（endlessh 先例，E392 同族） |
| 2 | Makefile install 目标依赖 `install` coreutils 命令 | OHOS 平台无 install 命令（E098/E108） | 不跑 make install，package() 用 Conan copy() 直接拷贝产物（endlessh 先例） |
| 3 | Makefile 默认 `CC` 为空、CFLAGS 硬编码 `-g -O2` | 上游 Makefile 面向原生 Linux | make 命令行传 `CC=<conf 取出的 clang>`；CFLAGS 用上游默认值（-g -O2 -Wall 系列，交叉编译无影响） |
| 4 | 测试脚本在 mksh 下 `e_type` 断言失败 | mksh 把 `$17` 解析为 `${1}7`，多位位置参数须花括号 | 改用 `${17}` 形式引用（OHOS /bin/sh 即 mksh，脚本兼容性坑） |

## 源码修改

无补丁。lr.c 在 OHOS 上零警告直接编译：
- `__linux__` 分支（getmntent/mntent 挂载表支持）在 OHOS 上可用且正常编译
- 不需要 endlessh 式的任何平台适配

## 依赖版本

无外部依赖（Makefile 无任何 `-l` 链接项，仅 libc）。
链接产物 NEEDED 仅 `libc.so`（musl）。

## 验证结果

```bash
# OHOS 专项 ELF/ABI 检查（打包二进制，test_lr.sh test 14）
# ELF magic 7f454c46 / ELFCLASS64 / LE / ET_DYN(PIE) / EM_AARCH64 —— 全部通过
# NEEDED 仅 [libc.so]，INTERP=/lib/ld-musl-aarch64.so.1，无 RPATH/RUNPATH

# test_package 功能测试（本机预跑）
# 36/36 通过：-1/-0/-F/-t/-e/-f/stdin/-d/-l/无效选项退出码/不存在路径
# （断言值全部来自本机真实执行基线，非臆测）

# conan create（ohos-aarch64 profile，2026-09-20 真实执行）
# $ conan create archives/l/lr/2.0.1 -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing
# → 退出码 0
# → 包引用: lr/2.0.1#9d2c580c5e66a489d5476fca57aabd89:6b129b068851896169fae42d399fa922d239ce8a#cd3e096751ce1dabdd594deb228677dd
# → RUN: make CC="/storage/Users/currentUser/usr/local/bin/clang" -j1（R9/R33）
# → Packaged 3 files: lr, _lr, LICENSE；1 个 manpage: lr.1
# → test_package: 36/36 通过（LR_OK: all 36 checks passed）
# 完整日志: reports/conan-create.log
```

## 注意事项

- lr 是终端工具（R26 场景），但本身仅链接 libc（NEEDED 只有 libc.so），
  上游 Makefile 不提供静态链接选项且 musl 下动态链接即零额外依赖，
  与 endlessh 先例一致按 application 动态打包。
- `-h` 在 lr 中不是 help 而是普通列文件选项（人类可读大小），测试断言时
  勿照搬 endlessh 的 `-h help` 模式。
- lr 的 `-t` 过滤表达式、`-f` 格式串语义以 lr.1 手册页为准
  （如 `name ~~ "*.txt"` 是 glob 匹配而非正则）。

## 对话记录

### 对话 #1 [2026-09-20]

- 问题: 测试脚本 test 14 的 e_type/e_machine 断言失败（34/36）
- 处理: 根因是 mksh 将 `$17` 解析为 `${1}7`；改为 `${17}` 花括号引用
- 结果: 36/36 全部通过

### 对话 #2 [2026-09-20]

- 问题: 无（conan create 一轮通过）
- 处理: 完整执行 ohos-aarch64 的 conan create --build=missing，源码下载/编译/打包/test_package 全流程真实运行
- 结果: 36/36 断言通过，包 6b129b068851896169fae42d399fa922d239ce8a 创建成功

---

**编译结束**: 2026-09-20
**最终状态**: built
