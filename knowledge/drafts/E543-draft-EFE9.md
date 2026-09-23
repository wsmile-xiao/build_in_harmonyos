# E543 — HongMeng 内核版本串非标准（a.b.c 解析失败 + /proc/version 不可读）导致版本解析类测试环境性失败

## 错误特征
- 上游测试输出 `FAIL: library/tests/test_version`（procps-ng 4.0.7 实测）
- 库 API `procps_linux_version()` 返回 0（解析失败），断言 `rc==0 && ver>0` 不满足
- 实机取证：
  - `cat /proc/sys/kernel/osrelease` → `HongMeng Kernel 1.12.0`（非数字开头的 a.b.c 串）
  - `cat /proc/version` → Permission denied
- 对照证据：同一测试程序的 `LINUX_VERSION` macro（编译期宏）子用例 PASS——仅运行时 /proc 解析路径受影响

## 触发条件
- 构建系统: autotools / make（任何构建系统的 make check 阶段）
- 阶段: testing / runtime
- 场景: 软件在运行时用 `sscanf("%d.%d.%d")` 类格式从 `/proc/sys/kernel/osrelease` 或 `/proc/version` 解析内核版本号（procps-ng libproc2 的 `procps_linux_version()` 即此模式）

## 根因分析
OHOS 的 HongMeng 内核在这两个 procfs 接口上返回非标准内容：
1. `/proc/sys/kernel/osrelease` 为 `"HongMeng Kernel 1.12.0"` —— 以文字开头，
   `sscanf("%d.%d.%d")` 在首 token 即匹配失败；
2. `/proc/version` 不可读（`cat` 返回 `Permission denied`）—— 备用解析路径
   同样无数据。

标准 Linux 上两接口分别返回 `"6.1.0-xxx"` 与
`"Linux version 6.1.0 (...) ..."`。依赖这两处做运行时版本探测的库，
在 OHOS 上解析结果为 0/失败。这是**平台环境语义差异**，不是适配缺陷：
代码逻辑正确、编译链接正常，仅喂入的数据形态不同。

procps 4.0.7 全量影响面：8 个测试程序 7 PASS / 1 FAIL / 0 SKIP，
唯一 FAIL 即此环境性子用例。

## 解决方案

### 推荐方案（环境性定性处置）
1. **禁止修改上游断言**（R9 门禁语义：门禁 FAIL 禁标 success；如实记录）。
   不 patch 测试期望值、不删除测试用例。
2. `conanfile.py` `build()` 中将 `make check` 用 `try/except` 包裹，
   捕获失败后 `output.info` 记录"已知环境性失败"继续构建——保证包可交付，
   失败信息保留在 conan create 日志中可审计。
3. `notes.md` / `reports/test-report.md` 如实记录统计（7 PASS / 1 FAIL /
   0 SKIP）与定性证据链（osrelease 实际串 + /proc/version 不可读 +
   macro 子用例 PASS 对照），并注明"环境限制，禁改断言"。
4. 沉淀知识草稿（本条目）供后续同类软件检索。

### 禁止做法
- ❌ 修改/删除上游测试断言或期望值以"刷绿"测试
- ❌ 在 `__OHOS__` 守卫下替换解析实现来绕过断言语义（除非用户显式要求
  且上游接受，且不得改变断言本身）
- ❌ 将整个 `make check` 静默跳过不留记录（失败信息必须可审计）
- ❌ 把环境性 FAIL 标记为适配成功（门禁语义违规）

## 验证
```bash
# 环境取证
cat /proc/sys/kernel/osrelease   # -> HongMeng Kernel 1.12.0
cat /proc/version                # -> Permission denied

# 测试统计（探索构建与 conan create G2 干净构建两次一致）
make check 2>&1 | tee check.log
grep -E "^(PASS|FAIL)" check.log | sort | uniq -c
# TOTAL: 8  PASS: 7  FAIL: 1  SKIP: 0

# 失败子用例定位
grep -A3 "test_version" check.log
```

## 关联条目
- 相关: E007（config.guess/sub HarmonyOS 平台识别——同为 OHOS 平台语义差异类）
- 案例来源: procps 4.0.7（archives/p/procps/4.0.7/notes.md）
