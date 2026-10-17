# mmix

MMIX 是 Donald Knuth 设计的 64 位 RISC 体系结构及随架构发布的一套参考软件，上游为
<https://mmix.cs.hm.edu/>。本归档包含该发布中的四个命令行工具及验证所需的示例数据，不包含教材。

## 功能概述

| 程序 | 作用 |
|------|------|
| `mmixal` | MMIXAL 汇编器，把 `.mms` 汇编成 MMO 目标文件 |
| `mmix` | MMIX 模拟器，执行 MMO 程序，支持交互式跟踪与 `-D` dump |
| `mmotype` | MMO 目标文件检查器，列出符号、段与头部信息 |
| `mmmix` | 流水线元模拟器，按 `.mmconfig` 描述的功能单元配置给出周期计数与预测统计 |

## OHOS 适配

- 源码形态：CWEB（`.w`）文学程序，无 `configure`。构建时先用 `ctangle` 把 `.w` 展开成 C，
  再用目标编译器编译；构建系统为自定义脚本而非 autotools/cmake。
- 补丁：两个 CWEB change file（`.ch`），均为可移植性修复，不含 OHOS 专有接口。
  1. `mmmix-portability.ch`：驱动模块的 buffer 加 `static`，避免与 config 模块同名符号重复定义，
     从而不需要 `-fcommon`。
  2. `mmotype-portability.ch`：MMO 头部的 32 位时间戳按值转换为 `time_t` 再交给 `localtime`，
     避免 LP64 下把整数重解释为指针导致越界。未打补丁的上游代码会读出 1890 年。
- 按 K&R C 风格保留 GNU89（`-std=gnu89`）。**不要**添加 `_GNU_SOURCE`：它会暴露新版 glibc 的
  `fadd`/`fmul`/`fdiv`/`fsub`，与上游流水线枚举名冲突。
- 默认 PIE + RELRO/NOW；`static=True` 用于产出单文件静态可执行程序。
- 设备本地（非交叉）OHOS 构建会对四个新生成的 ELF 调用 `binary-sign-tool -selfSign 1` 签名，
  之后才能在本机执行。

## 依赖关系

- 编译期：`cweb/4.12.2`（`tool_requires`，提供 `ctangle`），C 编译器。
- 运行期：仅系统 C 库，无第三方运行时依赖。

## 已知限制

- 上游没有 `make check`。测试基准来自 README 记录的运行结果、`silly.run`/`silly.out` 记录，
  以及 49 个 `.mms` 汇编样例。
- 其中 `halves.mms`（GREGTOP 未知）与 `number1.mms`（Main 未定义）**未修改的上游 Linux 基线同样
  报错**，按负例检查，不能计入"正例全部通过"。

## 参考资料

- 上游发布页与源码：<https://mmix.cs.hm.edu/>
- MMIX 架构与 MMIXAL 说明：Knuth, *MMIXware: A RISC Computer for the Third Millennium*（随发布附带 `README`）
- 版本级适配记录见同目录下 `20160804/notes.md`
