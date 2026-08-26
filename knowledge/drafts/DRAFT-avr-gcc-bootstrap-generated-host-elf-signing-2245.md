# DRAFT-avr-gcc-bootstrap-generated-host-elf-signing-2245 - 引导构建期宿主 ELF 签名

> **Contributor**: xuguowei | **Status**: PRE-VERIFICATION DRAFT | **Updated**: 2026-08-18
> **Source event**: avr-gcc-bootstrap 14.2.0, issue #2245

## 知识类型与提升边界

本条目是路径 B 知识库扩展候选，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote 或已获 B 类认定；是否提升及最终分类由知识库维护者和赛事评审决定。

当前状态为真机 r12 待验证。r1-r10 已逐步定位签名、HMDFS helper、目标工具分发与构建范围
问题；r11 推进到 `all-target-libgcc`，在可选 fixed-point/libf7 组合编译中耗尽一小时 runner
窗口。提交 `c2089cc318` 已关闭该非引导必需功能；由于真机 SSH 端点随后不可达，r12 尚未
启动。最终成功计数只会在完整 `conan create`、上游自检、编译抽样与消费者测试通过后更新。

## 适用场景

本方法适用于同时满足以下条件的自举或工具链构建：

- 构建运行在 HarmonyOS 宿主机，内核要求原生 ELF 带有效 `.codesign`；
- 构建系统用宿主编译器生成辅助程序、代码生成器或内部编译器；
- 新程序在同一个构建图中很快被后续规则执行；
- 同一编译器还可能生成对象文件、静态库或不同架构的目标 ELF；
- 最终工具必须保持原生 ELF 身份，供下游直接探测和执行。

普通“安装结束后对 bin/ 批量签名”的项目不需要本方法。只生成且不执行目标程序的纯交叉
编译也不属于本条目。

## 问题模型

GCC stage-1 构建并不是简单的“全部编译完成，再统一安装”。它会反复发生以下序列：

1. 宿主 Clang 链接一个新的 GCC 构建辅助程序；
2. Makefile 在后续规则中立即执行该程序生成表、头文件或编译器数据；
3. 新生成的 `xgcc`/`cc1` 又参与目标代码和 `libgcc` 构建。

在普通 Linux 上，链接成功且具有执行位即可进入第 2 步。在 HarmonyOS 上，缺少有效
`.codesign` 的宿主 ELF 会在首次执行时被拒绝。只在 `all-gcc` 完成后扫描会迟于首次执行；
只在 `package()` 扫描更迟。

另一方面，包装器不能对每个 `-o` 输出盲目签名。`-c`、`-S`、`-E` 以及 AVR 目标链接
会产生非宿主可执行文件。对这些输出签名会污染目标产物或直接失败。

## 推荐方法

### 1. 在链接边界拦截，而不是等待安装阶段

在 Conan 的 OHOS 构建环境中，把 `CC`、`CXX`、`CC_FOR_BUILD` 和 `CXX_FOR_BUILD` 指向
同一个签名包装器。包装器先原样调用真实编译器；只有真实命令成功后才分析输出。

解析必须覆盖分离的 `-o file` 与紧凑的 `-ofile`，并识别 `-c/-S/-E`。若未显式给出输出且
是链接命令，才考虑默认 `a.out`。

### 2. 用 ELF 类型而不是文件名或执行位分类

对候选输出运行 `readelf -h`，只有宿主 `EXEC` 或 `DYN` 才进入签名流程。对象文件、归档、
汇编和 AVR ELF 保持原样。签名前复制到同目录临时文件并移除旧 `.codesign`，签名到另一个
临时文件，确认新文件包含 `.codesign` 后再替换原输出并恢复模式位。

同目录临时文件使替换保持在同一文件系统中，也避免把部分签名结果暴露给并行 make。

### 3. 明确解释 HMDFS 上的包装脚本

包装器本身是 shell 脚本。HMDFS 可能保留内容但不允许直接执行，因此构建环境中的编译器
命令应是 `bash /path/to/wrapper`，不能依赖 `chmod +x`。这一步属于已有 E087 的应用，
不是本草稿的新增点。

### 4. 以阶段扫描补漏，并保持最终工具为原生 ELF

编译器包装器解决“首次执行前”签名；`all-gcc`、`all-target-libgcc` 和 `package()` 后的
ELF 扫描用于补签非标准链接路径产生的遗漏。扫描同样必须用 ELF 类型分类并验证签名段。

最终 `bin/avr-gcc` 和 `libexec/.../cc1` 应直接是签名后的原生 ELF。不要把 `avr-gcc`
改名为 `avr-gcc.real` 再放一个 shell 启动器，这会改变 GCC 的程序名、相对工具路径和下游
探测边界。

### 5. 消费者测试验证工具链所有权

`test_package` 应直接执行已打包的 `avr-gcc --version`，并验证：

- `-print-libgcc-file-name` 解析到当前 Conan 包内部；
- 能为真实 MCU 链接 AVR ELF；
- `avr-objdump` 确认 `elf32-avr` 和 AVR 架构；
- `avr-nm` 同时看到应用符号及来自包内 `libgcc` 的辅助符号。

这比“命令返回 0”更能证明最终原生驱动、内部 `cc1`、依赖的 avr-binutils 和包内运行库
协同工作。

## 与已有知识的差异

- E077 处理安装后 ELF 被 strip/patchelf 修改而需要重签；本条目处理构建期新 ELF 在首次
  执行前必须完成签名，时间边界不同。
- E087 处理 HMDFS 上 shell 脚本不能直接执行；本条目复用其显式 shell 方式，但新增点是
  编译器链接输出分类和首次执行前签名。
- E311 讨论 Conan source-folder 隔离；`no_copy_source=True` 可降低大型 GCC 源码复制成本，
  但不是本条 B 类候选的主要创新。

## 禁止做法

- 不要只在 `package()` 或 `make install` 后签名。
- 不要按扩展名、文件名或执行位盲签所有编译输出。
- 不要把目标对象、静态库或 AVR ELF 当作 HarmonyOS 宿主 ELF 签名。
- 不要用 shell 包装器替换最终交付的 `avr-gcc` 原生 ELF。
- 不要把 E087 的脚本权限修复重复申报为本条目的新知识。
- 不要在完整真机门禁通过前把草稿写成已验证或正式知识条目。

## 验证状态

- 本地：配方/test_package AST、YAML、Conan inspect/export/source 与补丁应用检查已通过。
- 依赖：`avr-binutils/2.43.1` 独立真机 shadow CI 已通过。
- r1：依赖缓存恢复和 G0 通过；构建在 GCC 直接执行 `move-if-change` 时命中 E087，已形成
  独立补丁，未计为成功。
- r2-r10：逐步定位并修复签名、HMDFS helper、目标工具分发与构建范围问题，均未计为成功。
- r11：run ID `codex-avr-gcc-bootstrap-shadow-ci-r11-2245-20260818-064329-8726`；推进到
  `all-target-libgcc`，约 3660 秒后 rc=1，末尾仍在可选 fixed-point/libf7 组合编译。
- r12：提交 `c2089cc318` 已禁用非引导必需的 fixed-point 支持；因授权真机 SSH 端点
  `10.62.218.131:2222` 不可达而尚未启动。通过标准仍为 L0-L5、GCC selftest、16 个官方
  torture 编译检查和消费者 AVR ELF 链接验证全部通过。

复现入口：

```sh
CI_PACKAGES="archives/a/avr-gcc-bootstrap/14.2.0" zsh ci/conan/build_and_test.sh
```
