# DRAFT：测试程序名里有 device / receiver ≠ 需要真实硬件 —— 判据只能是夹具构造函数

> 状态：草稿（待知识库主编 promote）
> 来源：libratbag 0.18 适配，`archives/l/libratbag/0.18`
> 类别：testing / portability / rule4 / meson / check

## 错误特征

这不算一条「报错」，而是一种**判定错误**，特征是**通过率被大幅少报**：

在一台没有 `/dev/hidraw*` 节点、没有 udev 守护进程的 CI 机器上，
上游有 4 个名字里带 `device` 的 C 测试程序：

```
test-context      (6 个用例)
test-device       (23 个用例)
test-util         (2 个用例)
test-iconv-helper (4 个用例)
```

按名字推断「`test-device` 要插一只鼠标才能跑」，就会把整套 35 个用例判为
「平台受阻、0 通过」，于是报表写成「上游 10 程序 / 35 用例，本平台 0 通过」。
**而实际口径是 7 程序 / 35 用例通过（程序 70%、用例 100%）。**

识别信号：某个测试程序的**名字**描述的是硬件或外部服务，但它的**夹具构造函数**
是一个 `*_test_*` / `*_mock_*` / `*_dummy_*` / `*_fake_*` 工厂，且该工厂的实现
里没有任何 `open()` / `ioctl()` / udev 枚举 / socket 连接。

## 触发条件

同时成立：

1. 上游是**驱动库 / 系统服务库**一类「名字里天然带设备名词」的项目；
2. 它的测试夹具为了让开发机也能跑，构造了**内存内的虚拟设备**；
3. 适配者只看测试程序名（或只看到「这是个鼠标驱动库」），没读夹具源码。

libratbag 0.18 的现场（`test/test-device.c`）：

```c
/* 夹具走 ratbag_test_device_new()（实现见 src/libratbag-test.c）：
   全程 zalloc/malloc + 字段赋值，不开 hidraw、不枚举 udev。 */
```

于是 profile / 分辨率 / 按键 / LED 的读写全部落在内存结构上，
**不需要插任何硬件**。

## 根因分析

### 名字描述的是「测什么」，不是「需要什么才能测」

`test-device` 里的 `device` 说的是**被测对象**，不是**运行前提**。
把它读成运行前提，是把「领域名词」当成了「资源依赖」。

### 正确的判据只有一条：夹具构造函数

必须打开源码，找到测试程序的 main() / suite 初始化，看它构造的被测对象从哪来：

| 夹具来源 | 结论 |
|----------|------|
| `*_test_device_new()` / `*_mock_*` / `*_fake_*`，实现里无 I/O | **不需要**外部资源，必须通过 |
| `open("/dev/...")`、`ioctl(..., HIDIOCGRAWINFO)` | 需要真实设备 |
| `udev_new()` / `udev_enumerate_*` | 需要 udev 守护进程 |
| `g_test_dbus_up()` / `socket(AF_UNIX)` / `connect()` | 需要私有总线 / 守护进程 |

libratbag 实证：10 个测试程序里只有 3 个真的需要外部资源
（`ratbagctl-test` 要私有 D-Bus + `ratbagd`；`python-black-check` /
`python-ruff-check` 要 pip 装好的 `black` / `ruff`），另外 7 个（4 个 C +
3 个纯 Python 数据校验）无外部依赖。

### 为什么这个误判代价特别大

- **rule4 意义上就是少报**：把 35 个可执行的用例写成 0 通过，评审据此无法判断
  适配质量；
- **掩盖了补丁的作用**：这 4 个程序拷问的是 libratbag 的核心逻辑（profile /
  分辨率 / 按键 / LED 的读写与序列化），它们全绿才说明适配没伤到库本身；
  报成 0 等于把最有价值的那部分证据扔了；
- **误判会自我强化**：一旦在配方里把 `test-device` 写进「受阻清单」，后续所有
  评审都按这个清单看，没人会再去读夹具源码。

## 正确做法

1. **先分类，再写配方**：按夹具构造函数把上游每个测试程序分成
   「内存替身 → 必须通过」与「真实外部资源 → 如实声明受阻」两组；
2. 配方里用**三个分开的集合**表达：`UPSTREAM_TEST_PROGRAMS`（上游注册了几个）、
   `REQUIRED_PASSING_PROGRAMS`（必须通过的）、`BLOCKED_PROGRAMS`（声明受阻的）；
3. `build()` 内**全量执行**上游套件，不吃退出码，回读汇总块硬断言：
   - `Timeout == 0`、`Unexpected Pass == 0`；
   - `Fail` 的**数量与身份**恰好等于受阻集合（多一个 = 真实回归）；
   - `Ok` ≥ 必须通过的集合大小，且每个名字都出现在日志里（挡住「用例根本没注册」）；
4. 声明时**两个口径都写**：程序数（本例 7/10 = 70%）与用例数（本例 35/35 = 100%）。

## 判据 / 复现命令

```sh
# 判据一：夹具是不是内存替身（唯一可靠的判据）
grep -n "_test_device_new\|static struct .*_device" test/test-device.c | head
sed -n '/ratbag_test_device_new/,+30p' src/libratbag-test.c
#   → 全程 zalloc/malloc + 字段赋值，无 open()/ioctl()/udev → 不需要硬件

# 判据二：夹具里有没有真正的外部资源调用
grep -n 'open(\|ioctl(\|udev_\|g_test_dbus\|socket(\|connect(' test/*.c
#   → 命中哪个程序，哪个程序才需要外部资源

# 判据三：这台机器上到底有没有那些资源
ls /dev/hidraw* 2>/dev/null ; echo "exit=$?"      # 空 → 没有设备
command -v dbus-daemon ; echo "exit=$?"           # 空 → 没有守护进程
command -v black ; command -v ruff                # 空 → 没有代码风格工具

# 判据四：跑一遍看汇总块（不要看退出码）
meson test -C <builddir> --print-errorlogs
sed -n '/^Ok:/,/^Timeout:/p' <builddir>/meson-logs/testlog.txt
#   → 期望 Ok: 7  Fail: 3   （而不是 Ok: 0  Fail: 10）
```

## 反模式（不要这么做）

| 反模式 | 为什么不行 |
|--------|-----------|
| `meson test --no-suite device` / `--gtest_filter=-.*device` 把「看起来要硬件」的过滤掉 | 用猜测把可能通过的用例一起删了；rule4 判少报，回归保护丢失 |
| 在 CI 里 `mkdir` / `mknod` 伪造一个 `/dev/hidraw` 节点 | 改变被测环境而非适配库；OHOS 沙箱下也做不到，与真机行为不一致 |
| 把受阻程序的断言删掉、直接 `return 0` | 把「已知不支持」伪装成「已验证正确」，比过滤更糟 |

## 迁移范围

同一种形状在任何语言、任何测试框架里都成立：**判断「这个测试需要什么才能跑」
只能读夹具，不能读名字**。反过来也成立 —— 夹具读得越细，
`REQUIRED_PASSING_PROGRAMS` 这个集合就能定得越大，报告出来的通过率越接近真实。

同族条目：`DRAFT-libgsystemservice-0.3.0-session-bus-tests-cannot-run-in-the-ohos-sandbox`
（讲的是「已经确定受阻的程序该怎么处理：照常执行、按身份+数量硬核对、不得 SKIP」；
本条讲的是**前一步**：怎么确定哪些程序才真的算受阻）。
