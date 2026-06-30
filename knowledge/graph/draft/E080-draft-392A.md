# E080: Fortran编译器缺失（gfortran未安装）

## 错误特征

编译过程中出现以下错误：

```
make[1]: gfortran: No such file or directory
make[1]: *** [Makefile:58: caxcpy.o] Error 127
```

或 Makefile/Makeconf 中包含：

```
FC=gfortran
```

源文件为 `.f`、`.f90`、`.f95` 等 Fortran 格式。

## 根因分析

### 平台限制

**OpenHarmony系统未预装Fortran编译器**：
- 系统中没有 gfortran、f77、f90、f95 等任何 Fortran 编译器
- 预编译包仓库（cmd-pkgs）中无 Fortran 编译器预编译包
- 无标准包管理器（apt-get/dnf/yum）可供安装

### 编译器自举问题

Fortran 编译器本身的编译通常需要已有的 Fortran 编译器（无法完全自举），因此无法通过源码编译安装 gfortran。

### 受影响范围

**所有 Fortran 项目**：
- qrupdate（QR/Cholesky分解更新库）
- BLAS/LAPACK（基础线性代数库）
- 其他科学计算库（使用Fortran编写）

## 解决方案

### 方案 1: 交叉编译（推荐）

在其他支持 Fortran 的平台（如 Linux x86_64）上编译，然后移植到 OpenHarmony。

**步骤**：
1. 在 Linux 系统安装 gfortran
2. 使用交叉编译工具链编译 qrupdate
3. 确保目标架构为 aarch64
4. 通过 ELF 名后部署到 OpenHarmony

**限制**：
- 需要确保 ABI 兼容性
- 需确保依赖库（BLAS/LAPACK）在 OpenHarmony 上可用

### 方案 2: 等待官方支持

等待 OpenHarmony 官方提供 Fortran 编译器预编译包。

**时间**：未知（依赖社区支持和优先级）

### 方案 3: 功能替代

如果项目仅需要 QR/Cholesky 分解功能，可考虑：
- LAPACK 本身提供完整的 QR/Cholesky 分解（但部分也是 Fortran）
- Eigen 库（C++）提供类似功能
- 其他纯 C/C++ 实现的科学计算库

## 处理流程

1. **检测错误**：编译失败，错误代码 127（找不到命令）
2. **确认类型**：检查 Makefile/Makeconf 中的 `FC=gfortran` 或 `.f` 源文件
3. **标记状态**：将编译状态设置为 `failed`，记录 `failure_reason: missing_fortran_compiler`
4. **归档记录**：在 notes.md 中详细记录失败原因和建议方案
5. **知识沉淀**：创建知识图谱条目（E080）

## 验证方法

```bash
# 检查 Fortran 编译器是否可用
gfortran --version
which f77 f90 f95

# 检查预编译包仓库是否有 gfortran
python3 $SKILL_ROOT/scripts/ohc-run.py resolve-deps --list-available | grep -i fortran

# 查看源文件类型
ls src/*.f
```

## 归档示例

qrupdate 1.1.2 编译失败：

```
状态: failed
失败阶段: Step 4 (make)
失败原因: 缺少 Fortran 编译器 (gfortran)
影响: 无法编译任何 Fortran 源文件
```

## 建议

### 对编译协作者

- 遇到 Fortran 项目时，立即检查 gfortran 可用性
- 标记为 `failed`，不要尝试绕过（会导致其他问题）
- 在归档中记录详细的失败原因和替代方案

### 对 cmd-pkgs 团队

- 优先提供 gfortran 预编译包（P1 级别）
- 或提供交叉编译工具链和文档
- 评估科学计算库的整体支持策略

## 相关知识条目

- E001-E079：其他编译失败模式
- knowledge/operations/dependencies.md：依赖管理

## 历史

- **首次发现**：qrupdate 1.1.2 编译（2026-05-26）
- **发现者**：392A
- **平台**：OpenHarmony aarch64

---

*Draft by 392A — 2026-05-26*