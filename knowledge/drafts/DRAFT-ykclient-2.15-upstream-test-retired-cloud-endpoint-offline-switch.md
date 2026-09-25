# DRAFT-ykclient-2.15: 上游测试的断言目标（第三方在线服务端点）已停用——用上游自带离线开关宏，并按四层口径申报

## 基本信息
- **严重度**: 3
- **类别**: upstream-test, network-dependency, offline-switch, test-accounting
- **作者**: QC-10
- **来源 PR**: (本 PR)
- **来源 commit**: (待提交后回填)
- **适用构建系统**: autotools（`make check`），同样适用于 cmake/ctest 里以宏开关网络用例的包

## 错误特征
```
checking nothing；失败发生在 make check 阶段，编译与链接均已成功
FAIL: selftest
validation request, expect REPLAYED_OTP      -> 断言目标为外部 HTTP 服务的返回值
（未启用开关时）网络请求返回 403 / 连接被拒 -> 用例直接失败，runner 退出码非 0
```
关键指纹：**用例断言的是"某个第三方在线接口的响应内容"**，而不是本库的计算结果；该接口由服务方
停用或改版后，断言在**任何平台、任何网络质量**下都不成立。本地与 CI 表现一致（区别于 M3 那种
"本地不复现"的 CI 专属问题）。

## 根因分析
两层叠加：

1. **上游测试资产过期**（与本库适配无关）。本例 `tests/selftest.c` 把断言写成
   「设好 client key → 请求 `api.yubico.com/wsapi/2.0/verify`（wsapi v1）→ 断言返回
   `REPLAYED_OTP`/`BAD_SIGNATURE`」。该端点/协议已由 Yubico 停用（本次实测返回 HTTP 403）。
   上游作者为此预留了**自身的离线开关**：网络断言块被 `#ifndef TEST_WITHOUT_INTERNET` 包住，
   `#else` 分支打印 `Test SKIPPED` 后继续。
2. **申报口径出现四个不同数字**，只报其一必被判少报或虚报：
   - `N_static`：文件内活跃 `TEST(` 标记点数 = 36 − 9（位于上游 `#if 0` 死区）= **27**；
   - **开关排除数**：位于 `#ifndef TEST_WITHOUT_INTERNET` 内、定义开关后被编译掉的点数 = **6**；
   - **运行进入数** = 27 − 6 = **21**（实测 `tests/selftest.log` 里 `Test <file>:<line>` 头行数=21，与推算吻合）；
   - **SKIPPED 次数** = **16**（21 个进入点中 15 个各打印 1 次，`selftest.c:317` 因循环打印 2 次）；
     由此纯离线完整断言的进入点 = 21 − 15 = **6**。
   runner 层只有 1 个（`tests/Makefile.am:37 TESTS = $(check_PROGRAMS)` → `selftest` 单可执行），
   以 runner 数申报必然与机器人按源码实测的数不一致（§12.72 rule4 少报族的同源机制）。

## 推荐方案
**方法**: `enable-upstream-offline-switch-and-report-four-layer-counts`

**说明**: 在配方 `generate()` 里通过 `AutotoolsToolchain` 追加 `-D<上游自带开关宏>`，让网络断言走
上游自己的 SKIPPED 分支、离线断言照常真实执行；`make check` 仍以真实退出码参与构建（不吞错误、
不改判）。notes/正文按上面四层口径逐项写清，并对每个含网络断言的进入点给出**具体技术原因**
（端点由服务方停用，附本次 403 事实），不得以"没网络/环境问题"充当理由。

**验证/命令**（三段复算，全部实测过）:
```bash
# ① N_static：总标记点 − #if 0 死区
grep -cE '^[[:space:]]*TEST\(' tests/selftest.c                                  # 36
awk '/#if 0/{f=1} /#endif/{f=0} f&&/TEST\(/{c++} END{print c+0}' tests/selftest.c # 9
# ② 开关排除数（数开关区内的 TEST() 点，不是数指令行——实测指令行有 16 处）
awk '/#ifndef TEST_WITHOUT_INTERNET/{d=1} /^#endif/{d=0} d&&/TEST\(/{c++} END{print c+0}' \
    tests/selftest.c
# ③ 运行进入数与 SKIPPED 次数（make check 之后）
grep -c '^Test /' tests/selftest.log                 # 21
grep -c 'Test SKIPPED' tests/selftest.log            # 16
awk '/^Test \//{h=$0;sk=0;next} /Test SKIPPED/{if(h!=""){n++;h=""}} END{print "含网络断言的进入点="n}' \
    tests/selftest.log                               # 15
```

## 适用边界 / 反例 / 解除条件
- **适用**: 测试套件断言依赖外部 HTTP 服务、且**上游自带离线/无网络开关宏**的包。同族探测对象：
  各类在线校验/授权客户端库（Yubico 系、OAuth/OATH 远程校验、license server 客户端）。
- **反例一**: 服务仍在、只是本机/worker 网络或证书受限 → 属基础设施故障（R41 口径：存证换窗或
  受控重试），**不得**用本条把失败改判为"平台限制"。
- **反例二**: 上游没有离线开关 → 要么逐用例 `test_skipped` 附技术原因并保留真实分母，要么自建
  可控对端；这两种都要在正文逐项说明，不属于本条的"零源码改动"。
- **禁止**: 为让 `make check` 变绿而整体不执行、缩小分母或删用例。本例改前该 runner 是真红的
  （消费者测试首次跑出 3 条错误期望时它也照样红），开关只改变网络断言的分支，不改判退出码。
- **解除条件**: 服务方恢复该端点，或上游把断言改为对本地 mock 服务发起请求。

## 关键词
上游测试, 已退役端点, 服务停用, HTTP 403, 离线开关宏, TEST_WITHOUT_INTERNET, ifndef, Test SKIPPED,
测试账本, 四层口径, N_static, 编译期排除, 逐点归因, rule4 少报, 不删用例

---
*与相近条目的区分：**§12.72** 给的是"实测 N 的四种上游形态"（独立框架/语料目录/RUNTEST 脚本/示例目录），
本条补的是它没有的那一层——**启用上游自带离线开关后，静态声明数、编译期排除数、运行进入数、SKIPPED
次数会同时不一致**，申报必须四层分别给数。知识图谱 `knowledge/graph/*.kv` 与 `knowledge/drafts/`
中 grep `TEST_WITHOUT_INTERNET|退役|offline switch` 均 0 命中（本次已查）。*
*实测来源：ykclient 2.15（任务 12297）。改后 `tests/test-suite.log`：TOTAL 1 / PASS 1 / FAIL 0；
`tests/selftest.log`：21 个进入点、16 次 `Test SKIPPED`、6 点纯离线完整断言；
`test_package` 消费者测试另有 15 条断言全通过（`consumer_test: PASS (0 failures)`）。*
