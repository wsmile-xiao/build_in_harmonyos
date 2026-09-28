# 静态 ncurses 应用的 Conan 运行依赖：不能丢掉 terminfo 数据

> 待维护者审查的路径 B 候选草稿；触发包 tinyirc 1.1.dfsg.1，HarmonyOS PC AArch64 / Clang 15 / Conan 2.29.1，2026-09-25。它不代表路径 B 已受理、分数已确定或免答辩资格已确认。

## 现象

目标机已能以 `-lncursesw` 静态链接 tinyirc。Conan 最初的配方使用普通 `self.requires("ncurses/6.6")`；本包构建、装包成功，但下游 `test_package` 的依赖图显示 `Skipped binaries: ncurses/6.6`。虽然发布的 ncurses 配方在 `package_info()` 里声明 `TERMINFO` 和 `TERMINFO_DIRS`，测试进程中仍没有 `TERMINFO`，无法定位 `vt100` 的 terminfo 条目。旧源码在连上 IRC 服务器后才会调用 `tgetent`，仅运行 `--version` 或仅链接成功不能暴露这个问题。

本次第一次正式 `conan create` 的日志 `conan-create4.log`（SHA-256 `e1bd788cdeed9d9b07dc7252b1530187e5ca64ba51adcfa88a7b981e8120e4fa`）：包创建后，消费者脚本因 `TERMINFO is required for the ncurses termcap database` 失败。关键原文：

```text
Skipped binaries
    ncurses/6.6
AssertionError: TERMINFO is required for the ncurses termcap database
ERROR: tinyirc/1.1.dfsg.1 (test package): Error in test() method, line 22
```

此断言由测试 harness 主动给出，用来把缺少运行时数据的错误从后续 `tgetent` 失败中分离出来；它不是上游 tinyirc 的原文报错。

## 根因与修复

静态链接使可执行文件不再需要动态加载 ncurses 的 `.so`，但 **terminfo 是独立的运行时数据**，并不会嵌入静态归档。对 `package_type="application"` 的 Conan 包，普通依赖在下游图中可被视为仅供构建/链接而跳过包二进制；该包的 `runenv_info` 因而不会进入消费者的运行环境。

配方改为：

```python
def requirements(self):
    self.requires("ncurses/6.6", run=True)
```

再用 `VirtualRunEnv` 运行已安装的 tinyirc。目标机 `conan-final3.log` 的下游图中，`ncurses/6.6` 与 tinyirc 均为已安装依赖，TERMINFO 被注入；强制重建本包并通过 1/1 集成场景：USER/NICK、PING/PONG、收发 PRIVMSG、QUIT、退出码及收到消息的输出。关键原文是 `Source ... retrieved from local download cache`、`Package ... created` 和 `PASS: native IRC handshake, PING/PONG and PRIVMSG`。最终日志 SHA-256 为 `50299ffd2d667258a900e0599cf4b10aaac1d03ff0e7ac81acfddf832a032a78`。目标机当时访问 GitHub 超时，因此该缓存以 SHA-256 验证过的同一上游归档预先填充；正式配方的来源 URL 没有改变。这说明修复闭合了 Conan 消费者运行环境；**不等于**任意脱离 Conan 的裸运行环境已安装 terminfo 数据。

## 复验与边界

在配置 `ohos-aarch64` profile 和 `ohpcd` 远端的目标机，从仓库根目录运行：

```sh
conan create archives/t/tinyirc/1.1.dfsg.1 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 \
  -r=ohpcd --build=tinyirc/1.1.dfsg.1 -c tools.build:jobs=1
```

本知识的适用条件是“静态库仍有运行时数据或工具”，并且对应 Conan 依赖确实通过 `runenv_info` 发布数据路径。其他项目可能选择把 terminfo 数据复制到应用包中；例如仓内 ne/3.3.4 的方案属于复制数据，和这里保留依赖的 `run=True` 机制不同。复制或保留依赖各有体积与部署权衡，不能混称为同一新知识。tinyirc 的另一问题——应用 UID 无 passwd 条目导致 `getpwuid` 返回 NULL、`getutline` 在目标头文件不可用——由独立的源码特性守卫补丁处理；它不是本草稿的新颖性主张，也不能用 `run=True` 修复。
