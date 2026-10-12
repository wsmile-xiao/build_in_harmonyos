## PR 信息

- **三方库名称**：utimer
- **上游版本**：0.4
- **上游仓库地址**：https://launchpad.net/utimer；权威发行镜像 https://distfiles.macports.org/utimer/utimer-0.4.tar.gz
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：E11574-draft-2501；对比 E464 和 DRAFT-kevlar-2.0.1-getc-char-eof-loop

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 5 | src/tests/maintests.c 的全部 g_test_add_func 注册 |
| 集成测试 | 0 | 官方发行无其他注册集成入口 |
| 其他测试 | 0 | 完整发行归档与 Makefile.am 盘点无其他入口 |
| **合计** | **5** | Suffix、Duration、Timer、Stopwatch、Countdown |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 5 | 不变 | 原始 maintests.c，不改断言，原生执行 |
| 集成测试 | 6 | +6 | 安装版本/帮助、有限 timer/countdown、缺失/未知参数拒绝 |
| 鸿蒙特有测试 | 2 | +2 | 开放 stdin 自然退出、limits；属于新增消费者，不计入上游分母 |
| **合计** | **13** | **+8** | 上游 5/5，新增消费者 8/8 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

CMake 适配保留完整生产源与原始 GLib 测试源；执行 utimer-upstream-tests --verbose -m slow。不删除测试，不缩减分母。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

另在 test_package/test.py 新增 8 项真实安装产物消费者；调用被测二进制，有限命令同时覆盖 EOF 和开放 stdin。后者不输入 quit，不发成功信号；要求实际经过计时并正常退出。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：5/5（100%）
- 新增测试用例通过率：8/8（100%）

HarmonyOS PC 6.0 arm64 / Clang 15.0.4。原生正式 Conan 验证和官方 finish 的 W3 子步骤实际通过；L1e 移走安装 bin 后消费者失败。当前事务 utimer-full-finish-r2-20261011T094000Z 完整12阶段、单次 launch、release/postrelease PASS。

日志 SHA256：01d7865ff4b3b5654a79635230e1b9717d1c6dd8922a7b4ddf776fb2683a2602。官方 CI 安装 ELF SHA256：5f1df01b04cd1aa523fc0ac5af33bc63e13c9441866b37cbff3c64a2cb2c1bd1。

完整 finish 整体 RC1 / PARTIAL_POST_W3，仅 step5b/step8 旧知识及归档元数据检查失败，不冒称完整收尾 PASS。ConanVerifier L2/L4/L5 和官方 L2 的 SKIP 保留原义；不修改框架，不人工创建 .ci-result.json。比赛 worker CI 与平台 AI Review 尚无通过结论。

---

## 补充说明

- 关联 Issue：#3909
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/utimer-0.4
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 基础库任务 #11574，按 A+B 提交，HD1–HD4 当前逐项为否。
- GLib 2.88.3 及 libffi/pcre2/proxy-libintl/zlib 闭包均使用已发布制品；不构建或上传新依赖。
- 新知识区分 char 截断 EOF、资源流 EOF 和后台输入线程影响有限任务退出的边界；具体 libc 内锁路径明确标为推断。四区查重和配对草稿随候选提交，最终编号和分值以评审为准。
