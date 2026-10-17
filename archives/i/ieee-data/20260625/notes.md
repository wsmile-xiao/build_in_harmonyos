# ieee-data 20260625 适配笔记

## 概述

把 Debian 的 `ieee-data`（IEEE 注册管理机构公开数据表）适配为 HarmonyOS PC 的
Conan 纯数据包。它是 MAC 地址厂商查询类工具（arp-scan、netdiscover、wireshark、
nmap 的 `nmap-mac-prefixes` 替代品）的公共数据来源。

## 上游形态

`ieee-data` 是 **Debian 原生包（Debian-native）**：没有独立的上游工程，
Debian 源码包就是唯一分发形态（`debian/source/format` = `3.0 (native)`）。

```
ieee-data-20260625/
├── LICENSE
├── Makefile              # all: 为空；install: 拷贝数据到 /usr/share/ieee-data
├── .lastupdate           # 数据刷新时间戳（Unix epoch）
├── oui.txt   oui.csv     # MA-L  24 bit (6 hex)
├── mam.txt   mam.csv     # MA-M  28 bit (7 hex)
├── oui36.txt oui36.csv   # MA-S  36 bit (9 hex)
├── iab.txt   iab.csv     # IAB   36 bit (9 hex)
├── update-ieee-data      # /usr/sbin 下的运行时联网刷新脚本
├── update-ieee-data.8    # 对应 man page
└── debian/
```

## 安装内容

```
share/ieee-data/{oui,mam,oui36,iab}.{txt,csv}
share/ieee-data/.lastupdate
licenses/LICENSE
```

与 Debian 一致，数据表装在 `share/ieee-data/`；消费方通过
`IEEE_DATA_DIR`（buildenv/runenv）或 `cpp_info.resdirs` 定位。

## 为什么没有编译步骤

上游 `Makefile` 的 `all:` 目标为空 —— 数据表是**上游随源码一起发布的静态数据**，
不存在 from-source 生成过程（生成动作在 Debian 维护者的机器上由
`update-ieee-data` 完成）。因此本配方：

- `package_type = "unknown"`，不声明 `settings`（纯数据包，产物与架构无关）；
- `build()` 只做数据完整性自检，不调用任何编译器/构建系统；
- 不创建 `commands.json`、不伪造 ELF 产物（E255 的 forbid_1）。

## 为什么没有安装 `update-ieee-data`

`update-ieee-data` 是 Debian 的 `/usr/sbin` 运行时维护脚本：shebang 为
`#!/bin/sh`，内部依赖 `mktemp`/`curl`/`wget`/`awk`/`sed` 等 Debian 基础工具，
职责是**在目标机上联网重新抓取 8 个 IEEE URL 并重写数据表**。

OpenHarmony 上没有 `/bin`（E165），`#!/bin/sh` 的脚本在鸿蒙上根本无法启动；
而这些依赖工具与 `standards-oui.ieee.org` 的运行时可达性都不属于本包的交付
范围（本包的交付物是**数据本体**）。因此本包只安装数据表，不安装该脚本与
其 man page —— 这属于有意的技术取舍，不是遗漏。

## 上游测试情况

上游没有测试目录、测试框架或 CI 测试阶段，**上游用例数 N = 0**
（`debian/rules` 只跑 `dh $@`，`Makefile` 没有 `check`/`test` 目标）。

## 新增自检（test_package/test_ieee_data.py，33 条断言）

验证的是数据本体，而不是"文件存在"：

| 断言组 | 条数 | 内容 |
|--------|------|------|
| 文件齐备 | 10 | 8 个数据表 + `.lastupdate` 存在且非空，`share/ieee-data` 目录存在 |
| csv 规范 | 12 | 四个注册表的表头恒为 IEEE 四列；Assignment 位宽分别为 6/7/9/9 hex；Registry 列恒为 MA-L/MA-M/MA-S/IAB |
| txt↔csv 一致性 | 4 | 每个注册表 `.txt` 的 `(hex)` 行数与 `.csv` 数据行数**逐注册表相等**（39630/6451/7064/4575） |
| 真实数据抽查 | 3 | `oui.txt` 含 `28-6F-B9 → Nokia Shanghai Bell`；`oui.csv` 含同一分配的 `286FB9`；`oui.txt` 同时含 `(hex)` 与 `(base 16)` 两种渲染 |
| 规模与时间戳 | 2 | 四表合计 57720 条 ≥ 50000；`.lastupdate` 是合法 Unix 时间戳 |
| 纯净性 | 2 | 安装目录未混入 `Makefile`/`debian/`/`update-ieee-data`；`licenses/` 已发布 |

txt↔csv 行数一致性是本包最有价值的一条：两种形态是同一份数据的两种渲染，
数量不一致即说明数据被截断或混入了不同版本的数据表。

## 构建与验证

```bash
conan create archives/i/ieee-data/20260625 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
python3 scripts/ohc-run.py conan-verify ieee-data 20260625
```

## 来源

- Source URL: `https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/i/ieee-data/ieee-data_20260625.tar.xz`
  （官方路径 `https://deb.debian.org/debian/pool/main/i/ieee-data/ieee-data_20260625.tar.xz`，同一份文件）
- SHA256: `f466a4faf4eacba71340196d1ee7063c37b8ea574d5b9b75d247b8b4b1af8a35`
  （与 `ieee-data_20260625.dsc` 的 `Checksums-Sha256` 一致）
- License: WTFPL-2.0（Debian 维护部分）+ IEEE 注册数据原始条款

---

**编译结束**: 2026-09-19
**最终状态**: built
