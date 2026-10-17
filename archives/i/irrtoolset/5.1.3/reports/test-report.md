# Test Report — irrtoolset 5.1.3 (OHOS aarch64)

日期: 2026-09-16
分支: feat/irrtoolset-5.1.3
HEAD: 见 git rev-parse

## 一、上游测试枚举台账 (源码声明全集)

上游仓库: https://github.com/irrtoolset/irrtoolset (tag release-5.1.3)

| 类型 | 项目 | 是否独立上游用例 | 分类理由 | 结果 |
|------|------|----------------|----------|------|
| 构建目标 | peval (bin_PROGRAMS) | 否 | 产品二进制, 非测试 | 构建成功 |
| 构建目标 | rpslcheck (bin_PROGRAMS) | 否 | 产品二进制, 非测试 | 构建成功 |
| 构建目标 | rtconfig (bin_PROGRAMS) | 否 | 产品二进制, 非测试 | 构建成功 |
| 构建目标 | libirrtoolset.a (noinst_LTLIBRARIES) | 否 | 内部静态库, 不安装 | 构建成功 |
| 测试框架 | TESTS/check_PROGRAMS 注册 | — | make check 输出 "Nothing to be done for 'check'", 无任何注册 | 无注册项 |
| 测试框架文件 | gtest/Catch2/doctest 等 | 否 | 全树搜索无测试框架源码 | 不存在 |
| 测试源文件 | *test*/*.test/unittest* | 否 | 全树搜索无测试源文件 | 不存在 |
| 样例 | examples/ (ios/xr/junos cfg + private_irr_objects.txt) | 否 | 示例输入数据, 非断言型测试 (需访问 RADB 远端 whois) | 仅作鸿蒙专项测试数据 |

**结论: `source_declared_total = 0`** (官方 tag 源码按可复制枚举规则未发现独立测试用例声明)
`configured_executable_total = 0`, `executed_passed_total = 0`, 失败数 = 0, 未实例化数 = 0。

统计口径: 全目录枚举 (Makefile.am 的 TESTS/check_PROGRAMS + 测试源文件名 + 测试框架文件)。
全量通过率: 0/0 = N/A (无上游测试可运行, 如实申报, 不以空测充数)。

## 二、test_package 测试 (conan create L1 官方测试)

- 源文件: `test_package/test.sh` — 调用已安装 CLI 工具的实质功能验证
- 用例 1: rpslcheck 接受合法 RPSL 对象 (stdin 输入 inetnum + 必填属性) → exit 0, 输出 "Congratulations no errors were found" → PASS
- 用例 2: rpslcheck 报告非法 RPSL 对象错误 (缺必填属性) → 输出 7 条 mandatory attribute 错误 → PASS
- 用例 3: rtconfig 运行并产生输出 (`rtconfig irrtoolset-5.1.3`) → exit 0 → PASS
- 结果: conan-verify G2 (conan create 含 test_package) 通过

## 三、消费者用例 (Consumer Case, 独立计数)

- 源文件: `reports/consumer-case.sh` — 模拟网络运维上层应用中的 RPSL 策略校验环节
- 使用方式: 仅通过库已安装/导出的公开运行时产物 (bin/rpslcheck, bin/rtconfig) 与公开 CLI 接口, 不触碰内部头文件/符号
- 用例 1: 合法 RPSL 对象 (inetnum + netname/country/descr/admin-c/tech-c/mnt-by/status/created/last-modified/source) → `CONSUMER-PASS`, exit 0
- 用例 2: 非法 RPSL 对象 (缺必填属性) → 被拒绝并报告错误 → `CONSUMER-PASS`
- 用例 3: rtconfig 配置生成器运行 → 输出 `rtconfig irrtoolset-5.1.3` → `CONSUMER-PASS`
- 运行命令: `BIN_DIR=<conan pkg>/bin bash reports/consumer-case.sh`, cwd = archives/i/irrtoolset/5.1.3/reports
- 结果: `CONSUMER-ALL-PASSED`, exit 0

## 四、鸿蒙专项测试 (OHOS-specific, 独立计数)

- 源文件: `reports/ohos-specific-test.sh` — 验证 OHOS aarch64 平台适配完整性
- 用例 1: 二进制架构核验 → `rpslcheck: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)` → `OHOS-PASS`
- 用例 2: 上游真实 RPSL 数据 (examples/private_irr_objects.txt) 在 OHOS 平台加载校验 → exit 0, rpslcheck 如实报告上游数据自身缺少 source/descr 等必填属性的引用错误 (属预期行为, 平台链路正常) → `OHOS-PASS`
- 运行命令: `BIN_DIR=<conan pkg>/bin SRC_EXAMPLES=<src>/examples bash reports/ohos-specific-test.sh`
- 结果: `OHOS-SPECIFIC-ALL-PASSED`, exit 0

## 五、消费者可用性结论

消费者通过库公开交付物 (bin/ 下 CLI 工具) 编译/链接/调用/运行链路完整可用:
- 编译链接: conan create 干净构建 + test_package 链接验证通过 (G2)
- 调用运行: rpslcheck 真实解析 RPSL 对象, rtconfig 生成配置输出, 均在本机 OHOS 平台 exit 0
- 可观察结果: 合法/非法对象判定正确, 配置生成器输出版本信息

## 六、未运行项与恢复条件

- 上游无独立测试用例 (source_declared_total=0), 无未运行/未实例化项
- peval 需要连接 IRR whois 远端 (RADB 等) 做 newClient, 测试环境无外网时挂起; 已如实排除在 test_package 之外, 其本地求值功能由手动冒烟验证 (`peval 'AS3'` exit 0)