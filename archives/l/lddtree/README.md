# lddtree

> 以 POSIX shell 实现的 ELF 依赖树查看工具，输出可执行文件/共享库的完整依赖链路。

## 简介

`lddtree` 是 Gentoo pax-utils 中 `lddtree.sh` 的独立 fork，由 Natanael Copa 维护，
Alpine Linux 亦使用同一实现。它读取 ELF 文件的 `DT_NEEDED`、`RPATH`/`RUNPATH`
与 interpreter（`PT_INTERP`）信息，按 `ld.so` 的搜索顺序解析每个依赖的实际落盘
路径，并以树状（默认）或扁平（`-l/--list`）形式打印。

相较 pax-utils 的 bash 版本，本实现有三点差异：不依赖 `/bin/bash`、会展开符号
链接链、在缺少 `scanelf` 时回退到 binutils 的 `objdump` + `readelf`。

溯源依赖链（判断一个二进制到底加载了哪份 `.so`）是打包、裁剪 initramfs、排查
"同名库被哪个副本满足"这类问题的常用手段。

## OHOS 适配要点

- **无编译步骤**：产品是一份 shell 脚本，构建期只做语法检查与上游测试。
- **必须提供 ELF 后端**：本平台无 `scanelf`，因此运行依赖 binutils 的
  `objdump` + `readelf`；配方已把 `binutils/2.46.0` 声明为运行时依赖，
  `conan install` 会自动拉取并把它加入 `PATH`。若自行部署，需保证
  `objdump` 与 `readelf` 可从 `PATH` 找到，否则工具会以
  `needs either scanelf or binutils` 退出 1。
- **`getopt` 依赖已移除**：上游使用外部 GNU `getopt(1)` 解析选项，本平台的
  toybox/busybox 不提供该命令且制品仓无 util-linux，故 `patches/0001` 以等价的
  POSIX shell 解析器替换之（语义与可观测行为保持一致）。
- **测试框架替换**：上游以 ATF + kyua 驱动 `tests/lddtree_test`，二者在本平台均
  不存在。`patches/0002` 保留 `make check` 目标并新增自带的
  `tools/atf-sh-mini`（133 行 POSIX sh 的 ATF 兼容层），使 13 个上游用例
  逐字节原样执行；上游测试文件未被改动，断言未被削弱。
- **`/tmp` 只读**：测试与工具运行时如遇临时文件需求，请设置 `TMPDIR`。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| binutils | 2.46.0 | 运行时后端，提供 `objdump` 与 `readelf`（`scanelf` 在本平台不可用） |
| bmake | 20200710 | 仅构建期，用于驱动上游 `make check` |

## 功能验证

```bash
# 解释器与依赖树（默认树状输出）
lddtree.sh /bin/sh
#   sh => /bin/sh (interpreter => /lib/ld-musl-aarch64.so.1)
#       libc.so => /system/lib64/libc.so

# 扁平输出，便于脚本消费（每行一个绝对路径）
lddtree.sh -l /bin/sh

# 以指定根目录解析（用于剖析镜像/根文件系统，不执行目标文件）
lddtree.sh --list --no-auto-root --root /mnt/image/ /mnt/image/usr/bin/foo

# 版本
lddtree.sh -V
#   lddtree-1.27
```

## 参考

- [上游源码仓库](https://github.com/ncopa/lddtree)
- [Gentoo pax-utils（原始 bash 版 lddtree.sh）](https://github.com/gentoo/pax-utils)
