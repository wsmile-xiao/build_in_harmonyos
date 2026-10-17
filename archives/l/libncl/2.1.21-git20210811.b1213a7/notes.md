# libncl 2.1.21-git20210811.b1213a7 适配笔记

状态: built。此状态由 H1-009 框架 `close-archive` 在 2026-09-25 04:09（北京时间）写出；`finish` 整体仍以 rc1 结束，尚未发布或取得远端官方 CI 结果。

官方源码固定在 `mtholder/ncl@b1213a78003629483426d83258d8ab9e43ab20b1`，源码归档 SHA-256 为 `FA83172B928036BE212E1422CD14F7D242063E7A829FFF9D325AED20D4995F7F`。`0001-CMakeLists.txt.patch` 接入上游测试程序，`0002-test-roundTripNCLTest.py.patch` 将原测试驱动迁至 Python 3。两份补丁由官方 `refresh-patch --auto` 对固定源码生成；与先前补丁应用后的 285 个源码文件逐字节一致。

## 真机验证

- H1-004 在 OHOS/armv8/Clang15/libc++ 环境，对先前等价源码完成静态与共享 Conan `create`；每种包型各通过 11 组上游测试、52 个唯一输入、97 次程序调用及消费者 10 项断言。结果包 SHA-256 为 `CC18D5BA2FEA1C9BF0E5F0705EF363D62446DDBE9CFA57FEF1FEE6BA6BBF5483`，不代替当前候选的正式框架门禁。
- H1-008 当前候选的 Conan `create` 与消费者 10 项断言通过，但 W3 的 JC 因孤立克隆缺 `origin/main` 而整仓扫描，命中旧基线中三个其他软件的已跟踪状态文件，L0 失败。软件树未改。
- H1-009 在新私有根对完全相同的 16 文件候选运行：前置及正式 JC 均为 `prdiff (16 个文件)` 且通过，`setup.sh` 与 `build_and_test.sh` 各 rc0。W3 L0/L1/L4/L5 通过，纯库无 `bin/` 故 L2 跳过；上游测试发现 52 个输入、执行 97 次调用并通过，包消费者 `LIBNCL_CONSUMER_PASS assertions=10`。框架 `.ci-result.json exit_code=0`，其 `log_sha256=7A9DF5779775306B99BDB82F4F6446B91387D684233DA88F91D7DA53EEBCDAF7` 与回传的完整 W3 日志吻合。原始 009 结果包 SHA-256 为 `3745782EAE1C00616668E32C156A02B6D3C4341DCF26F8E727D35EA234ED834D`。

## 收尾限制

H1-009 `finish` 的 `wrapper.exit=finish.exit=1`。正式 W3 已通过，后续 `finalize-archive` 在当次运行中报本地 `packaging/` 与 release/debug tar 缺失、旧 notes 状态矛盾；全仓 SUMMARY 生成报 `'str' object has no attribute 'append'`，知识完整性与 submit 就绪检查还有独立告警。

之后只读取回 H1-009 真机 Conan stage2 包（SHA-256 `3689F9F9DAD57FB645FC653E246B97695C33B94FACA061AAF4BCFF185213E3FB`），确认其 `lib/ncl/libncl.a` SHA-256 为 `97A615618D2B64CB9E140522737150470BB6EFD6C4060AA6E47FD6DE44A5EAE8`。从此包调用框架现有 `package_cli`，在本地隔离目录产出 release tar（SHA-256 `4EDA8630CF755BD5A9EB5FED05560C016EEE459CCD1B94F5BA4B23F988E49F50`）；包内静态库字节未变。当前配方产物只有静态库，不能从该包生成真实的独立 debug tar。这些本地补充不会改变 H1-009 原始 `finish` rc1。PR 跟踪差异不得加入 tar、测试报告或运行时标记。可供维护者访问的证据链接、独立 W4 及远端 CI 仍待后续核验。

### 对话 #1：H1-009 结果交接与审计

2026-09-25，唯一 H1 协调位回传 61 项 tar 清单及完整 `results/`，libncl 软件任务逐项核输入 SHA、16 文件、JC 范围、W3 退出码和日志 SHA；将 W3 通过与 `finish` 整体 rc1 分开登记，并请求只读回收 009 的 Conan 包字节以核对后续归档产物。本记录不代替正式 W4 或远端审核。
