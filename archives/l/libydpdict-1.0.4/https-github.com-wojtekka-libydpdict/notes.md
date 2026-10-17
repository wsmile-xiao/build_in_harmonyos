# libydpdict 1.0.4 — HarmonyOS PC

## 来源与版本标识

源码为 wojtekka/libydpdict 官方 1.0.4 发布包，SHA256 为
`37dcbc12def981a20728bdcb6a5ff1eef8931f29a0f16852f0b2201ff8563528`。
用户更正后的归档路径为
`archives/l/libydpdict-1.0.4/https-github.com-wojtekka-libydpdict/`。
按仓库目录一致性要求，Conan 引用为
`libydpdict-1.0.4/https-github.com-wojtekka-libydpdict`；库头文件中的上游版本仍为 1.0.4。
分支从 upstream/main 的 `2446216757be20359617ac140c2e103fac6398f0` 创建。

## 历史经验复核（W0b）

参考同库 `../../libydpdict/1.0.4/` 的配方、补丁和 2026-09-25 记录。
当前真机为 HarmonyOS 6.0、HongMeng Kernel 1.12.0、aarch64，使用仓库
`ci/conan/profiles/ohos-aarch64`，Clang 15.0.4、Conan 2.29.1。
默认构建静态 libydpdict.a，无 Conan 依赖。GNU Libtool 2.4 仅提供构建辅助文件。

保留旧 config.guess/config.sub 的 HarmonyOS 支持和 Libtool 版本匹配处理。
新版将 HMDFS mktemp 辅助文件限制在 OHOS 构建，通过 Conan 工具链传递 PATH，
不修改全局 os.environ 或进程 umask。VPATH 生成头文件路径通过工具链 CFLAGS 传递。
关闭可选 libxml2 探测，避免偶然链接真机上的未声明依赖。

## 上游检查程序清点（R51）

官方 tarball 共 40 个成员。`misc/Makefile.am` 实际声明了四个 check_PROGRAMS：
ydpstress、ydptest、ydpxml、gentable，没有 Automake TESTS 自动运行列表。
ydptest 与 ydpstress 共用 ydpstress.c。顶层 SUBDIRS 不包含 misc，仅 DIST_SUBDIRS 包含它。
因此顶层 make check 本身不会构建或执行这四个程序；本配方额外运行 make -C misc check，
再逐个执行它们。历史记录中“无 check_PROGRAMS”的结论在本次源码复核中被纠正。

两个 misc 源文件的补丁使 YDPDICT_TEST_DIR 可覆盖商业词典的固定安装路径，
未设置时保留上游默认路径。测试数据由 Python 按上游 misc/mkdict.py 的小端格式生成：
四套词典、每套三个词目，包含 Windows1250 字符与 RTF 释义，不携带商业词典内容。
本配置不启用 libxml2，因此 ydpxml 覆盖 XHTML 转换流程，未执行外部 XML/DTD 验证。
gentable 调用真机 iconv 生成字符表。上游程序 4/4 执行成功；这不是商业全量词典覆盖率。

全部四个补丁由仓库 refresh-patch --auto 在真机生成并经过 dry-run。
未修改 configure、Makefile.in 等生成文件。

## 消费者测试

- test.c：9 项真实 API 检查，覆盖 UTF8 转换及 NULL/缺失文件边界。
- test_ydpdict_e2e.c：13 项检查，创建词典文件并查询、读取释义、关闭和删除。
- test_harmony_storage.c：真实 HarmonyOS 内核与用户存储流程。创建中文目录及文件，
  从暂存文件改名安装，调用词典 API 查词、读取释义，关闭后重开并清理全部文件。
  非 HarmonyOS 内核会返回失败；只在 OHOS 配置下构建和执行。

ydpdict_get_word 返回词目；ydpdict_read_rtf 返回需调用方 free 的原始释义字节。
find_word 使用大小写不敏感的前缀匹配。测试按这些上游语义检查。

## 发现与知识积累（路线 B）

- ✅ 新增成对草稿 `knowledge/drafts/E14722-draft-YDPB.kv/.md`：Automake 的分发目录与递归构建目录不同，发布包携带 misc 检查源码但顶层 make check 漏构建；无 TESTS 时还须显式执行。实际首轮 shell 127 及修复日志按原始字节保存在 reports，草稿记录 SHA256。
- ✅ 已撞库 E589-draft-libfshfs-check-programs-runner-dispatch：该草稿覆盖“已构建、未派发”。本轮新知识覆盖更早的“目录不递归、未构建”，并记录两阶段修复；MD 有逐项撞车判定，KV 的 similar_to 引用相关草稿。
- ✅ 复用 `knowledge/drafts/E543-draft-A443.kv` 的同库 Libtool 版本匹配修复，不重复提取。
- ✅ 复用 E011、E528 的 HMDFS 临时目录与 Autotools 环境闭包，以及 E525 的串行 Make；具体应用是现有 recipe-local mktemp 辅助文件和工具链设置。
- ✅ 新增 `build_support/verify_upstream_census.py`，只读并校验固定官方发布包，不解包；输出 SUBDIRS / DIST_SUBDIRS / 四个 check_PROGRAMS / 无 TESTS。三项本地诊断测试通过，未并入上游或消费者运行测试数量。

路线 B 为已有库修订与新知识贡献；本轮不声称解除其他软件的下游依赖阻塞。
草稿通过仓库 graph add --draft 生成，未晋升或修改正式知识条目、索引、他人归档。
运行日志中的旧路径仅用于首次故障与修复来源，更正后的 Conan / W3 回执单独保存。

## 构建记录与限制

2026-10-03 按更正后的目录和 Conan 引用重新进行真机原生构建。
conan-verify 的 Conan create 和 W3 的 Conan create 均返回 0；
上述四个上游程序和三个消费者可执行文件全部通过。
构建使用独立 Conan 缓存；官方源码先在 Windows 经 HTTPS 下载并核对 SHA256，
再传入真机 Conan 下载缓存，配方保留官方 URL，未携带源码压缩包或二进制到归档。

旧路径首次适配时因顶层 make check 未构建 misc 检查程序而失败；
显式构建 misc 后通过，本轮新路径验证保留该修正。
上游 misc 文件有 Clang 指针符号警告，未改变库 API；测试构建的 GNU Make 并行 jobserver
在 HMDFS 上提示 mkfifo 不支持，但编译完成且退出码为 0。库自身已按 OHOS 使用串行 Make。

ohpcd registry 的版本占用检查返回 `system acceleration policy not enabled`，无法确认远程占用。
仓库 result.json 协议拒绝超过 32 字符的版本号；更正后的指定版本仍有 36 字符。
旧路径测试使用的版本有 42 字符，当时工具未写入回执。
本次保留用户要求的目录名，不修改共享工具或绕过协议手写结果。

## 目录更正首轮验证记录（路线 B 复验前）

仓库 conan-verify 返回 0，Verdict PASS。其 G4 包 ID 查询未能解析该引用，
已独立查询真实 package ID `4b977264131a1c74e82bd6bb51b63cc9aadc4cfa`，
确认静态库内对象为 ELF64 AArch64、14 个公开 ydpdict 符号，头文件及 LGPL COPYING 齐全。

finish 内嵌 W3 的 setup.sh 与 build_and_test.sh 返回 0，1/1 目标包成功。
L0/L1/L5=pass，L2=skip（纯库无 bin），L4=warn（config.guess 上游上下文的字符串函数）。
CI 的 L0m 目录检查和 L0n 分支名检查均通过。负向测试在移走库及头文件后失败，
恢复后正常，确认消费者依赖真实包。
本轮工具生成的 .ci-result.json 保留在本地，integrity_hash 为
`d3417d915507134e`，w3-local-ci.log SHA256 为
`3e452596fcbe1d040d71f1759a493506093c6635fbf2bbcf6c90007804e67579`。

PackageBuilder 静态打包返回 0，交付文件为 packaging/ 下
`libydpdict-1.0.4-https-github.com-wojtekka-libydpdict-ohos-aarch64.tar.gz`。
本轮归档 SHA256 为
`8f27d6255f543e4d5dc9e567c2316d40d422bbd1f0ee9d0b7e9f0e1e3440d4bd`。
这是 Release 静态库包；未伪造单独调试符号包。Conan 消费者使用已验证的
`find_package(libydpdict REQUIRED)` 和 `libydpdict::libydpdict` 目标。

本轮完整 finish 返回 1，不宣称全部收尾门禁通过：W5 对共享知识库 E219/E253/E305 的多行字段判空，
以及运行当时的 PR 前置产物检查未全部满足。后续补齐了本轮测试报告和真实打包产物。
通用 G0 clean-verify 应用四个补丁成功，但 configure 报
`working directory cannot be determined`，原始 g0-configure.log 已保存。
旧路径独立验证曾报 subs1.awk Permission denied；两轮错误分别保留，不混用。
该通用工具不执行本配方的 generate()/source() 辅助准备。
共享脚本及知识字段未修改，未伪造门禁标记。

W3 工具会临时注入下载镜像；本轮远端 conandata.yml 导出件仍带镜像列表。
已检查测试配方的 Python 内容与本地逐字一致，下载源 SHA256、补丁声明及官方备用 URL 一致。
本地交付配方只保留官方 URL。原始远端导出件和驱动日志保存在
`tmp/libydpdict-pathfix-evidence/`，用于核查工具改写及本轮实际结果。

## 需求记录

用户要求以 upstream/main 为基准创建指定 feat 分支，按上述更正后的目录保存移植，
完成 aarch64 本地 CI、Conan 及至少一个非纯断言的鸿蒙专有测试。
已按用户确认的真机地址完成测试。移植文件只新增在 libydpdict-1.0.4 归档下，
历史 xplot 本地改动继续保存在原 stash 中。

目录更正时保留了旧路径的完整测试证据到 `tmp/libydpdict-path-correction-baseline/`。
旧 .ci-result.json 未修改或复用于新路径。Conan 包标识按目录更正，同时显式保留
libydpdict 的 CMake 文件名和消费者目标；上面的最终验证记录全部对应更正后的路径。

**编译结束**: 2026-10-03
**最终状态**: built

## 路线 B 本轮复验与提交门禁

本节对应新增草稿与清点脚本后的最新验证；前文“目录更正首轮”记录仅保留历史证据。
实际 W3 工具真机时间为 `2026-10-03T11:17:18.178064`，返回 0；原生 aarch64 重构建并运行四个上游程序 4/4、三个消费者 3/3，含真实鸿蒙中文用户存储流程。L0m、L0n 均执行并通过；移走头文件/库的负向测试按预期失败，恢复成功。

最新 `.ci-result.json` integrity_hash 为 `365c2bdf9dfc881b`，
W3 原始日志 SHA256 为 `c0c5f7497b4345777d56b0980af1dcc35308fac51a0173014b00c866436db618`。
最新工具生成的 Release 静态交付包 SHA256 为 `2844ab692b97dc2c2a5c952a1aff3ec1fcddc88d2f3a6038978e0fcc947ae801`。
真实制品检查确认 ELF64 AArch64、14 个公开 ydpdict 符号、头文件和 LGPL COPYING。

Conan 验证返回 0；源码清点诊断 3/3 通过，不并入运行测试分母。
独立审计指出的旧注释与文档 CRLF 已修正；mktemp 辅助脚本增加兼容 shell 的安全模式、默认模板参数，以及 chmod 失败时清理并返回非零。
权限失败测试先在原脚本实测为失败（脚本误报成功），修复后真机 4/4 辅助诊断通过，含真实 HMDFS 目录内写文件。原始前后日志保存于 reports/route-b-mktemp-before-fix.log 与 after-fix.log，未混入上游/消费者运行分母。
归档知识遗漏检查返回 0（5 项提取、5 项有效引用、无待处理或未引用）。
仓库 BuildDriver 的真实 staging 步骤生成 `verified=0 failed=0`：纯库没有 CLI，因而是 0/0 个 `--version` 检查；库内容另由 VerifyBuild、真实消费者及 LLVM 工具验证，不把该标记声称为运行测试通过。

完整 finish 实际返回 1，唯一失败步骤为 step5b：共享 W5 扫描器将基线 E219/E253 的 root_cause、E305 的 root_cause/rec_approach 的首行块标记视为空；这些字段下的正文实际存在。归档自身检查与 submit 产物就绪检查均通过。
通用 G0 的 configure 验证仍失败并在 finish 中作为警告保留；实际 Conan/CI 流程执行配方的辅助准备后成功。
结果工具仍拒绝用户指定的 36 字符版本（上限 32），本轮真实日志保存在 `reports/push-finish.log`，未伪造 result.json。
独立运行 PR preflight 还发现 PF9 将软件级 README.md / manifest.yaml 判为缺少版本层；但根 SKILL §6 和 ARCHIVE-SPEC 要求这两个文件位于软件级。该共享门禁与归档规范冲突，原始输出保存于 reports/preflight.log，不通过删除必需文件或修改共享脚本绕过。

根 SKILL 和补充知识扩展 SKILL 禁止协作者修改共享脚本、正式知识；因此本提交只包含一个软件及自己的草稿，完整 finish 未通过前不发布 PR。
PR 标题及正文已按“【知识库扩展】/路径 B（贡献创新）”和积分赛事模板准备在本地报告目录，待门禁满足后使用。

## 推送前文件范围整理

按 ARCHIVE-SPEC 补齐软件级 manifest.yaml，并将软件级 README 整理为功能、适配、依赖和参考资料；版本配置与过程证据放在本版本归档。
归档中的废弃 packaging/、.verify-passed 和 .staging-verified 已移出到忽略的任务临时目录保存原始证据。
最终变更清单为 22 个文件，仅一个软件 archives/l/libydpdict-1.0.4/ 及 E14722-draft-YDPB 成对草稿；日志、二进制、运行标记、临时补丁与共享基础设施均不在提交清单内。
三个 build_support 文件均保留：generate_fixtures.py 和 mktemp 为真实构建/测试输入，verify_upstream_census.py 为路线 B verification_cmd 的复算输入。
本轮 Conan、W3 和制品检查使用原始仓库工具重新执行；测试输入与本地配方、辅助文件、补丁及消费者源逐字节一致。
按用户本轮明确指示，推送同名功能分支供审核并在聊天区提供 PR 文本。正式发布门禁仍为阻断状态，版本号保持用户指定值。
