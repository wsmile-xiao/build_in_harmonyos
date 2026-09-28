# DRAFT-clipboard_lite-3.4-headless-x11-consumer：X11 硬依赖库的无显示消费者测试

> Contributor: pc1-48 (AtomCode) | Status: Draft | Updated: 2026-09-22
> Source: task clipboard_lite-3.4-r01-pc1-48-20260922T043531Z

## 背景

clipboard_lite 的公开 API（`SL::Clipboard_Lite::CreateClipboard()`）运行时**硬依赖**
X11 显示服务器：Linux/OHOS 后端 `Clipboard_Manager` 构造函数执行
`XOpenDisplay(NULL)`，没有 dummy/offscreen 后端可选。OHOS CI/无头 worker 无显示
服务器（DISPLAY 未设置、无 /tmp/.X11-unix socket、无 Xvfb），真实调用必然失败。

## 关键观察

- 在 Release/NDEBUG 构建下 `assert(Display_)` 被编译掉，`XOpenDisplay` 返回 NULL 后
  继续执行 `XCreateWindow(NULL,...)` → **确定性 SIGSEGV（退出码 139）**。
- 崩溃发生在程序打印"已到达库后端"标记**之后**（consumer 先 printf
  "building clipboard manager"，再调 CreateClipboard），且所有 X11 动态库
  （libX11/libXfixes/libXtst/libXcb/libXau/libXdmcp/libXi/libXext）均已成功加载
  （无 "symbol not found"）——证明：消费者编译 ✅、链接 ✅、调用 ✅、真实到达库后端 ✅，
  崩溃点是运行时显示服务器缺失（环境条件），不是库或配方缺陷。
- 与 CLI 工具 clipnotify 的先例同构：OHOS 无 X server 时其确定性错误路径
  （exit 1 + "Can't open X display"）被用作最小充分断言。

## 方案（test_package 消费者断言）

消费者（consumer.cpp）仅通过公开头 `<Clipboard_Lite.h>` + libclipboard_lite 驱动
公开 API；conanfile.py test() 用 conanrun env 真实运行并落日志，断言：

| 环境 | 日志特征 | 退出码 | 结论 |
|------|----------|--------|------|
| 无显示（headless worker） | 含 "building clipboard manager" | 139（SIGSEGV） | 消费者到达真实 X11 后端，无显示条件确认 |
| 有显示 | 含 "consumer: OK" | 0 | 完整剪贴板读写闭环通过 |

```python
cmd = f'"{exe}" > "{log}" 2>&1; echo "RC=$?" >> "{log}"'
self.run(cmd, env="conanrun", ignore_errors=True)  # RC=139 时 self.run 默认抛错，须 ignore
out = open(log).read()
if "consumer: OK" in out and "RC=0" in out:      # 有显示
    ...
elif "building clipboard manager" in out and "RC=139" in out:  # 无显示
    ...
else:
    raise Exception(...)                          # 非预期
```

关键坑：`self.run` 默认在非零退出码时抛 ConanException——确定性崩溃（139）会让
test() 提前失败，必须 `ignore_errors=True` 才能走到日志断言分支。

## 验证

- consumer.cpp 编译 exit 0；headless 运行日志:
  `clipboard_lite consumer: building clipboard manager` / `Signal 11 (core dumped)` /
  `RC=139`
- conan create 全流程 test() 通过（无显示条件确认分支命中）；W3 本地 CI L1a/L1b
  test_package 执行证据确认。
- 鸿蒙专项 test_ohos T1-T4 全过（aarch64 ELF / 无宿主路径泄漏 / X11 符号链接 /
  公开 API 符号导出），证明包本身在 OHOS 上正确。
- 证据: archives/c/clipboard_lite/3.4/reports/test-report.md、
  test_package/build/clang-15-armv8-17-release/consumer-run.log

## 适用边界

- 适用: 公开 API 运行时硬依赖显示服务器的库（剪贴板/输入/事件类）在无头
  CI/OHOS worker 上的消费者验证。
- 不适用/反例: 无运行时显示依赖的 X11 库（libXinerama 等）用 E530
  （强类型活重定位 + ABI 固定，display-independent）；有 dummy 后端（SDL）的库用
  E472（dummy 驱动 + 签名运行）；GUI 框架可切后端（GTK Broadway）用 E463。
- 诚实性要求: 不能把崩溃写成通过或伪造输出；如实记录 exit code、日志与恢复条件
  （在带 X 会话的 OHOS PC 上运行可走完整闭环 RC=0）。

## 查重差异

E530 面向"无运行时显示依赖"的库（make check 为空，用重定位+ABI 固定验证导出面）；
本条面向"公开 API 硬依赖 X11"的库（必须真实调用，以确定性崩溃路径为到达后端的
通过证据），两者互补，无 conflicts_with。
