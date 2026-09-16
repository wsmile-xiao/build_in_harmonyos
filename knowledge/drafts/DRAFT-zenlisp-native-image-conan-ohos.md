# DRAFT-zenlisp-native-image-conan-ohos：自生成运行时 image 的 OHOS Conan 原生闭环

> **Contributor**: codex | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-14
> **Source event**: zenlisp 2013.11.22 HarmonyOS PC 适配，Shadow CI run `20260914T002209Z-dfbfd1ac80-20807`

## 知识类型与提升边界

本条目是路径 B 知识库扩展候选，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote 或已经获得 B 类认定；最终分类由知识库维护者和赛事评审决定。

本条目的新增点不是单独使用 `-D_GNU_SOURCE`、单独调用 `patch`，也不是“Conan
test_package 通过”本身，而是把**构建期必须执行目标解释器生成 image、安装后运行时
资源路径重定位、原生签名、上游完整回归和消费者测试**串成一个可复用的 Conan 闭环。

## 适用场景

适用于以下类型的 HarmonyOS/OHOS 包：

- 上游是小型 C/C++ 解释器、编译器或自举工具，构建产物会在构建阶段立即执行；
- 上游 Makefile 先编译可执行文件，再用该可执行文件生成默认 image、字节码、表或其他
  后续构建输入；
- 上游默认把 image 或运行时库写入 `/usr/local`、源码目录或构建机绝对路径；
- 安装后的命令需要继续加载包内的脚本、标准库或数据文件；
- 上游有可直接运行的确定性回归脚本，但构建系统依赖 GNU/Linux 主机工具语义。

普通只编译、不执行目标程序的静态库不需要本条方法。只有在 `test_package` 中运行一个
独立 marker 也不能满足本条方法。

## 问题模型

### 1. 构建不是单纯的 compile/link

zenlisp upstream 的核心流程是：

```text
编译 zl.c -> 运行 zl -> (load base) (dump-image zenlisp) -> 运行 test.l
```

因此，只有交叉编译出 `aarch64` ELF 不能证明配方可构建。目标解释器必须在 OHOS
原生环境执行，且在第一次执行前完成 HarmonyOS ELF 签名。`can_run(self)` 应作为构建
门槛；不能在不可运行的交叉环境中伪造 image 或把上游测试改成 host 执行。

### 2. 构建路径与安装路径不同

上游默认 image 路径适合 `/usr/local/share/zenlisp`，而 Conan package 的真实路径位于
缓存目录。若保留编译期绝对路径，安装后的 `zl` 会找不到 `zenlisp` image 或 `.l`
标准库。

### 3. OHOS libc 的声明面与上游默认编译选项不同

zenlisp 使用 `strdup()`，但源文件没有显式 feature-test macro。HarmonyOS Native SDK
下需要通过 `-D_GNU_SOURCE` 获得声明；这属于 OHOS musl 兼容性前置条件，而不是通过
修改业务代码绕过编译器诊断。

### 4. Conan 补丁应用器与设备工具链可能不一致

首次 Shadow CI 中，Conan `conan.tools.files.patch()` 在 OHOS 环境对该 git-style
unified diff 报：

```text
source/target file does not exist
```

同一个补丁在设备 Toybox `patch -p1` 下可以干净应用。修复后的配方通过配置的原生 shell
显式调用设备 `patch -p1 -i <patch>`，仍保留补丁文件、导出逻辑和 L4 检查。这个动作
只能在目标环境复现 Conan 应用器失败后采用，不能用 `patch -p1 --dry-run` 替代 Conan
实际语义，也不能借此跳过补丁质量门禁。

## 推荐方法

### 1. 把 native execution 当作构建契约

在 `build()` 中按以下顺序执行：

1. 应用最小源码补丁；
2. 通过 Conan profile 的绝对编译器路径编译目标解释器；
3. 对 OHOS 目标 ELF 执行设备签名工具；
4. 运行目标解释器生成默认 image；
5. 在同一源码/构建目录运行上游回归；
6. 只有全部步骤成功后才进入 `package()`。

任何 image 生成失败、签名失败、目标程序启动失败或上游测试失败都必须让
`conan create` 返回非零。

### 2. 用环境变量覆盖安装后的 image 路径

补丁应保留编译期默认值作为兜底，同时允许运行时覆盖：

```c
env_image = getenv("ZENLISP_IMAGE");
if (env_image != NULL && *env_image != 0)
        strncpy(Image, env_image, MAX_PATH_LEN - 1);
else
        strncpy(Image, DEFAULT_IMAGE, MAX_PATH_LEN - 1);
```

`package_info()` 从实际 `package_folder` 导出：

- `ZENLISP_IMAGE=<package>/share/zenlisp/zenlisp`
- `ZENSRC=<package>/share/zenlisp`

这样 Conan cache、Shadow CI run 目录和最终安装目录都使用同一份运行时契约。脚本库
可以集中复制到包内运行时目录，避免依赖源码树或构建目录。

### 3. 保留上游完整测试并只做输出归一化

如果上游测试输出包含随执行位置变化的错误行号，可以在比较前只归一化该动态字段，
例如将 `* 123: ` 变成 `* `；不得删除测试输入、按平台名整体 skip 或把未执行项计为
通过。`test_package` 另行验证安装布局和代表性行为，不能替代上游套件。

### 4. 设计有包归属的消费者测试

对于解释器/命令行工具，消费者测试至少应同时证明：

- 包内 `bin/zl` 存在且可执行；
- 默认 image 存在；
- `ZENSRC` 下的标准库可以被加载；
- 一个核心语言行为和一个数值/库加载行为返回预期结果；
- 产物确实来自被测 Conan 包。

只执行 `zl --version` 或 `zl --help` 不足以覆盖没有这类选项的上游工具；此类工具可
在 L2 记录 `skip_no_version_or_help`，但不能把 L1 或 `test_package` 降级成 marker。

## 复用与新增边界

| 内容 | 处理 |
|---|---|
| OHOS `strdup()` 声明需要 `-D_GNU_SOURCE` | 复用 E032 类 musl feature-test 经验，不作为本条唯一创新 |
| OHOS ELF 签名后才能执行 | 复用 E077 的签名与运行能力边界 |
| git-style patch 的路径层级和校验语义 | 参考 E526；本条仅记录 Conan 应用器在本目标环境的实测差异 |
| 编译器与运行时资源路径分离、image 可重定位 | 本条新增的可迁移方法 |
| 构建期生成 image、原生执行、完整上游测试、安装后消费者测试的统一顺序 | 本条新增的流程闭环 |

## 已验证证据

- 本地 HarmonyOS SDK 目标编译：`aarch64-linux-ohos`，加入 `-D_GNU_SOURCE` 后通过，
  仅有 C89 风格未使用参数警告。
- 首轮 Shadow CI：补丁阶段失败，错误为 Conan 补丁应用器找不到 source/target 文件；
  未将该轮计为成功。
- 修复后 Shadow CI：run `20260914T002209Z-dfbfd1ac80-20807`，`conan create` 退出码
  `0`，设备 `binary-sign-tool` 签名成功，默认 image 生成成功。
- 上游回归：`test.l` 与 `test.OK` 完整比较，`633/633` 通过。
- `test_package`：`7/7` 断言通过，包含安装后的二进制、image、标准库加载、算术行为
  和许可证输出。
- Shadow 汇总：`Total: 1 / Success: 1 / Failed: 0`；L0、L1、L4、L5 通过；L2
  由于 `zl` 没有 `--version/--help` 语义而非阻塞跳过。

## 复现入口

```sh
conan create archives/z/zenlisp/2013.11.22 --build=missing
```

Shadow CI 必须使用单包隔离 job、`ohos-aarch64` profile 和原生 OHOS shell。日志至少
应包含补丁应用、编译、签名、image 生成、上游测试、`test_package` 及 L0-L5 结果。
不得在草稿、manifest 或 PR 中写入真机 IP、账号或私钥路径。

## 禁止做法

- 不要只做交叉编译后声称 image 和上游测试已验证。
- 不要伪造或复制 host 生成的 image 到 OHOS 包中。
- 不要把 Conan cache 绝对路径编译进最终运行时且不提供覆盖机制。
- 不要在签名失败、image 生成失败或上游测试失败时继续打包。
- 不要删除上游回归输入，或把 `test_package` marker 当成完整上游测试。
- 不要把 `zl` 的 L2 版本/帮助不适用写成库功能失败，也不要把它写成通过。
- 不要把 E032、E077 或 E526 的既有内容重复申报为本条新增知识。

## 证据来源

- `archives/z/zenlisp/2013.11.22/conanfile.py`
- `archives/z/zenlisp/2013.11.22/manifest.yaml`
- `archives/z/zenlisp/2013.11.22/notes.md`
- `archives/z/zenlisp/2013.11.22/patches/0001-relocatable-default-image.patch`
- `archives/z/zenlisp/2013.11.22/test_package/conanfile.py`
- `archives/z/zenlisp/2013.11.22/test_package/test_zenlisp.sh`
- Shadow CI run `20260914T002209Z-dfbfd1ac80-20807`
