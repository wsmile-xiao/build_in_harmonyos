# DRAFT-debian-security-support-14+2026.05.07-dpkg-aware-tool-portability

> Debian package-manager-aware Shell/Perl 工具迁移到 HarmonyOS 的通用兼容模式
> 实例：`debian-security-support` 14+2026.05.07（Debian canonical `1:14+2026.05.07`）
> PR #9223 ｜ commit `89d0a015cf` ｜ HarmonyOS PASS ｜ CI PASS

## 问题 (Problem / Trigger)

Debian 运维/查询类工具把「操作系统包管理器」当作默认数据后端。`debian-security-support`
的程序本体是一个 shell 脚本（`check-support-status`），核心逻辑 = 读发行版安全支持数据文件
`security-support.deb{11..14}` → 与「已装 Debian 包清单」求交 → 按行内日期与今天比较 →
输出 `ended/limited/earlyend`。它在 HarmonyOS 上遭遇以下能力缺失/行为差异：

| 依赖 | Debian 侧 | HarmonyOS worker 实测 |
|---|---|---|
| dpkg-query（枚举已装包） | 默认后端（读 /var/lib/dpkg/status） | 不存在 |
| `/etc/debian_version`（选数据文件） | 存在 | 不存在（`cat: No such file`） |
| `grep -P`（PCRE，交集匹配） | GNU grep 支持 | `grep: Perl matching not supported in a --disable-perl-regexp build` |
| `gettext`/`gettext.sh`（本地化） | gettext-base | 二进制因 `libintl.so.8` 无法重定位而不可用 |
| `mktemp --tmpdir --directory ...XXXXX` | GNU mktemp | 部分 OHOS worker 拒绝 `--tmpdir`/模板长度 |
| Debian 文件系统标志 | 存在 | 不存在 |

## 根因 (Root Cause)

1. **包管理器耦合**：软件把 dpkg-query 当默认数据后端——领域核心可移植，但「枚举已装包」
   这一 I/O 被写死为 Debian 专属实现。
2. **静默假通过（最危险）**：上游把 dpkg-query 放进管道
   `dpkg-query ... | awk ... | awk ... > "$INSTALLED_LIST"`，管道退出码取自末位 awk；
   dpkg-query 缺失时被吞 → **stdout 空 + exit 0** = 伪「没有受影响的包」。本批已在本机与
   真机实锤（stderr 报错但 exit 0）。
3. **GNU-only 参数不可移植**：`grep -P`、`gettext.sh`、`mktemp --tmpdir` 并非普遍可用。
4. **发行版/平台标志缺失**：`/etc/debian_version` 不存在导致选数据文件落空。
5. 结论：不是「Shell 不兼容」这么简单，而是**「默认后端假设 + 失败语义错误 + GNU 参数假设」**
   三者叠加，必须以真实能力探测 + 诚实失败来迁移。

## 通用方案 (Portable Solution)

**切分可移植核心 vs Debian 集成层（不删核心逻辑、不 mock、不固定成功）：**

1. **包清单后端抽象 `pkglist-probe`（capability detection，优先级）**
   `DSS_MANIFEST`（真实 TSV 清单） → `DSS_DPKG_STATUS`（真实 dpkg status 文件，awk 真解析）
   → PATH 上的 `dpkg-query`（原样 exec，Debian/chroot/容器语义不变） → 全无则写 marker 并
   **exit 3**。
2. **反静默假通过（最小诚实补丁）**：probe 无后端时写 `$TEMPDIR/backend-unavailable`；
   主脚本在管道**之后**检测 marker → stderr 诊断 + **exit 3**。正常 Debian 路径与提供清单的
   路径行为完全不变。
3. **`grep -P` → 运行期探测 + `-E` 回退**：`command grep -P -q 'x' /dev/null` 探测；
   数据文件模式 ERE 安全，回退无损。
4. **gettext 可选**：不 source 不可用的 `gettext.sh`、不调用坏 `gettext` 二进制；内建最小
   `gettext()/eval_gettext()`（保留英文消息），i18n 不承重。
5. **mktemp POSIX 回退**：`mktemp -d "$TMPBASE/...XXXXXX"`（$TMPDIR||/tmp）+ 显式二次回退。
6. **数据目录可覆盖**：`DSS_DATA_DIR`（默认包内绝对路径），保持 relocatable。
7. **核心判定真实执行**：数据文件随包原样分发（=真实知识库），判定逻辑不改。
8. **Conan 侧**：python 渲染模板占位符（VERSION/AWK/DPKG_QUERY/LIST），无需 perl/tpage；
   零 requires；运行依赖（sh/awk/GNU grep/date/getopt/gettext-base）部署期声明，**不在 recipe 里 apt 安装**。

## 验证 (Verification，真实证据)

- **本地主机** conan create：test_package PASS。
- **HarmonyOS PC（aarch64）** conan create + test_package PASS（首跑因 gettext/libintl/
  `/etc/debian_version` 失败 → 按真机差异修复后 PASS，最终 commit `89d0a015cf`）。
- test_package 断言：`--version`/`--help`；供 `DSS_MANIFEST` + 受控数据（过去/未来/limited/
  supported 行）→ `--type ended/earlyend` 输出与上游 `t/` 语义一致；`DSS_DISABLE_DPKG=1`
  且无后端 → **exit 3 且 stdout 空**（反假通过）；4 份数据文件弱 lint。
- **CI**（AtomGit PR #9223）PASS；`current == harmony == ci == 89d0a015cf`。
- 诚实边界：**本轮没有**把上游 Perl `t/check-support-status.t`（需真实 dpkg-query + gawk/
  mawk/original-awk）写成已完整执行；autopkgtest 需 trixie。上述为 Harmony 特有 package
  validation，复用上游「受控包清单注入」手法。

证据文件：`ohos-farm/runtime/research/debian-security-support.md`、
`ohos-farm/logs/harmony-verify/debian-security-support-14-2026.05.07-WIN01-89d0a015cf13.log`、
PR #9223、recipe `archives/d/debian-security-support/14+2026.05.07/`。

## 适用范围 (Applicable)

- Debian 系运维/查询工具、dpkg-query 依赖脚本、apt/dpkg-aware CLI、包清单/支持状态分析工具、
  OS 包数据库消费者、Shell/Perl 运维脚本。
- 更一般：任何「枚举系统状态 → 判定」型工具，在系统能力缺失平台上需要诚实迁移者。

## 不适用 (Not Applicable)

- 包管理器本体或必须真正执行 apt/dpkg 安装/删除事务的软件（事务语义不可抽象）。
- 无法把数据后端抽象出来、核心逻辑本身即 dpkg 事务的工具。
- 仅 build-time 使用 dpkg 的项目（构建期依赖，与运行时迁移无关）。

## 与既有条目查重 (Dedup)

- `dpkg-query` / `installed package list` / `blends` / `metapackage` / `Suggests`：
  knowledge/ **0 命中**（`dpkg` 仅 1 处 `operations/dependencies.md`：dpkg 作为 lzma 消费者）。
- 邻居（非等价）：E507（可选 pthread 能力探测）、E220（权限/文件系统探测）、
  E071/E089/E157/E414/E425（OHOS 非 Debian/Ubuntu，禁 apt/yum 策略族）。
- 无等价条目 → **新立条目**。

## 潜在复用 (Potential Reuse，仓库真实命中)

- `archives/a/apt-dater-host/1.0.1`（apt-dater 主机侧助手，apt/包清单感知）
- `archives/a/alien/8.95.9`（rpm/dpkg 包格式转换，纯 Perl）
- `archives/d/debconf/1.5.77`、`archives/c/cdebconf/0.283`（Debian 包配置系统，纯 Perl）
- `archives/d/debianutils/5.23.2`（run-parts/tempfile/ischroot 等 Debian 专属脚本/工具）
- `archives/a/adcli/0.9.2`、`archives/b/base-installer/1.229`、`archives/d/dpkg/1.23.7`、
  `archives/l/libdpkg-perl`（dpkg/安装器相关）
