# ctpv 1.1 测试报告

> **项目**: ctpv 1.1
> **测试日期**: 2026-09-11
> **测试环境**: HarmonyOS 6.0 AArch64 / OHOS Clang 15 / QEMU AArch64 用户态仿真
> **测试类型**: 上游测试清点、Conan 消费者功能测试、HarmonyOS 专项测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试入口 | 0 | 100% 已清点 |
| 适配后总测试数 | 12 | 100% |
| 通过 (PASS) | 12 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

---

## 二、测试结论

### 2.1 总体评价

✅ **全部通过**

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无 | 无 | 🟢 |

### 2.3 可用功能清单

```
✅ ctpv：版本、帮助、预览器列表、MIME 识别和文本预览
✅ ctpv：符号链接信息、错误输入和 XDG 路径处理
✅ ctpvclear / ctpvquit：原生命令实际执行、IPC 分发与命令发现
✅ HarmonyOS 专项：IPC 状态文件遵循可写 TMPDIR
```

### 2.4 已知限制

无。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| ctpv 安装、ctpvclear/ctpvquit 实际调用（3 项） | 包完整性与辅助命令行为 | ✅ PASS |
| `ctpv -v` | 版本输出 | ✅ PASS |
| `ctpv -h` | 帮助输出 | ✅ PASS |
| `ctpv -l` | 内嵌预览器清单 | ✅ PASS |
| `ctpv -m` | libmagic MIME 识别 | ✅ PASS |
| 文本文件预览 | shell 回退与 cat 后端 | ✅ PASS |
| 符号链接预览 | 链接目标信息 | ✅ PASS |
| 缺失文件 | 负向错误处理 | ✅ PASS |
| XDG 配置文件 | 可写用户目录 | ✅ PASS |
| `TMPDIR` IPC 状态 | HarmonyOS 专项路径行为 | ✅ PASS |

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| 无 | 无 | 0 项失败 |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 无 | 无（上游源码没有测试入口） |

---

## 四、关键问题分析

### 问题1: 交叉编译构建期生成器

**现象**：
```
embed/embed 由目标编译器生成后，构建规则立即在宿主执行该程序。
```

**根因分析**：
上游 Makefile 未区分构建机编译器与目标机编译器。

**解决方案**：
新增 `HOSTCC`，仅用于构建 `embed/embed`；生产可执行文件继续使用 OHOS 目标编译器。

### 问题2: 固定 `/tmp` 路径

**现象**：
```
FIFO 与 Kitty 状态文件固定写入 /tmp。
```

**根因分析**：
上游假定 `/tmp` 可写，不符合 HarmonyOS 应用运行目录约束。

**解决方案**：
所有相关路径统一使用 `${TMPDIR:-/tmp}`，并由专项测试验证实际写入位置。

### 问题3: AArch64 无符号 char 丢失 EOF

**现象**：
```
ctpv: config:1:2: cannot handle character: 0xff
```

**根因分析**：
词法器把 `int` 类型的 EOF 缩窄到默认无符号的 `char`，`-1` 因此变成 `255`。

**解决方案**：
字符读取、前瞻和 EOF 比较链路统一使用 `int`，保留 EOF 哨兵值。

### 问题4: shell 名称的 PATH 解析

**现象**：
```
ctpv: internal error: shell 'sh' was not found
```

**根因分析**：
配置校验对不含路径的 shell 名称直接调用 `access()`，但实际执行使用支持 `PATH` 查找的 `execvp()`。

**解决方案**：
不含斜杠的 shell 名称交给 `execvp()` 按 `PATH` 解析；显式路径继续使用 `X_OK` 校验。

### 问题5: 安装脚本的固定 shebang

**现象**：
```
ctpvclear 使用 #!/bin/sh，但 HarmonyOS 没有传统 /bin 目录。
```

**根因分析**：
上游把辅助命令实现为依赖固定解释器路径的 shell 包装脚本。

**解决方案**：
以相同参数和环境变量接口实现 AArch64 原生 `ctpvclear` 启动器，并为两个辅助命令补充 `--help`/`--version` 命令发现。

---

## 五、测试环境

```
ctpv 1.1
OpenHarmony public SDK 6.0.0.47 (API 20)
Target: aarch64-unknown-linux-ohos
Compiler: OHOS Clang 15.0.4
Runtime validation: QEMU AArch64 user-mode with binfmt
Build: Conan 2.29.1, make -j1, static PIE, stack protector, FORTIFY
```

---

## 六、规范与制品复核

| 检查 | 结果 |
|------|------|
| 强制源码 `conan create` + QEMU 消费者测试 | ✅ 12/12，通过 |
| 赛事定向 CI：L0/L1/L2/L4/L5 | ✅ 全部通过 |
| 三个安装命令 `--version` 冒烟 | ✅ 全部通过 |
| AArch64 ELF：静态 PIE、NX、RELRO、BIND_NOW、栈保护 | ✅ 全部通过 |
| `tests/run_all.py` 仓库规范回归 | ✅ 11/11 套件通过 |
| PF1–PF9、依赖仓、junk、knowledge、graph 门禁 | ✅ 全部通过 |

---

*报告生成时间: 2026-09-11*
