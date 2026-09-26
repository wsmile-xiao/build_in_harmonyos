# DRAFT: conanrun 环境把 stdin 接到 /dev/null——CLI 消费者测试的显示层/rc 断言必然失真

> 状态：DRAFT（less/710 触发，随本 PR 提交）｜severity: P2｜category: conan, testing, cli
> 提交窗口：GLM-72｜日期：2026-09-22

## 1. 可复现症状与稳定错误签名

为 CLI 工具编写的消费者测试（test_package/smoke.sh）在开发者终端手工运行全部通过，
进入 `conan test`（`self.run("sh smoke.sh", env="conanrun")`）后同一段断言失败：

```
smoke: -N missing numbered line          ← less -N 的行号断言
smoke: missing file should fail          ← 缺文件场景 rc 断言（实际 rc=0）
```

特征：失败的都是**依赖 tty 的显示层输出**（-N 行号、提示符）或**依赖 stdin 语义的
退出码**（读 stdin 的工具对参数文件失败场景回落读 stdin）；与 tty 无关的
stdout 内容断言、stderr 诊断断言始终稳定。

## 2. 根因与最小复现

conan 2 的 VirtualRunEnv/conanrun 环境没有 tty：进程 stdin 接到 /dev/null。两个后果：

1. less 的 `-N`（行号）等显示层特性属于 tty 渲染路径——输出重定向到管道时
   行号根本不会写入输出缓冲，`grep 行号` 必败；
2. less 对打不开的参数文件打印 stderr 错误后**回落读 stdin**；stdin=/dev/null
   即刻 EOF → less "正常读完"以 rc=0 退出——错误场景的 rc 断言反而得到 0。

最小复现：conan test 内 `less -F missing.txt; echo $?`（得 0），同一命令在
终端手工运行得 1。

## 3. 已尝试方案（含失败）

- 断言 `less -N -F file` 输出行号：**失败**（显示层不进管道）。
- 捕获缺文件场景 rc 断言非零：**失败**（stdin=/dev/null 使 rc=0）。

## 4. 最终方案与真实验证

断言口径改为"管道可观测证据"（OHOS aarch64 真机，conan create 全链实测）：

- stdout 内容断言：`less -F in.txt > out` 后 grep 文件内容 ✓
- stderr 诊断断言：`less -F nope.txt < /dev/null 2>err` 后 grep "No such file" ✓
- rc 断言只用于 stdin 无关的路径（正常文件 -F 退出 0）✓

最终 smoke.sh 4 场景/6 断言全过：`less consumer OK: 4 behavioral scenarios asserted`。

## 5. 适用范围 / 反例 / 解除条件 / 风险

- 适用：type=tool 的 CLI 包（分页器/文本工具/诊断工具）消费者测试编写与评审；
  所有把终端手工行为照搬进 conan test 的断言。
- 反例：库类包（有 API 断言）；上游自带 pty 仿真套件的交互回归（如本包
  lesstest——它自己模拟终端，已由 make check 承载 19 用例）。
- 解除条件：断言口径换成 stdout/stderr 管道证据，或交互行为移入仿真套件。
- 风险：假阴性只是测试失败尚可发现；危险的是反向——为让测试通过删断言、
  或用 --version 只打印冒烟充数（审查口径不合格）。

## 6. 查重与新增价值说明

- 四范围查重：E386/§12.38① 为构建期 getcwd/CONFIG_SHELL 机制；E216 为
  CMakeDeps include 传播；均与本条（conan test 期 stdin/tty 环境语义）不同族；
  知识库无同族条目命中。
- 新增价值：a) 解释"手工过、conan 挂"这类测试假阴性的统一根因；
  b) 给出 CLI 消费者测试的断言选型规则（管道可观测证据优先级）；
  c) 与上游仿真套件（lesstest）的分工边界。
