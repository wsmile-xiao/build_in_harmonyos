# E238：嵌入式 Clang 头路径发现必须保留目标 sysroot

## 现象

嵌入式 Clang 工具完成配置、构建、安装和签名，版本命令也能成功，但一执行默认
C++ 输入就先报告：

```text
fatal error: 'features.h' file not found
```

随后程序还可能在错误恢复路径退出 139。关闭默认运行时后，纯 C 符号调用可以成功，
说明首先失败的是系统头搜索，而不是 JIT 可执行内存或动态符号解析。

## 根因

目标 `clang++ -xc++ -E -v /dev/null` 的搜索列表通常同时包含：

1. libc++ 头目录；
2. 当前 Clang 的 resource headers；
3. `sysroot/usr/include/<target-triplet>` 架构目录；
4. `sysroot/usr/include` 通用目录。

只按路径名是否含 `++` 过滤会稳定保留第一类，却丢失第三、第四类。libc++ 继续间接
包含 libc 的 `features.h` 时便找不到目标系统头。

另一个容易漏掉的分支是运行时相邻编译器。工具可能先查询安装目录旁的 `clang`，
只有结果完全为空才使用配置期路径。若相邻编译器返回 libc++ 但没有 sysroot，结果
虽然非空，仍不完整；此时“非空即成功”会遮蔽配置期已经验证过的完整 fallback。

## 修复

1. 只在 OHOS/HarmonyOS 目标路径中额外保留与当前 sysroot 匹配的架构和通用系统头。
2. 运行时先保留相邻编译器给出的有效目录顺序，再遍历配置期列表，只追加缺失的绝对
   target sysroot 路径；不能只检查列表是否为空。
3. 比较前去除尾 `/`，避免同一目录重复。相邻结果完全为空时保留上游整体 fallback；
   无法安全补合并的其他实现也应整体回退到配置期完整列表。
4. 保留当前嵌入式 Clang 自身的 resource headers。不能为了补系统头而混入旧 SDK
   Clang resource 目录。
5. Linux 和其他平台保持上游原有过滤行为，避免扩大平台补丁范围。
6. 若运行时源码要复用 CMake 的 OHOS/HarmonyOS 判断，注入项目私有特性宏，并把
   `PRIVATE` 定义放到真正编译该源码的 target。LLVM helper 可能把源码放进
   `obj.<name>` 对象库，外层库不会把定义逆向传播给对象库；必须从
   `compile_commands.json` 回读目标源码的实际命令。

## 验证

验证必须覆盖配置期和正式安装布局两条路径：

- `OHOS` 与 `HarmonyOS` 两种 CMake 系统名；
- 相邻 clang 返回完整 sysroot、只返回 libc++、完全无结果三种情况；
- 架构 sysroot 与通用 sysroot 都存在且最终顺序稳定、无重复；
- 含空格、尾斜杠和相对路径输入不会破坏解析；
- 旧 SDK resource headers 被排除，当前 Cling/Clang resource headers 仍保留；
- `cling -v` 回读最终搜索顺序，标量、C 接口和不同标准库消费者分别在独立进程中
  退出 0。

Cling 1.3 的 Build #9206 提供了 `features.h` 首错证据。最终候选源码 SHA-256 为
`a07fb914...` 与 `ae466d6b...`，两份新增补丁通过 `git apply --check` 和 GNU patch
2.7.6 `--fuzz=0` 的 fresh 官方源码重放。签名 ELF 夹具覆盖完整、仅 libc++、空发现、
尾斜杠与含空格路径 5 种配置，结果为 5/5；签名 package 以自身 `lib` 作为唯一
`LD_LIBRARY_PATH`，52 个 C++17 消费者与 1 个版本入口合计 53/53。矩阵与版本日志
SHA-256 分别为 `74d98018859ec14e9d7eef4a0ba9a90e10ef68691355770ef2d423a7f9f5a792`
和 `b6403da9b22abe355ad17208a336e658322c5d1d7ff646ca7b9229237ba4aef4`。
真实 compile database 中 `CIFactory.cpp` 的 1/1 命令包含私有特性宏，宏的 38 个编译
项均位于 `lib/Interpreter`；OHOS/HarmonyOS/Linux 独立路由夹具为 3/3。
当前修复提交后的正式 CI 尚待新 HEAD 执行，不能用本地真机日志替代 CI 结论。

## 禁止做法

- 不得把 `Signal 11` 直接归因于 JIT，而忽略它之前的第一条编译诊断。
- 不得把任意非空 include 列表当成完整搜索闭包。
- 不得手工硬编码单台设备的绝对 SDK 路径。
- 不得把旧版 Clang resource headers 与嵌入式前端的新版本 resource headers混用。

## 关联知识

- E077：CMake 交叉编译探测与宿主/目标边界。
- E140：OpenHarmony 工具链可能使用 `OHOS` 或 `HarmonyOS` 平台名。
