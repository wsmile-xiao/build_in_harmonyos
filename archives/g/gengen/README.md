# gengen

**GNU gengen — 通用代码文本生成器 — 读 .cc_skel 骨架文件，生成带缩进文本生成能力的 C/C++ 类**

## 命令行工具

- `gengen`

## 构建

- 构建系统：autotools
- 许可证：GPL-3.0-or-later
- 上游：https://ftp.gnu.org/gnu/gengen/
- 官方主页：https://www.gnu.org/software/gengen/

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 1.4.2 | built | 首个鸿蒙 PC conan 配方 |

## 为什么做这个包

gengen 是 GNU 代码生成器家族的底层组件：gengetopt（命令行参数解析器生成器）等工具的代码生成能力即来自 gengen 生成的类。需要把 gengetopt 生态或自研代码生成器移植到鸿蒙 PC 的场景会用到它。

## 用法示例

写一个最小骨架 `demo.cc_skel`：

```
demo begin
  value=@value@
@IF@ flag @THEN@
  flag=yes
@ELSE@
  flag=no
@ENDIF@
demo end
```

生成 C++ 生成器类：

```bash
gengen --no-gen-version -i demo.cc_skel --file-name demo.h --gen-name demo
```

生成的 `demo.h` 含 `demo_gen_class`：`set_value("42")`、`set_flag(true)` 后调用
`generate_demo(output_stream)` 即可按骨架输出文本（`@VAR@` 替换、`@IF@/@ELSE@`
分支、缩进控制）。

## 鸿蒙适配要点

- 产物只有 `bin/gengen`（libgengen.a 为 noinst 不安装，无公开头文件），工具型包声明 `commands.json`
- 2010 年的 config.guess/config.sub：显式 `--build=--host=aarch64-unknown-linux-gnu` 跳过猜测
- configure 内嵌 `umask 077` 已按知识库 E011 受控方案替换为 022
- flex 生成码含 `register`，C++17 profile 下已移除
- 设备无 texinfo：`MAKEINFO=true` + 顶层 SUBDIRS 收窄为 `lib src`
