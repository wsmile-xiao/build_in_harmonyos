# E14722 草稿 — 发布包有检查源码，默认递归却漏掉检查目录

## 适用条件与可迁移边界

Automake 将“进入发布包”和“进入当前递归构建”分开控制。发布包中存在测试源码不等于默认 `make check` 会构建它们。
先检查 `SUBDIRS`、`DIST_SUBDIRS`、目录 `Makefile`、`check_PROGRAMS` 和 `TESTS`；有条件变量时还须核验 configure 的实际分支。本草稿的示例是无条件的字面赋值，清点脚本只支持这个固定版本，遇到变量展开、多行或重复赋值即拒绝，不能当通用 Automake 解释器。

## 真实错误与根因链

源码：[官方 1.0.4 发布包](https://github.com/wojtekka/libydpdict/releases/download/1.0.4/libydpdict-1.0.4.tar.gz)。
SHA256：`37dcbc12def981a20728bdcb6a5ff1eef8931f29a0f16852f0b2201ff8563528`。

```make
# Makefile.am
SUBDIRS = include src pkgconfig
DIST_SUBDIRS = include src pkgconfig misc
# misc/Makefile.am
check_PROGRAMS = ydpstress ydptest ydpxml gentable
# 没有 TESTS 赋值
```

最初原生 Conan 构建日志（旧归档标识；仅作为故障来源，不充作更正路径的新回执）：

```text
Making check in src
make[1]: Nothing to be done for 'check'.
Running upstream check program: ydpstress
/system/bin/sh: .../build-release/misc/ydpstress: inaccessible or not found
ConanException: Error 127 while executing
```

根因依次为：misc 只进入分发集合 → 顶层递归没有 misc → `make check` 返回 0 但检查可执行文件不存在 → 显式执行触发 shell 127。不是查词 API 失败或商业词典缺失。构建 misc 后还必须解决第二层派发：没有 `TESTS`，所以目录内 `make check` 只构建检查程序，不能代替执行。

## 推荐方案（已验证）

1. 以校验过的发布包为准清点：40 个 tar 成员、4 个 `check_PROGRAMS`，其中 ydptest/ydpstress 共享源码，不能少计其独立可执行入口。
2. 保持顶层 `make check`；从 VPATH 构建根执行 `make -C misc check`，使用已生成的目录 Makefile 和当前工具链。
3. 原生构建时生成真实字典格式的合成数据，以 `YDPDICT_TEST_DIR` 给两个上游源码覆盖数据位置；四个程序逐一执行并校验返回码。未设置变量时保留上游默认位置。
4. 交叉构建仅报告检查程序已编译；运行结果必须在目标设备补充。当前配方使用 host/build 同为 OHOS armv8 的原生 profile，完成了实际执行。

本库 `ydpxml` 未启用可选 libxml2，覆盖转换流程，不声称完成外部 XML/DTD 验证。合成词典每套三词目，不声称商业词典全量覆盖。

## 回退与禁止策略

若上游要修复默认递归，可以将目录纳入 `Makefile.am` 的活动 `SUBDIRS`，用匹配版本工具重生成；若已有 runner，则遵循原 runner 的参数/环境。该回退方案尚未在本库实测。

禁止将顶层返回 0 或 `0/0` 当作所有上游测试通过；禁止删除 check_PROGRAMS、直接改生成的 Makefile.in、用新增纯断言替代上游程序。不能把“构建成功”“runner 通过”“程序执行数”混成一种单位。

## 相关既有条目与撞车判定

| 既有条目 | 已覆盖机制 | 本草稿增量与关系 |
|---|---|---|
| E589-draft-libfshfs-check-programs-runner-dispatch | check_PROGRAMS 已被构建，但 shell runner 列表为空，4 程序未派发 | 本例在派发之前即漏构建：目录不在 SUBDIRS，且无 TESTS。先恢复目录 check 构建，再实际执行。部分相关，记入 similar_to |
| DRAFT-10251-libnfc-tools-1.8.0-autotools-test-framework-guard | Cutter 缺失导致 configure 条件禁用测试目标 | 本例无框架依赖/条件禁用；源码和目录 Makefile 存在，递归集合遗漏。不是补框架方案 |
| DRAFT-no-upstream-tests-drive-real-interface | 上游确实没有可用测试时补真实接口测试 | 本例有四个上游检查程序，必须恢复并执行，不能申报 N=0 |
| E543-draft-A443（同库） | 发布包 Libtool 宏与 ltmain.sh 版本不一致 | 已复用其辅助文件修复；与测试目录遗漏独立，不重复提取 |
| jool-modules-lts 的 DIST_SUBDIRS 草稿 | 分发内核模块但不能交付目标内核模块 | 对象是内核 ABI/交付边界，不覆盖 Automake 检查目录与运行派发 |

本次检索正式索引、知识文档及草稿后，没有发现覆盖这条完整机制链的条目。正式条目与他人草稿保持原状，仅提交这对草稿给主编审核。

## 可复算验证

在仓库根执行，下列源码文件由官方 URL 下载并核对上面的 SHA256；Conan 步骤在具备仓库原生工具链的 HarmonyOS aarch64 设备运行：

```sh
python3 archives/l/libydpdict-1.0.4/https-github.com-wojtekka-libydpdict/build_support/verify_upstream_census.py --source-archive libydpdict-1.0.4.tar.gz
conan create archives/l/libydpdict-1.0.4/https-github.com-wojtekka-libydpdict -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build="libydpdict-1.0.4/*" -nr
```

第一条只复算源码清点，不证明运行成功。第二条强制重构建，并应看到四条 `Running upstream check program:` 及正常退出，随后真实消费者 `consumer e2e: OK (13 checks)` 与 `HarmonyOS storage workflow: OK`。不要以单条程序开始日志代替其退出码和整次 Conan 返回码。

## 实测证据与归属

归档证据目录：`archives/l/libydpdict-1.0.4/https-github.com-wojtekka-libydpdict/reports/`（日志/制品按仓库忽略规则本地保存）。

- 首次故障原始日志 `upstream-checks-before-fix.log`，SHA256 `0c2a8fc0f82a4e5b82628a8c311c78c6403c779e215e19a7c584c05dd7466ac8`。
- 首次修复原始日志 `upstream-checks-after-fix-original.log`，SHA256 `53e8a7f7d2e949b74d3708935eaa243a24eba7b0763b130e88fe15db6e68d05a`，四个上游程序及消费者实际运行；两份均从旧路径原始导出 tar 按字节保存。
- 更正目录的新验证：`conan-create.log`、`w3-local-ci.log`；工具 `.ci-result.json` 内含实际 W3 日志 SHA256，身份为 `libydpdict-1.0.4/https-github.com-wojtekka-libydpdict`。
- `upstream-census.json` 可由发布包清点脚本重新生成。它的“40 成员/4 程序/无 TESTS”不增加运行测试分母。
- 目标设备 HarmonyOS 6.0、HongMeng Kernel 1.12.0、aarch64；3 个消费者可执行文件含 9 项 API 检查、13 项文件端到端检查及 1 个真实中文用户存储安装/改名/重开/清理流程。

作者 Tillthen；通过 `graph add --draft` 生成，仅为未晋升草稿。当前提交必须保留完整 finish / 独立 W4 审计的实际结果；未通过共享门禁时不声称已提交 PR。
