# 上游默认启用 `-pg` 会令鸿蒙链接请求缺失的运行库

> 知识草稿。2026-09-28 为鸿蒙 PC 构建 GNU RPGE 0.0.3 时记录。

## 失败特征

RPGE 0.0.3 的 `src/Makefile.am` 将 `-pg` 无条件加入 `AM_CFLAGS`。在鸿蒙 PC 上，C 编译已完成，但 Clang/ld.lld 最终链接失败：

```text
ld.lld: error: cannot open gcrt1.o: No such file or directory
clang-15: error: linker command failed with exit code 1
```

失败的链接命令包含 `-pg`。该选项会让编译器驱动请求性能分析启动文件和运行库；本次使用的 OHOS SDK 未提供 `gcrt1.o`。

## 触发条件

- 目标平台：鸿蒙 PC AArch64，使用鸿蒙 Clang 15 工具链和 `ld.lld`。
- 构建系统：GNU Autotools/Automake 发布归档。
- 源码设置：`AM_CFLAGS` 等目标编译或链接选项中无条件包含 `-pg`。
- 产品要求：打包的应用程序不需要性能分析插桩。

## 证据与诊断

发布归档的 `src/Makefile.am` 中包含该选项。配置和编译完成后，生成的 RPGE 链接命令含有 `-Wall -pg`，随后链接器报告找不到 `gcrt1.o`。该链接命令已包含其他目标对象和解析出的软件包库，因此这一特征指向性能分析启动支持缺失，而不是 RPGE 依赖缺失。

从生成的 `src/Makefile.in` 中移除 ` -pg` 后重新构建，鸿蒙 `conan create` 成功完成，安装了 `usr/bin/rpge`，并通过设备端两项消费者检查（`--help` 和 `--version`）。配方不修改 `src/Makefile.am`；修改它会使旧版发布包尝试重新运行构建环境未安装的 Automake 1.13。

## 建议处理方式

1. 确认 `-pg` 来自上游 Makefile，并确认产品不需要性能分析。
2. 从发布归档使用的生成目标 Makefile 中移除该选项，然后重新构建并检查最终链接命令。
3. 保持编译器和目标三元组不变；更改它们无法提供缺失的性能分析运行库。

若产品必须提供性能分析输出，则不要移除 `-pg`。此时需要 SDK 提供兼容的性能分析运行库，并另行验证运行库配置。

## 适用范围与限制

目前的复现和成功修复来自单个上游应用 RPGE 0.0.3。这支持对鸿蒙链接故障作出具体诊断，但尚不能说明该情况在不同上游软件中普遍出现。将此草稿提升为通用知识规则前，应在第二个受影响的独立源码树或 SDK 配置中验证相同的 `-pg`/`gcrt1.o` 特征。

此条目不同于 Autoconf 的 `rpl_malloc` 交叉编译探测问题：RPGE 的 `-pg` 故障发生在最终链接阶段，处理方式是移除不受支持的性能分析请求；分配函数探测问题则通过提供正确的 configure 缓存答案解决。

## 复现定位

- 上游源码：`https://ftp.gnu.org/gnu/rpge/rpge-0.0.3.tar.gz`
- 配方：`archives/r/rpge/0.0.3/conanfile.py`
- 源码选项：`src/Makefile.am` 中的 `AM_CFLAGS`。
- 故障现场：鸿蒙设备上的 `conan create`，RPGE 最终链接阶段（`ld.lld: cannot open gcrt1.o`）。
- 修复后验证：`conan create` 退出码为 0；鸿蒙设备上的 `rpge --help` 和 `rpge --version` 检查通过。
