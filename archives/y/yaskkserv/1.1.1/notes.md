# yaskkserv 1.1.1 适配笔记（HarmonyOS PC）

- 适配路径：路径 A（作者官方 GitHub 源直编 + 1 项 TMPDIR 可移植性补丁，零依赖）
- 使用知识库：E461 家族（OHOS /tmp 只读 → tmpdir 回退机制）；死上游替代源口径（经验库 §12.32④：web.archive.org / GitHub mirror / fossies）
- 知识库扩展：B判定=hit（/tmp EROFS + mkstemp 硬编码路径属既有 /tmp 只读条目覆盖面，解法=TMPDIR 回退，无新增机制）
- 关联 Issue：-（无新增机制）

## 上游与取源（死上游处置）

- 原官方主页 http://umiushi.org/~wac/yaskkserv/ 已成停放域名（HTTP 200 但返回 HTML 停放页，直链软 404）
- 作者本人官方 GitHub = wachikun/yaskkserv（upstream 延续）；master HEAD configure 第 18 行声明 version=1.1.1（即 1.1.1 最终代码）
- 取源：commit 钉死归档 a8306b1412ca54e280d791e26133098822826443，sha256 d78a9093395db608478a2bfd962cd34aa16f7d1ac8e2caadf92a146af96b2fcb
- 与 Debian orig（sha256 7b17563f...）非同一打包（autoconf 旧布局 vs git 归档布局），内容同为 1.1.1

## 症状 / 根因 / 处置

| # | 症状 | 根因 | 处置 |
|---|------|------|------|
| 1 | configure 报 mkstemps Could not create temp file /tmp/...: Read-only file system | configure 两处（40/63 行）硬编码 /tmp 模板传给 File::Temp::mkstemps；OHOS /tmp 为只读（EROFS） | 补丁 0001：模板改为 ($ENV{TMPDIR} || /tmp) 前缀，构建期 TMPDIR 指向 conan build 目录 |
| 2 | configure 报 unknown architecture (HarmonyOS) 警告 | 其架构探测表无 HarmonyOS 条目 | 警告级，回退 bsd_cygwin_linux_gcc 通用构建路径，实测编译链接全通过，不处理 |
| 3 | 构建产物无法直接运行 | OHOS 未签名 ELF 禁止执行 | build() 内 objcopy 移除 .codesign 后 binary-sign-tool 自签（valkey 家族同款） |

## 失败方案（走过的弯路，勿重复）

- perl configure 不吃 TMPDIR 之外的绕法：File::Temp 模板含目录成分时 ENV 不参与，必须改模板本身（补丁）。
- 该 configure 为 perl 脚本：不能用 `sh ./configure` 驱动（探索期 driver 的 autotools 分支会这样调 ⇒ 配方里显式以 perl 调用）。
- binary-sign-tool 对已有 .codesign 段的产物直接签会报 already exists ⇒ 先 llvm-objcopy --remove-section .codesign。

## 适用边界

- yaskkserv_{simple,normal,hairy} 为 SKK 字典服务端，启动需 SKK 字典文件；包级消费者测试覆盖可执行性（--version 自报 1.1.1），完整服务链路（字典加载/网络转换）不在包级测试面内。
- yaskkserv_make_dictionary 为字典制作工具，随包发布。

## 测试账本（五维口径）

- N_static：0（上游无测试框架/测试目标；实测源码树无 test* 文件、Makefile 无 test 目标）
- N_registered：0
- N_executed：0（无上游可执行测试）
- N_consumer：1（test_package/test.sh：真机执行打包产物并断言自报版本，日志原句 yaskkserv consumer test passed: 1 assertion）
- 通过率：消费者 1/1；上游 N/A（分母为 0，不虚报）

## 验证结果

- 本机先行验证：configure + make 全过，yaskkserv_simple 签名后真机 --version 自报 version 1.1.1
- conan-verify G0-G4/L2/L4/L5：见 reports/conan-verify-report.md
- 构建环境：A 机（HarmonyOS PC aarch64），CONAN_HOME ~/tmp/ch/home-yaskkserv，profile ci/conan/profiles/ohos-aarch64
---

**编译结束**: 2026-09-26 04:04
**最终状态**: built
