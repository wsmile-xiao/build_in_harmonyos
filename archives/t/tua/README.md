# tua（The UUCP Analyzer）

读取 Taylor UUCP 的日志与统计文件（`Log`、`Stats`），输出 UUCP 流量报表：
按远程系统、按用户、按日期、按月、按小时的收发量与连接时长统计，并可根据
PCD 费率文件估算电话费用。

## 功能

- 按系统 / 用户 / 日期 / 月份的输出统计（文件数、KBytes、时长、ATP）
- 20 分钟粒度的每小时活动图（`-o` 仅输出图表）
- 系统 / 用户 / 端口的别名替换与 glob 别名（`-s` / `-u` / `-r` / `-M` / `-E` / `-R`）
- 限制/排除指定系统或用户（`-O` / `-k` / `-K`）
- 基于 `TUA.pcd` 的费率与国家配置（`--print-country` / `--list-countries`）
- 历史文件更新/重置（`-H` / `-0`）

## 命令行

```sh
tua [options]

  -p, --prefix-path=DIR   从目录 DIR 读取 Log / Stats（默认 /usr/local/spool/uucp）
  -o, --chart-only        仅输出每小时活动图
  -S/-U/-D/-m/-h/-y       关闭 系统/用户/每日/月度/历史/小时图 报表
  -i, --help              用法
  -V, --version           版本
  --print-country         打印国家费率配置
```

## 安装

```bash
conan install --requires=tua/4.3 -r=ohpcd
# 产物：<package>/bin/tua
```

## 依赖关系

| 类型 | 依赖 |
|------|------|
| 编译依赖 | 无（仅 OHOS libc；`bison` 仅构建期用于生成 `pcdl_gram.c`） |
| 运行依赖 | 无（动态链接 OHOS 系统 musl 运行时） |

## OHOS 适配要点

- 源码归档（Debian 重打包版）删除了 `intl/`、`src/getopt.[ch]`、`src/alloca.c`，
  而随包 `configure` / `src/Makefile.in` 仍引用它们：patch 0002/0003 做等价修复
  （不生成 intl 头链接、改用 libc 的 getopt_long）。
- `src/tua.h` 原先包含私有的 `intl/libgettext.h`：patch 0005 改为公有 gettext API，
  并在 `--disable-nls` 下把 `_()` 退化为恒等映射（OHOS libc 运行期自带 gettext）。
- `src/tua.c` 的 `<locale.h>` 原先由内嵌 gettext 头间接带入：patch 0004 显式包含。
- `LOG()` 宏使用 `__FUNCTION__` 做字符串拼接，clang 已不再视其为字符串字面量：
  patch 0005 改用 `__func__`。
- 文档目标需要 `makeinfo`/`texi2dvi`（工具链不具备），且 man 源 `doc/tua.1l`
  被重打包删除：patch 0001 从 `SUBDIRS` 移除 `doc`。

## 测试

- 上游 4.3（1996）无任何自动化测试：无 `tests/` 目录、无 `TESTS` 声明，
  `make check` 仅无断言地运行 `./tua` 且需真实 UUCP spool 数据。
- 消费者侧测试见 `4.3/test_package/test_tua.sh`：10 项用例（含 1 项鸿蒙平台专有：
  产物 AArch64 OHOS ELF + musl 解释器），构造合成 Taylor UUCP spool 实际运行被测二进制。

## 参考资料

- 上游源码（Debian 官方归档）：https://deb.debian.org/debian/pool/main/t/tua/
- 源码浏览：https://sources.debian.org/src/tua/
- 许可证：GPL-2.0-or-later
