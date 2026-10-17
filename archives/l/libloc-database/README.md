# libloc-database

IPFire Location Database —— `libloc` IP 地理位置查询库所使用的**编译后数据库**（`location.db`）。

本仓收录该数据库的 Conan 配方：把上游按日期发布的 `location-<version>.db.xz` 解压后，
安装到与 Debian 官方包一致的 `share/libloc-location/location.db`。

## 功能概述

- 提供 IP 地址 → 地理位置（国家/ASN/网络）的查询数据，供 `libloc` 库加载
- 上游以"编译好的二进制 DB + 日期版本号"发布（如 `location-2026-06-28-03:45.db.xz`），
  数据在发布前已完成编译与签名，使用者只需安装、无需构建
- 数据库格式版本 1，魔数 `LOCDBXX\x01`

## OHOS 适配要点

| 项 | 说明 |
|---|---|
| 构建系统 | 无（纯数据包）。上游无 Makefile/CMake/meson/configure |
| 编译 | 不需要；`conan create` 只做"下载 → 解压 → 安装 → 校验" |
| 安装路径 | `share/libloc-location/location.db`（对齐 Debian 官方包，libloc 的数据库查找目录） |
| 压缩格式处理 | 上游发布物是**单个 `.xz` 压缩文件**（不是 tar 归档）。conan 的 `get()/unzip()` 只识别 tar/zip，裸 `.xz` 会落到 `zipfile` 分支抛 `BadZipFile`，因此配方用 `download()` + Python `lzma` 流式解压 |
| 落盘文件名 | 上游名字含冒号（`location-2026-06-28-03:45.db.xz`），`conandata.yml` 用 `filename: location.db.xz` 归一化 |
| 源码源 | 上游 `location.ipfire.org` 在 CI Worker 上不可达（构建 #48346/#48351 实测），故取 Debian 官方源码包（orig.tar.xz）的权威镜像源（TUNA 主 / USTC 备）——其 `location.db` 与上游发布物逐字节一致，打包期仍按固定 size+SHA256 校验 |
| commands.json | 不适用（无 CLI 工具，R38 仅对可执行产物适用） |

## 依赖关系

- 编译依赖：无（`debian/control` 的 `Build-Depends` 只有 `debhelper-compat (= 14)`，属 Debian 打包工具）
- 运行依赖：无（官方二进制包 `control` 无 `Depends`，`Architecture: all`）
- 反向依赖：`libloc` / `libloc1t64`（`Recommends: libloc-database`）——即本包是 libloc 的数据依赖，反之不成立

## 上游测试

上游**没有自动化测试入口**：数据仓只有数据与 README（README 声明本仓仅供审计，
数据"不是机器友好格式"）；Debian 打包仓无 `debian/tests`。测试入口、构建文件存在性的
逐项核验证据见版本目录的 `reports/test-report.md`。

## 参考资料

- 官网/下载：https://location.ipfire.org/databases/
- 数据仓：https://git.ipfire.org/?p=location/location-database.git
- 打包仓：https://salsa.debian.org/debian/libloc-database
- 使用方（libloc 库）：https://git.ipfire.org/?p=location/libloc.git
- Debian 包页：https://packages.debian.org/sid/libloc-database
