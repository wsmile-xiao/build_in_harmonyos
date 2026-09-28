# SKILL_FEEDBACK — xtail/2.1

## 背景
- 软件/版本：xtail 2.1；构建系统：Autotools（预生成 configure + Makefile）。
- 上游仓库：`https://salsa.debian.org/debian/xtail.git`，取 `upstream/2.1` 官方标签。
- 适配路径：路径 B（1 份 POSIX 可移植性源码补丁）；Conan 外部依赖 0，系统 libc。
- 本地状态：built（交叉编译 + Conan 验证 + W3 均成功，未向仓库发布）；PR/远程 CI：建 PR 前尚未触发。

## 情况
| 阶段 | 结果 | 实测说明 |
|---|---|---|
| init-build | 成功（换官方标签归档后） | 仓库 `.git` URL 返回 HTML，不适合下载器；Salsa 上游标签归档 SHA256 双次一致。 |
| 编译 | 成功 | 初次缺 `autoconf`（源码预生成脚本时间戳）、缺 `MAXNAMLEN`；保留预生成脚本并补带边界检查的 PATH_MAX。 |
| conan-verify | 通过 | 首次 G2 因 out-of-source `config.h` 路径缺失失败，修正 Toolchain 私有 build_folder include 后重验通过。 |
| finish/W3 | W3 通过；finish 存在非阻塞旧告警 | 首次 L1e 发现完全跳过无法验证包，改为先检查交付 ELF；第二次 L0/L1/L5 通过，L1e 删除 bin 后失败符合预期。G0 旧脚本未注入 cross CC 而失败，另有旧 packaging 提示、生成摘要异常。 |
| W4/PR/CI | 待审计及触发 | 不把未得到的机器人检视/CI 结果填作通过。 |

- 测试清点：上游 `tests/` 0、CTest/pytest 0，`make check` 无目标；上游测试 0/0，不报虚构通过率。x86 上 `test_package` 确认 AArch64 ELF 有效及包存在，原生功能部分 skip（0/1）；同源码目标文件静态重链副本在 QEMU 执行文件追加与长目录发现 2/2，通过不等于交付动态 ELF 实跑。CI 原生功能测试待远端审查。
- 知识图谱：引擎先后命中 E232/E032/E540，分别与本次的缺 autoconf、`MAXNAMLEN` 溢出、out-of-source config.h 问题不符；`draft-review` 提示 E500 (0.42) 但其 `MAX_INPUT` 不同。新增仅草稿 `E550-draft-D79C`，知识图谱验证通过（全仓存量警告 169 项未改）。
- AI 检视：尚未生成摘要/意见，意见数未知；无须假装已闭环。远端 CI 尚未触发；本地 W3 L2 对无 `--help/--version` 的历史 CLI 标记 skip，L4 源码危险函数扫描仅 warn。
- HANDOFF：首次 W3 L1e 一次阻塞，缺省 G0 与旧式 packaging 为非阻断提示；有效调整包括换源码归档、补路径长度、补生成头路径和补 L1e 被测包关联。
- 耗时瓶颈：预生成 Autoconf 时间戳触发再生、Conan out-of-source 与旧 Makefile -I$(srcdir) 不一致；QEMU 只用于同源静态重链副本，不重试本机无法运行的动态 ELF。

## 建议
### SKILL 设计改进
`scripts/ohc/finish.py:373-386` 将 Conan CLI 包仍强制列出 `packaging/` 与 staging 缺失，尽管 `packaging/` 已废弃；将打包就绪只应用于旧制品流，并优先使用 W3 的 `.ci-result.json` 证据，避免 `finish` exit 1 被误认 W3 红。

### 模板改进
`templates/conanfile-autotools.py.tmpl` 生成时默认 `package_type=library`、静态共享开关和非版本键 `sources`，而本例是只有 bin 的 CLI；增加 CLI 变体：`package_type=application`、`cpp_info.bindirs`、`sources[self.version]`，并令 `test_package` 真正使用包内二进制。新手复制骨架时不能留下空壳 `test.c`。

### 自动化补全
`conan-init` 未自动核验源码 SHA256、生成的 conandata 留 `REPLACE_WITH_ACTUAL_SHA256`；初次 `init-build --url=...git` 下载 HTML，建议入口识别 Git 仓库 URL 并提示选上游 tag tarball。`scripts/ohc/feedback.py:451-468` 自动把 manifest `built` 写成「最终成功」，把构建系统写为 `{BUILD_SYSTEM}`、补丁数量写 0、上游写未知，且漏掉上游无测试/本机 x86 功能 skip；从真实源码、manifest、W3 与测试报告提取再渲染，不能误记 skip 为通过。`scripts/ohc/finish.py:336-345` 的 `gen_summary` 在本机报 `'str' object has no attribute 'append'`，建议隔离异常并打印准确字段来源。

### 知识图谱覆盖
新草稿 `knowledge/drafts/E550-draft-D79C.{kv,md}` 记录 `MAXNAMLEN` 被拿来分配**完整**路径的编译错误与缓冲区溢出风险，附 255 字节以上路径的 QEMU 实测。引擎对 `config.h file not found` 命中 E540（runner PATH），实际是 Autotools out-of-source 时只加 `-I$(srcdir)`；建议检索排序加入 `config.h` 与 `build_folder` 特征，并由主编评估是否新增独立条目；本 PR 不修改正式图谱。

## 作者
- 姓名：nyaco3
- 邮箱：aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- Agent ID：69FE
- 生成时间：2026-09-24 22:05:14 PDT
- PR 编号：建 PR 前尚未分配（报告已于初次提交前闭环）
