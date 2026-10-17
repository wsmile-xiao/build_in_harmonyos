# E-DRAFT: automake 测试脚本 `#!/bin/bash` shebang 在无 /bin/bash 的 HarmonyOS 上全灭——LOG_COMPILER 兜底

- **触发实例**：libgctp 2.0.0 适配（2026-09-17，任务 8207，分支 feat/libgctp-2.0.0）
- **错误签名**：`test-driver[119]: <script>: No such file or directory` + `exit status: 126`；套件汇总 `# PASS: 0 / # FAIL: 30`
- **类别**：test-harness-interpreter（测试框架对解释器的硬依赖）
- **严重度**：2（全部上游测试同因误判失败，修复模式固定为两行声明）

## 症状

`make check` 全部 30 个注册测试同因失败，test-suite.log 每项形态一致：

```text
FAIL: ../test/test_proj/alaska_test
===================================
.../test-driver[119]: .../test/test_proj/alaska_test: No such file or directory
FAIL ../test/test_proj/alaska_test (exit status: 126)

# TOTAL: 30
# PASS:  0
# FAIL:  30
```

脚本内容本身是 POSIX 构造（export/test/grep/exit），在任何有 /bin/sh 的系统上手跑都通过。

## 根因

automake 并行测试框架的 test-driver 对 TESTS 脚本是**直接 exec**：execvp 只认 shebang。HarmonyOS `/bin` 下只有 `/bin/sh`（mksh），**没有 `/bin/bash`**。30 个脚本首行全是 `#!/bin/bash` → exec 返回 ENOENT → 退出码 126。测试是否真的需要 bash 与失败无关——shebang 指向不存在的解释器即全军覆没。

**鉴别要点**（与真实测试失败区分）：执行后断言失败 = exit 1 且带脚本自身输出；崩溃 = `Signal 11 (core dumped)`；解释器缺失 = exit 126 + "No such file or directory"（不是 127——126 是"找到文件但无法执行/解释器不存在"）。

## 修复

在定义 TESTS 的 `source/Makefile.am` 头部加：

```make
LOG_COMPILER = /bin/sh
TEST_LOG_COMPILER = /bin/sh
```

automake 生成的 Makefile 把脚本经 `$(LOG_COMPILE)/$(TEST_LOG_COMPILE)` 交给 test-driver，脚本改由 /bin/sh 解释，shebang 被绕开。修复后：`# PASS: 29 / # XFAIL: 1 / # FAIL: 0`（XFAIL 为上游自身段错误的 som_test，用原生 `XFAIL_TESTS` 声明，账本透明）。

**适用边界**：脚本内容须为 POSIX shell（本例成立）。若个别脚本确用 bash 特性（数组、`[[`、进程替换），先用 /bin/sh 暴露真实差异，再对个别文件单独评估。

## 反例与禁止

- 不要伪造 `/bin/bash`（符号链接、shim、busybox 假装）——掩盖平台事实且 /bin 只读，属假环境红线。
- 不要逐个 sed 改 30 个脚本 shebang——效果等价但产生大面积机械 diff，上游更新即重做。
- 不要因为 PASS=0 就断言"上游测试全部不适配"——先看 exit 码与 test-suite.log 的失败形态（126 ≠ 1 ≠ Signal 11）。

## 查重说明

知识库既有条目 E386（CONFIG_SHELL/hnp bash getcwd，运行 configure 阶段）、E228（HMDFS 上 libtool 无扩展名测试 wrapper 启动失败）、E443（跨 UID shebang 执行边界）均为相邻家族，但均未覆盖"**测试脚本 shebang 指向系统不存在的解释器 → LOG_COMPILER/TEST_LOG_COMPILER=/bin/sh 兜底**"这一触发面与修法，无重复登记。

## 验证

- 触发实例：libgctp 2.0.0 `make check`（本 PR archives/l/libgctp/2.0.0，补丁 `patches/0002-source-Makefile.am.patch`）
- 修复前：PASS 0 / FAIL 30（全 exit 126）；修复后：PASS 29 / XFAIL 1 / FAIL 0
- 消费者测试 test_libgctp 同 PR 独立通过（7 断言），证明库功能本身正常
