# debian-security-support

Debian 的安全支持状态检查工具 `check-support-status`（纯 shell）：读每发行版的安全支持
数据文件，与"已装 Debian 包清单"求交，报告哪些包的 security support 已结束/受限/即将结束。
本仓库适配为 **shell 工具 + 数据包**（无编译）：核心算法原样运行，唯一 Debian 耦合
（dpkg-query 枚举已装包）抽成 capability-detect 的 `pkglist-probe` 后端。

## 上游
- salsa：https://salsa.debian.org/debian/debian-security-support
- Debian 源包：`debian-security-support_14+2026.05.07.tar.xz`（native）

## 版本
- 赛事 task/branch slug：`14-2026.05.07` / `feat/debian-security-support-14-2026.05.07`
- Debian canonical：**`1:14+2026.05.07`**（epoch 1: 不入 Conan reference，见 notes）
- Conan / recipe：`14+2026.05.07`

## 用法（OHOS）
```
check-support-status                      # 需后端提供已装包清单，否则 exit 3
DSS_MANIFEST=real-list.tsv check-support-status
DSS_DPKG_STATUS=/var/lib/dpkg/status check-support-status   # 解析真实 status
```
数据目录可用 `DSS_DATA_DIR` 覆盖（默认包内 share）。详细语义见
`share/debian-security-support/README.ohos` 与 notes.md。

## 说明
- 纯 OHOS 无 dpkg 数据库，"扫描本机已装 Debian 包"无真实语义 → 工具在无后端时**明确失败**
  （exit 3），不空报"一切正常"。
- 上游测试套件需 dpkg/三种 awk/trixie，本轮未在 Harmony 照跑；test_package 为 Harmony 特有
  package validation（受控清单核心判定 + 无后端诚实失败）。
