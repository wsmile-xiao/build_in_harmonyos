# debian-parl

Debian Pure Blend **DebianParl**（议会/公民桌面工作）。真实身份是 **boxer 配方集合**
（新一代 blends 工具链）：一个 native 源包生成 5 个 `Architecture: all` 包——
`parl-data`（D-I preseed 配方，唯一有实义数据）+ `parl-desktop` / `-world` / `-eu` /
`-strict`（纯元包，本体仅依赖/冲突声明，无编译产物）。真实包清单由独立源包
`boxer-data`（10.10）决定，本源码不含清单本体。

本仓库将其适配为 **config/metadata 数据包**：装 3 个 boxer node（class 引用）+ 2 个
skel 模板 + Makefile/NEWS/TODO + 派生 `debian-metadata.json`（记录 5 元包真实
Depends/Suggests/Conflicts 计数与 profile 语义，出处为官方 .deb）。**零 Conan requires**。
> 注：本 recipe 打包的是"配置/元数据资产"，**不含** boxer 生成的 preseed 成品
>（真实产物在 parl-data .deb）；它不代表能在 OHOS 上复现 DebianParl 桌面。

## 上游
- 权威仓库：https://salsa.debian.org/blends-parl-team/blends
- Debian 源包：`debian-parl_1.9.33+nmu1.tar.xz`（native；1.9.33 为 NMU，无 salsa tag）

## 版本说明
- 赛事 task/branch slug：`1.9.33-nmu1` / `feat/debian-parl-1.9.33-nmu1`
- Debian canonical / 本 recipe 版本：`1.9.33+nmu1`
