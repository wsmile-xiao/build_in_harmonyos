# 测试报告

> **项目**: finalcut 0.9.1  
> **测试日期**: 2026-10-02  
> **测试环境**: HarmonyOS 6.0 PC aarch64；Clang 15.0.4/libc++；Conan 2.29.1  
> **测试类型**: 上游官方测试套件 + Conan consumer + 仓库正式本地 CI

---

## 一、测试摘要

下表按可执行测试目标/consumer 测试统计：上游发布归档 30 个目标，HarmonyOS 上 28 个适用目标通过、2 个 BSD 专属目标不适用；另有 2 个 Conan consumer 测试通过。按 CppUnit 源码中的测试方法统计，上游共 311 个方法：297 个实测通过，5 个 BSD 专属方法不适用，9 个依赖 `TIOCSTI` 的方法未注册；因此为 **297/311（95.5%）**，可运行方法通过率为 **297/297（100%）**。

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 32 | 100% |
| 通过 (PASS) | 30 | 93.75% |
| 失败 (FAIL) | 0 | 0% |
| 跳过/不适用 (SKIP/N/A) | 2 | 6.25% |

**核心功能通过率**: ✅ **100%（30/30 个适用目标）**

另有 `fkeyboard_test` 内部 9 个依赖 `TIOCSTI` 的用例未注册；同一目标的 4 个非注入用例仍运行通过。它们是用例级能力门控，不重复计入 32 个可执行目标。

---

## 二、测试结论

### 2.1 总体评价

✅ **HarmonyOS 6.0 aarch64 Conan clean build、正式 W3 `build_and_test.sh`、28 个适用上游测试目标及 2 个 consumer 测试均通过。**鸿蒙专项 consumer 已改为真实 PTY 驱动的 FINAL CUT 界面流程，不再只构造 FString 后做断言。

外层 `finish` 随后未完全收尾：单独的 clean-verify 阶段提示原始源码 tarball 不存在，SUMMARY 生成器报 `'str' object has no attribute 'append'`，submit 预检提示缺少 `packaging/` 与 `.staging-verified`。这些状态已如实记录；W3 的 Conan clean build/consumer 测试本身通过，未添加占位 staging 标记或预编译包。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| BSD 专属后端 | FreeBSD/OpenBSD 两个上游目标不适用于 HarmonyOS | 🟢 |
| `TIOCSTI` 权限边界 | `fkeyboard_test` 中 9 个依赖输入注入的用例不注册 | 🟡 |

### 2.3 可用功能清单

```text
✅ finalcut/0.9.1 静态 Conan 包：HarmonyOS aarch64 clean build 与打包通过
✅ 上游 make -j1 check：28/28 个适用目标通过
✅ test_finalcut：已安装的 FString 公共 API consumer 测试通过
✅ test_ohos_unicode：PTY 启动 FINAL CUT、显示 CJK、键入“鸿蒙”、Tab/回车激活 Accept、验证输入保留与应用退出
✅ 正式 finish/W3 build_and_test.sh：通过
⚠️ FreeBSD/OpenBSD 后端目标：目标系统不适用
⚠️ TIOCSTI 输入注入：只跳过明确依赖该 ioctl 的 9 个键盘用例
```

### 2.4 已知限制

1. 目标设备上对自有 pty slave 执行 `TIOCSTI` 返回 `EACCES`；此结论限定于本次 HarmonyOS 6.0 aarch64 设备及测试进程上下文。
2. 此交付为 Conan 源码配方，不提交预编译二进制 tarball；目标设备上实际完成了 Conan 构建和 consumer 测试。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| 上游 `make -j1 check`（目标级） | CppUnit 单元测试；逐项见 `reports/upstream-tests-ledger.md` | ✅ PASS 28/30（2 BSD N/A） |
| `test_finalcut` | 安装后 FString 公共 API、长度及字符串转换 | ✅ PASS |
| `test_ohos_unicode` | 真机 PTY 端到端 FINAL CUT UI：渲染中文、键入中文、切换焦点、激活按钮、检查输入和正常退出 | ✅ PASS |
| 正式 W3 `build_and_test.sh` | Conan aarch64 clean build、打包和 test_package | ✅ PASS |

### 3.2 失败的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| 无 | — | 最终验证中没有失败目标 |

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| `ftermfreebsd_test` | 测试 FreeBSD/DragonFly 专属终端后端；Automake 只对这些 native host 注册，HarmonyOS 没有该后端 |
| `ftermopenbsd_test` | 测试 OpenBSD 专属终端后端；Automake 只对 OpenBSD native host 注册，HarmonyOS 没有该后端 |

`fkeyboard_test` 中 9 个注入用例因目标内核拒绝 `TIOCSTI` 而不注册；4 个不依赖该能力的用例仍通过。方法级核算为 297 PASS + 5 BSD N/A + 9 `TIOCSTI` 未注册 = 311 个上游方法。原始探针见 `reports/tiocsti-probe.md`。

---

## 四、关键问题分析

### 问题1: HarmonyOS 对 pty 的 `TIOCSTI` 输入注入返回 EACCES

**现象**：

```text
PermissionError: [Errno 13] Permission denied
```

**根因分析**：

HarmonyOS 6.0 aarch64 真机上的当前 HNP 测试进程无法对自有 pty slave 使用 `TIOCSTI`。上游 `fkeyboard_test` 的 13 个用例中，9 个依赖该注入行为。

**解决方案**：

仅在目标能力探测确认 `TIOCSTI` 不可用时，不注册这 9 个依赖用例；其余 4 个键盘用例和其他上游目标照常运行。没有以此推断其他 HarmonyOS 版本，也没有改动生产输入代码。

### 问题2: 上游 GitHub archive 跳转在目标网络中超时

官方 codeload URL 在设备上可下载，SHA256 与原发布归档一致。`conandata.yml` 显式指定 `filename: finalcut-0.9.1.tar.gz`，让 Conan 正确选择 gzip tar 解包器。

---

## 五、测试环境

```text
目标系统：HarmonyOS 6.0 PC，aarch64
编译器：Clang/Clang++ 15.0.4，libc++
Conan：2.29.1
运行时依赖：ncurses/6.6；上游测试使用 CppUnit 1.15.1
上游命令：make -j1 check（目标级 28/30；方法级 297/311 PASS，5 BSD N/A，9 个 TIOCSTI 方法未注册）
Consumer：Conan test_package（test_finalcut、test_ohos_unicode，2/2 PASS；test_ohos_unicode PTY UI flow 1.50s；CTest 1.53s）
本地 CI：`python3 scripts/ohc-run.py finish finalcut 0.9.1 built` 中正式 W3 `build_and_test.sh` PASS；finish 后续 summary/submit 收尾部分完成，具体见 notes.md
证据：reports/upstream-tests-ledger.md、reports/tiocsti-probe.md、reports/w3-local-ci.log
源码 SHA256：6593b3c43ba1de98e4e0e3a563dbf9316fade71ef85c82e6b6f086184ec69a56
```

W3 中的 `conan create` 执行了 Conan `test_package` 的 2 个 CTest；上游 28 个适用目标由设备上的独立 `make -j1 check` 执行，逐项结果见 `reports/upstream-tests-ledger.md`。W3 日志中的 L1c“上游测试已执行”是仓库检测器误报，不作为上游测试通过证据。

*报告生成时间: 2026-10-02*
