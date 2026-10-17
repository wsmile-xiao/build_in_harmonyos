# KConfig 系部件的往返测试：XDG 根要钉死，种子要由被测程序自己写

> Draft: DRAFT-knotifyconfig-6.26.0-xdg-hermetic-kconfig-roundtrip
> Stem: `knotifyconfig-6.26.0-xdg-hermetic-kconfig-roundtrip` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-knotifyconfig-6.26.0-xdg-hermetic-kconfig-roundtrip
- **严重度**: 1
- **类别**: testing, portability, environment, build-system
- **触发工具**: conan | cmake | ctest | clang
- **阶段**: testing

## 错误特征

失败信息看起来像功能坏了，其实往往是测试本身的问题：

```
FAIL: Sound is "", expected "bell.ogg"
FAIL: seed Action entry did not survive the seed write
---> ctest: test_knotifyconfig Failed
```

典型场景：**第一次运行通过，第二次运行失败**。在 conan 的 `test_package`
里这很常见——`cmake.test()` 与随后的 `self.run(executable)` 会各跑一次
同一个二进制。

## 根因分析

### 一、KConfig 的落盘位置不是"当前目录"

`KConfig(name)` 会把裸文件名解析到
`QStandardPaths::writableLocation(GenericConfigLocation)`，也就是
`$XDG_CONFIG_HOME`（未设时才退到 `~/.config`），拼上文件名。消费者测试
若不钉死 XDG 环境，就会去读写测试机上**真实的** `~/.config`：结果既不确定
（取决于 worker 预置了什么），又可能互相污染。

### 二、输入来源不止一个

KDE 这类部件常常"可写配置 + 若干只读配置源"一起读。
`KNotifyEventList::fill()` 除了打开
`$XDG_CONFIG_HOME/<app>.notifyrc`，还会

```cpp
QStandardPaths::locateAll(QStandardPaths::GenericDataLocation,
                          "knotifications6/" + appname + ".notifyrc")
```

去 `$XDG_DATA_DIRS` 扫只读源再 `addConfigSources()`。只钉
`XDG_CONFIG_HOME` 而放任 `XDG_DATA_DIRS` 保持默认
（`/usr/local/share:/usr/share`），测试结果依旧依赖宿主。

### 三、测试驱动方式决定了幂等性

如果种子文件由 Python 侧写好、C++ 侧只做"读-改-写"：

| 运行 | 文件前置状态 | 结果 |
|------|--------------|------|
| 第 1 次（`self.run`） | `Action=Sound|Popup` | 通过，写完变成 `Action=Popup` |
| 第 2 次（`cmake.test()`） | `Action=Popup` | **前置断言失败**（"种子应当是 Sound\|Popup"） |

于是"测试不幂等"被误读成"功能回归"。

## 解决方案

**主方案**: pin-xdg-roots-and-self-seed-in-binary

### 规则 1：钉死全部 XDG 根

在 `test_package/conanfile.py` 的 `test()` 里，把五个变量都指向构建目录下
的临时树，**并先 `os.makedirs` 建出来**：

```python
home = os.path.join(self.build_folder, "ohos-xdg")
for sub in ("config", "configdirs", "data", "datadirs"):
    os.makedirs(os.path.join(home, sub), exist_ok=True)
env.define("HOME", home)
env.define("XDG_CONFIG_HOME", os.path.join(home, "config"))
env.define("XDG_CONFIG_DIRS", os.path.join(home, "configdirs"))
env.define("XDG_DATA_HOME",   os.path.join(home, "data"))
env.define("XDG_DATA_DIRS",   os.path.join(home, "datadirs"))
```

`XDG_CONFIG_HOME` 指向的目录要先建好——`writableLocation` 对不存在路径的
行为依实现而定，建出来最省事。

**判据**：CI 日志里看不出任何 `~/.config` 或 `/usr/share` 的痕迹；把宿主
`$HOME` 换成一个空目录重跑，结果不变。

### 规则 2：种子文件由被测程序自己写

C++ 测试开头用自己的路径逻辑**覆盖写**一份配置，然后再构造部件：

```cpp
const QString path = QDir(QString::fromLocal8Bit(qgetenv("XDG_CONFIG_HOME")))
                         .filePath(QStringLiteral("knotifyconfig-consumer.notifyrc"));
writeSeedFile(path);   // 每次运行都重置到同一前置状态
```

Python 侧只负责建目录和设环境变量。这样无论被跑几次、由哪个入口跑，前置
状态都相同——测试对驱动方式免疫。

### 规则 3：找可观测信号，别只看文件

这类部件的内部状态（选中了哪个事件、文本框里是什么）大多不可从外部读取。
`KNotifyConfigWidget` 只暴露一个 `changed(bool)` 信号，但足够把流程钉住：

| 断言 | 证明什么 |
|------|----------|
| `disableAllSounds()` 发出恰好一次 `changed(true)` | 种子事件确实被解析进了事件表，且带 Sound（否则它内部 `changed` 标志为 false，不发信号） |
| `save()` 发出恰好一次 `changed(false)` | 写盘真的发生了 |
| 读回文件：`Action` 变了 / `Sound` 未变 / 同组 `Name` 未变 | 值对不对、改动范围是否正确 |

文件内容断言负责"值对不对"，信号断言负责"流程真的走了"。**缺了信号断言，
一个静默失配的 `selectEvent()`（事件 id 写错，或前面讲过的那类控件降级
把 `currentElement` 弄丢）会让测试变成永远通过的空壳**——因为如果什么都没
选中，`save()` 不会写 `Sound`，KConfig 会把原值原样保留下来，
"Sound 仍然是 bell.ogg" 这条断言反而会**假通过**。

### 规则 4（退化方案）

若部件连 `changed` 类信号都没有，退而求其次：断言往返前后**同一 group 里
其它键未被破坏**（本例：`Name=Round Trip` 仍在）。它至少能证明写回的是
同一个文件、KConfig 的 group 没被整体重写掉。

## 验证

```sh
conan create archives/k/knotifyconfig/6.26.0 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing

# 幂等性：同一个二进制跑两次都应通过
ctest --test-dir <build_folder> --output-on-failure
<build_folder>/test_knotifyconfig
```

## 关联条目

- 与 `DRAFT-knotifyconfig-6.26.0-ui-customwidget-kiowidgets-swap` 是同一包的
  两条独立教训：那条讲**怎么改**（.ui 控件降级三关），本条讲**怎么验**
  （XDG 钉死 + 自播种 + 信号断言）。
- "先找可观测行为再写断言"与本仓库 `DRAFT-libsvgtiny` 系列、
  `opencsg-1.8.2-ohos-headless-context-dependent-test-contract` 的思路同源：
  禁止用 grep 二进制这类间接痕迹代替行为断言。
