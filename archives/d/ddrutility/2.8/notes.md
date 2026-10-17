# ddrutility 2.8 适配笔记

## 编译环境
- 构建系统: makefile（上游手写，2.8 起不再使用 automake）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4（OHOS SDK，aarch64-linux-ohos / musl）
- 状态: built

## 编译步骤

```bash
# 1) 源码
https://downloads.sourceforge.net/project/ddrutility/ddrutility-2.8.tar.gz
sha256 4c31116189397bba7fb1750852bc1e21adc13357446b1fc7c4ac6ca7853b6f08

# 2) 应用 patches/0001+0002（apply_conandata_patches 自动执行）

# 3) 编译（解压后 strip 顶层目录 ddrutility-2.8/）
make CC=/data/service/hnp/bin/clang CFLAGS='-O2 -Wall -W' -j1
```

上游 makefile 只定义 `all`（4 个 C 程序）、`clean`、`install`、`uninstall` 目标，
没有 `check`/`test` 目标；配方在 `package()` 中按上游 install 规则的落点自行安装
（bin / share/man/man1 / share/info）并额外附 GPLv2 许可文件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接报大量 `ld.lld: error: duplicate symbol`（tvDiff / p_ntfs_attribute / p_mft_mft / p_boot_sector 等） | 2016 年的旧 C 代码在 `ddru_ntfscommon.h` 里**直接定义**全局变量（依赖编译器默认 `-fcommon` 合并各 TU 的 tentative definition）；clang 15 默认 `-fno-common`，于是每个包含该头的 TU 都产出强符号 | 按知识库 `DRAFT-clang-fno-common-header-globals` 的**正解**修：`ddru_ntfscommon.h` 的全局变量改为 `extern` 声明（4 个匿名 union 改为具名 typedef），并在 `ddru_ntfscommon.c` 里集中定义一次。产出 `patches/0001`+`patches/0002`。**未使用 `-fcommon` 兜底**（该草稿将 `-fcommon` 列为 fallback/技术债） |
| 2 | makefile 写死 `CC= gcc` | 上游 makefile 第 3 行 `CC= gcc` | `make CC=<clang>` 命令行赋值优先级高于 makefile 赋值，直接覆盖（无需补丁） |
| 3 | `ddru_findbad` 以 `ddru_findbad.sh` 交付 | 上游 makefile install 规则把它 `cp $(PROG20).sh $(bindir)$(PROG20)` 改名安装 | 配方 `package()` 同步改名安装并补 0755 执行位 |

## 源码修改

`patches/0001-ddru_ntfscommon.c.patch`、`patches/0002-ddru_ntfscommon.h.patch`
（由 `refresh-patch --auto` 生成，`patch_type: portability`）：

- `0002`：`ddru_ntfscommon.h` 中 4 个匿名 union 改为 `typedef union {...} <name>_t;`
  并改成 `extern <name>_t <name>; extern <name>_t *p_<name>;`；标量全局变量
  （`start_time`/`inode_count`/`file_name`/`cd`/`no_convert` 等）同样改为 `extern` 声明。
- `0001`：在 `ddru_ntfscommon.c` 中集中定义上述全部全局变量一次。

补丁**不含任何平台宏**（无 `#ifdef __OHOS__`），是纯 C 标准正确性修复，对任何现代
编译器（GCC 10+ / clang）都成立；`patch_classification.platform_only: False`。

## 依赖版本

无编译期依赖（仅 libc / libm）。`ddru_findbad` 运行期按需调用外部命令
（sleuthkit / ntfs-3g / gnu-fdisk / gnuddrescue），属运行期可选依赖，未纳入
conan `requirements()`（非链接依赖，OHOS 沙箱无这些工具时脚本按自身逻辑报错）。
构建期 `clang -dM -E` 实测 OHOS clang 定义 `__linux__`/`__OHOS__`/`__unix__`，
`scsi/sg.h` 与 `iconv.h` 均在 OHOS sysroot 中存在，`#ifndef __linux__` 平台分支
不会误入非 Linux stub。

## 验证结果

```bash
# 本地（设备，OHOS aarch64）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → test_package/test.sh: PASS=13 FAIL=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/ddrutility` | 工具集入口 |
| `bin/ddru_ntfsbitmap` | NTFS bitmap → ddrescue domain logfile |
| `bin/ddru_ntfsfindbad` | ddrescue 日志 → 涉及坏道的文件列表 |
| `bin/ddru_diskutility` | SCSI 直通磁盘工具 |
| `bin/ddru_findbad` | POSIX sh 坏道相关文件定位脚本 |
| `share/man/man1/*.1` | 5 个程序的手册页 |
| `share/info/ddrutility.info` | GNU info 文档 |

## 注意事项

- 上游无测试套件（N=0）；适配后补全的 13 项消费者断言全部为**新增**鸿蒙特有测试，
  不与上游用例数混计。
- `install` 目标写死 `$(DESTDIR)/usr/local/...`，配方未使用该目标（避免把文件装到
  `usr/local` 布局），改为在 `package()` 中按 conan 标准布局安装。
