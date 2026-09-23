# dbskkd-cdb

## 简介

dbskkd-cdb 是 SKK 日语输入法的**词典服务器**。它按 SKK 服务端协议在标准输入输出上应答
假名汉字转换请求（inetd 模型），每个请求都在一个 cdb 常量数据库里做定长查找：数据库由
SKK-JISYO 词典转换而来，因此查词复杂度与词典规模无关。

产物为单个命令行服务程序：`bin/dbskkd-cdb`（另附 `licenses/LICENSE`）。

上游版本 3.00（git tag `3.00`，2016-11-13），MIT 许可，作者 Kenji Rikitake。

## 功能概述

协议按首字节分派（详见上游 `skk-server-protocol.md`）：

| 请求 | 含义 | 应答 |
| --- | --- | --- |
| `1<键> ` | 转换请求 | 命中：`1` + 词典数据 + LF；未命中：`4` + 键 + LF（skkinput 需要回显键） |
| `2` | 版本 | `dbskkd-cdb-3.00 `（带尾空格） |
| `3` | 主机名 | `novalue: `（常量占位） |
| `0` | 结束会话 | 正常退出（退出码 0） |
| 其他 | 协议错误 | 退出码 76（`EX_PROTOCOL`） |

词典文件缺失或不可读时退出码 78（`EX_CONFIG`）；`<键> ` 缺少分隔空格同样按协议错误处理。

## 使用方法

```sh
# 1) 把 SKK-JISYO 文本转成 cdb 常量数据库（用上游 skktocdbm.sh 生成 cdbmake 输入，
#    再由 cdb 包的 cdbmake 写出数据库；本包不打包这两个脚本，见「OHOS 适配」）
sh skktocdbm.sh < SKK-JISYO.L | cdbmake SKK-JISYO.L.cdb SKK-JISYO.L.cdb.tmp

# 2) 启动服务：词典路径可用 argv[1] 或环境变量给出（补丁 0001，见下）
dbskkd-cdb /path/to/SKK-JISYO.L.cdb
DBSKKD_JISYO=/path/to/SKK-JISYO.L.cdb dbskkd-cdb

# 3) 交互式验证
printf '2'         | dbskkd-cdb SKK-JISYO.L.cdb   # -> dbskkd-cdb-3.00
printf '1かんじ '  | dbskkd-cdb SKK-JISYO.L.cdb   # -> 1/漢字/
printf '0'         | dbskkd-cdb SKK-JISYO.L.cdb   # 正常退出
```

inetd/xinetd 场景不需要参数，用 `server_args` 传词典路径或在该用户环境中设置
`DBSKKD_JISYO` 即可；两者都不给时退回编译期内置默认路径
`/usr/local/share/skk/SKK-JISYO.L.cdb`（上游默认值保持不变）。

## OHOS 适配

- **构建系统**：makefile。上游 Makefile 把编译器与其 flags 写在同一个变量里
  （`CC = cc -Wall -O2 -g -I/usr/local/include`）、把 cdb 库写成硬编码静态库路径
  （`CDBLIB = /usr/local/lib/libcdb.a`）、`install` 目标写死 `/usr/local/libexec`。
  配方在 make 命令行上整体替换 `CC`/`COMPAT`/`CDBLIB`（同时丢掉 `/usr/local/include`），
  并由 `package()` 显式安装产物，因此**没有**为构建系统打补丁。
- **依赖**：`cdb/20251021`（DJB cdb，提供 tinycdb 兼容的 `cdb.h` 与自包含 `libcdb.a`）。
  按上游做法静态链接该静态库，制品运行期只依赖 `libc.so`。`test_package` 另外用
  cdb 包的 `cdbmake`/`cdbtest` 生成并反向校验词典夹具，所以 test_package 也显式声明了该依赖。
- **源码补丁**（1 个，无平台条件编译）：
  1. `patches/0001-dbskkd-cdb.c.patch` 让词典路径可在运行期覆盖：优先级为
     `argv[1]` → `DBSKKD_JISYO` 环境变量 → 编译期内置的 `JISYO_FILE` 默认值。
     上游把词典路径编译进二进制（默认 `/usr/local/share/skk/SKK-JISYO.L.cdb`），
     而该路径在 OHOS 上既不存在也不可写（系统目录只读），包安装到任意 prefix 后都无法
     指定自己的词典、测试也无法驱动它。改动保留了上游默认值与协议行为，
     未引入任何 `#ifdef` 平台分支。
- **上游测试**：3.00 不提供任何测试文件与 `check`/`test` 目标（tarball 13 个成员中
  `test|check|spec` 命中 0，`.travis.yml` 的 script 只有编译命令），按可审计台账记为上游 0；
  `test_package/` 补充 **31** 个用例：**26** 个消费者视角功能用例（真实协议请求/应答逐字节比对、
  10 个夹具词条全覆盖、运行期词典选择（argv 优先级、环境变量、缺失词典退出码、
  编译期默认路径仍在二进制中）、夹具自校验（cdbmake 输入与 golden 文本逐字节一致 +
  `cdbtest` 反向读取），以及一次单进程交互会话（6 个断言））+ **5** 个**鸿蒙特有平台检查**
  （`ohos_` 前缀，`fixtures/ohos_platform_check.py` 用纯 Python 解析随包二进制，不依赖 readelf）：
  - `ohos_elf_aarch64_pie`：ELF64 / AArch64 / `ET_DYN`（PIE）——OHOS PC 目标三元组与平台加载形态；
  - `ohos_elf_codesign`：非空 `.codesign` 段——OHOS 加载器只执行带有效签名的 ELF（E077），
    这也是本包不做 strip 的原因；
  - `ohos_elf_hardening`：`PT_GNU_STACK` 无 `PF_X`（NX）+ `PT_GNU_RELRO` + `DF_BIND_NOW` + `DF_1_PIE`
    ——平台加固基线；
  - `ohos_elf_relocatable`：`DT_NEEDED` 恰为 `[libc.so]` 且无路径分隔符、无 `DT_RPATH`/`DT_RUNPATH`
    指向构建或缓存目录——产物可重定位，设备上除 libc 外无需任何东西（cdb 已静态链入）；
  - `ohos_runs_minimal_env`：仅 `PATH` 的最小环境、词典取自调用方可写目录即可运行——
    对应 OHOS 系统数据目录只读、且设备上不存在构建期环境的前提。
  词典 `.cdb` 是二进制文件，按仓库 CI 的检出约束**不随 PR 提交**，改由
  `test_package/fixtures/make_dict.py` 在测试运行时从纯文本 SKK-JISYO 夹具确定性重建。
- **版本号（请务必按此引用制品）**：任务卡/归档目录/分支版本是单字符 `3`。Conan 的 ConanName
  校验要求版本总长 ≥ 2，单字符会在导出阶段报 `Invalid package version '3'`；而 CI L0n 分支门禁
  要求分支名去前缀恒等于「包目录名-版本目录」、平台按分支名关联任务，目录与分支因此不可改写。
  唯一出口是：**目录 / 分支 / `commands.json` 的版本键与 ref 保持 `3`**（满足 L0n 与本地 PF8
  配方闸），**配方用 `set_version()` 把制品版本归一化为上游发布号 `3.00`**。
  因此**制品仓中的真实引用是 `dbskkd-cdb/3.00`**，消费/查询时请用该 ref；
  `commands.json` 的 `version_normalization.artifact_ref` 与版本级 `manifest.yaml` 的
  `conan_ref` 字段记录了这一对应关系。
- **不做 strip**：hnp clang/lld 的产物自带 `.codesign` 自签段，链接后任何字节改写都会让
  签名失效、内核拒绝 exec（`Operation not permitted`），因此配方不 strip。

## 已知上游限制（本次未修改）

- `cdb_read()` 的返回类型是无符号 `num`，源码里 `if (cdb_read(...) < 0)` 的比较恒为假，
  读失败的错误分支实际不可达（编译器也不报错）；这是上游写法，未改动。
- 请求循环每轮只 `read()` 一次且只处理 `combuf[0]`：多个请求在同一次读取中合流时，
  除首个之外都会被丢弃；键长上限受 `BUFSIZE`(1024) 约束。
- 词典数据长度 ≥ `DATASIZE - 2`(4094) 字节时直接按协议错误退出（`EX_PROTOCOL`）。

## 依赖关系

- 编译依赖：C 编译器（profile 中的 `clang`）+ `cdb/20251021` 的头文件与静态库。
- 运行依赖：`libc.so`（OHOS musl）；词典数据库由使用者自备。

## 参考资料

- 上游仓库：https://github.com/jj1bdx/dbskkd-cdb
- 上游协议说明：`skk-server-protocol.md`（随源码分发）
- TinyCDB：http://www.corpit.ru/mjt/tinycdb.html
- DJB cdb：https://cdb.cr.yp.to/
- Debian 打包（参考其 `cross.patch` 与词典路径处理）：https://salsa.debian.org/debian/dbskkd-cdb
- 许可证：MIT（上游 `LICENSE`）
