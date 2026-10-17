# debian-parl 1.9.33+nmu1 — 适配笔记

## 概述
Debian Pure Blend **DebianParl**（议会/公民桌面工作）。真实身份：**boxer 配方集合**
（新一代 blends 工具链），**native 源包**（Format 3.0）。一个源包生成 5 个
`Architecture: all` 包：parl-data（D-I preseed 配方，唯一有实义内容）+ 4 个纯元包
（parl-desktop/world/eu/strict，本体仅是依赖/冲突声明）。无 C/C++ 代码、无测试套件。

## 真实身份 / 源
- 赛事 task/branch slug：debian-parl-1.9.33-nmu1 / feat/debian-parl-1.9.33-nmu1
- **Debian canonical 版本 = 1.9.33+nmu1**（用户所写 -nmu1 为笔误；NMU 版本用 '+'）
- Conan/recipe 版本 = 1.9.33+nmu1（L0m slug 允许 '+'；L0n 分支 '+'→'-' 归一化；实测通过）
- salsa: https://salsa.debian.org/blends-parl-team/blends（无 1.9.33 tag，NMU；最近 tag debian/1.9.32）
- 源: pool `debian-parl_1.9.33+nmu1.tar.xz`（native; sha 见 conandata，实测）
- 版本漂移：真实包清单由 **boxer-data (>=10.8,<<10.11)=10.10** 决定，上游多次 "simple rebuild"
  即随其变化——本源码不含清单本体。

## 真实 .deb 语义（5 个 0.0.12…/1.9.33+nmu1 .deb 实测，dpkg-deb -I）
| 包 | Depends | Suggests | Conflicts | 内容 |
|---|---|---|---|---|
| parl-data | 0 | 0 | 0 | usr/share/parl/data/{desktop,desktop/eu,desktop/world}/preseed.cfg+script.sh + SHA*SUMS+NEWS+TODO |
| parl-desktop | 54 | 1(strict) | 0 | 仅 usr/sbin/parl-desktop-tidy (shell) + doc |
| parl-desktop-world | 350 | 1 | 0 | 仅 doc |
| parl-desktop-eu | 125 | 1 | 0 | 仅 doc |
| parl-desktop-strict | 1(parl-desktop) | 0 | 21 | 仅 doc |

- boxer 规则：preseed pkgsel include 集→Depends；`-` 后缀 avoid 项→strict 的 Conflicts；
  变体元包 = parl-desktop + (自身 include − 基础 include)。
- profile include/avoid 计数（实测 preseed）：desktop 53/16；eu 177/21；world 402/21。

## Conan 建模（config/metadata 包，零伪造）
- 本源 tar **不含 preseed 成品**（content/ 是 boxer 构建产物，真实数据在 parl-data .deb）。
  为诚实且可复现，本 recipe 不尝试复刻 boxer；package() 装**上游本源的真实配方文件**：
  `share/parl/config/nodes/{desktop,desktop-eu,desktop-world}.yml`（boxer class 引用）、
  `share/parl/config/skel/{preseed.cfg.in,script.sh.in}`、`Makefile/NEWS/TODO` +
  派生 `share/parl/debian-metadata.json`（逐字记录 5 元包 Depends/Suggests/Conflicts 计数与
  profile 语义、boxer-data 约束、源出处；依据官方 .deb，带 provenance）。
- **零 Conan requires**：Depends(54/125/350)全是 OS/发行版桌面软件（metadata-only），
  机械复制会造虚假依赖图；strict 的 Conflicts 记 metadata（Conan 无此概念）。
- test_package：config 文件/class 引用/metadata 计数断言（本地 create 已 PASS）。
- 不上报 preseed 生成物；若需 Debian 语义完整复制，请用 parl-data .deb（本包不含）。

## 上游测试
无（无 autotest；构建期自检 = shellcheck + blends.mk 非空断言）。upstream 0/0；
上述为 Harmony 特有 package/data 验证。

## 诚实边界 / 提示
- 本包实质价值低：软件选择在 boxer-data；元包零文件。按 "data/config 资产入库" 交付，
  不声称能把 DebianParl 桌面"装进 OHOS"。若积分以产出实质二进制为准，本库不适配。
- dep 漂移：上游换 boxer-data 版本即变；本 metadata 钉在 1.9.33+nmu1 实发。
