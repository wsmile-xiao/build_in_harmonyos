# debian-security-support 14+2026.05.07 — 适配笔记

## 概述
Debian-native 源包：程序本体 = 一个 shell 脚本模板 `check-support-status.in` +
每发行版一份安全支持状态数据文件 `security-support.deb{11,12,13,14}`。运行产物
`check-support-status` 报告"哪些已装 Debian 包安全支持已到期/受限"。**无编译、无 ELF**。

## 真实身份 / 源
- 赛事 task/branch slug：debian-security-support-14-2026.05.07 / feat/debian-security-support-14-2026.05.07
- **Debian canonical = 1:14+2026.05.07**（epoch 1: + 上游段 14+2026.05.07；用户写 `-` 有误）
- Conan 版本 = **14+2026.05.07**（epoch 不入 Conan reference，本文件/README.ohos 记录 epoch 1:）
- salsa: https://salsa.debian.org/debian/debian-security-support
- 源: pool `debian-security-support_14+2026.05.07.tar.xz`（native; sha 见 conandata，实测）

## 核心逻辑 vs Debian 集成层（切分，未删核心/未 mock）
- **可移植核心**（原样运行）：读数据文件→与"已装包清单"求交→按行内日期与 `date +%Y%m%d`
  比较→输出 ended/limited/earlyend。数据文件原样随包分发 = 真实知识库。
- **唯一 Debian 耦合**：用 dpkg-query 枚举已装包 → 抽成 `pkglist-probe` 后端
  （capability-detect：DSS_MANIFEST(真实TSV) → DSS_DPKG_STATUS(真实 status) →
  PATH 上的 dpkg-query 原样 exec → 全无则写标记并 exit 3）。
- /etc/debian_version 探测保留（DEBIAN_VERSION 可覆盖）；debconf/systemd/dpkg hook 通知层
  为 Debian 集成，OHOS 不启用（仅命令行工具）。

## 最小诚实补丁（全部在渲染期，保留语义）
1. **反静默假通过**：上游在 dpkg-query 缺失时（管道吞退出码）会 stderr 报错但 **exit 0 +
   空输出**（实测实锤）。补丁：probe 无后端时写 `$TEMPDIR/backend-unavailable`，脚本检测后
   stderr 诊断并 **exit 3**（不伪装"全部正常"）。
2. **grep PCRE 回退**：HarmonyOS 系统 grep 常无 `-P`（本 worker 实测不支持）。数据文件模式
   ERE 安全 → 脚本运行期探测 grep -P，不可用则回退 `-E`。
3. **gettext.sh 可选**：有则 source，无则安装最小 fallback（真实 gettext 程序仍用）。
4. **数据路径可覆盖**：`LIST` 用 `DSS_DATA_DIR:-<包内绝对路径>`，无覆盖时行为与上游一致。

## 打包布局（Conan）
- bin/check-support-status（渲染后，可执行）
- libexec/debian-security-support/pkglist-probe（新写后端）
- share/debian-security-support/security-support.deb{11,12,13,14} + README.ohos
- licenses/copyright
- 运行依赖（部署期保证，recipe 不装）：sh/awk(GNU date -d)/grep(-E/-P)/getopt/gettext-base/coreutils。

## test_package（Harmony 特有 package validation，非上游测试）
- CLI 冒烟 --version/--help
- 供真实数据文件+manifest → ended/earlyend 判定输出与上游 t/ 语义一致
- 无后端（DSS_DISABLE_DPKG=1，无 manifest/status）→ **exit 3**（反假通过）
- 4 份数据文件弱 lint
- 本地 conan create 已 PASS。

## 上游测试 / 诚实申报
- `t/check-support-status.t`（Perl + Test::Command）需 dpkg-query 探测 + gawk/mawk/original-awk
  三选一；autopkgtest 需跑在 trixie。纯 OHOS 不能照跑 → **不在本轮宣称跑了上游测试**；
  其"注入受控包清单"手法被本 test_package 复用做 Harmony 特有验证。

## 路径 B 候选
"Debian package-manager-aware 的 Perl/Shell 工具迁移到 OHOS 的通用兼容模式"
（capability-detect 包清单后端 + 反管道吞码假通过 + 数据随包分发 + 受控清单验证）。
knowledge 查重：无既有条目（dpkg-query/已装包清单 0 命中），仅邻居"OHOS 禁 apt/yum"策略族
与 capability-gap 叙述模板。→ 建议以草稿入 knowledge/drafts（本文件仅记录）。
