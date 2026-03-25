# 更新日志 (Changelog)

本项目的所有重要更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [v2.1.0] - 2026-03-23

### 新增功能

#### 软件档案

新增 **9** 个软件的编译档案：

##### F

- **file 5.45**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：high
  - 补丁：0 个（无）
  - 说明：文件类型识别工具。使用静态链接（`--enable-static --disable-shared LDFLAGS=-static`）解决鸿蒙 SELinux 软链接限制，72 项测试全部通过。

##### H

- **htop 3.4.1**
  - 状态：partial
  - 构建系统：autotools
  - 兼容性：medium
  - 补丁：3 个
    - `0001-config-guess-harmonyos.patch` — config.guess HarmonyOS 平台识别
    - `0002-config-sub-harmonyos.patch` — config.sub 三元组验证
    - `0003-fix-include-path.patch` — 修复 `Panel.h` 头文件包含路径
  - 备注：
    - 普通用户无法运行，SELinux 策略限制 `/proc` 文件系统访问
    - 需要 `sudo` 权限运行
    - 使用静态链接 ncursesw 编译

##### J

- **jq 1.7.1**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：high
  - 补丁：2 个
    - `0001-config-guess-harmonyos-support.patch` — config.guess 平台识别
    - `0002-config-sub-harmonyos-support.patch` — config.sub 三元组支持
  - 测试：5/6 通过（shtest 因 BusyBox `script -e` 不兼容失败，非 jq 问题）

##### L

- **libpipeline 1.5.8**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：high
  - 补丁：2 个
    - `0001-config.guess-add-HarmonyOS-detection.patch` — config.guess 添加 HarmonyOS 检测
    - `0002-config.sub-add-linux-ohos-support.patch` — config.sub 添加 ohos 支持
  - 说明：man-db 的核心依赖库

##### M

- **man-db 2.13.1**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：medium
  - 补丁：5 个
    - `0001-config.sub-add-linux-ohos-support.patch` — config.sub 添加 ohos 支持
    - `0002-security.c-handle-missing-man-owner.patch` — 处理缺失 man 用户
    - `0003-encodings.c-replace-locale-device-with-utf8.patch` — 适配 groff 1.23.0
    - `0004-man.c-replace-locale-roff-device-with-utf8.patch` — 适配 groff 1.23.0
    - `(构建时修改)` config.h 中 `#undef MAN_OWNER` — 彻底禁用权限代码
  - 依赖：gdbm、bzip2、libpipeline、groff（运行时）
  - 说明：man page 显示功能正常（带 ANSI 颜色）。apropos/whatis 因 musl iconv 不支持 `//IGNORE` 后缀而不可用。VPATH 构建策略避免 autotools 重生成。

##### P

- **patch 2.7.6**
  - 状态：partial
  - 构建系统：autotools
  - 兼容性：medium
  - 补丁：1 个
    - `0001-config-guess-harmonyos-support.patch` — config.guess 平台识别
  - 测试：32/44 通过，失败项为环境兼容性问题（umask、软链接限制），核心补丁功能正常。

##### R

- **rsync 3.3.0**
  - 状态：partial
  - 构建系统：autotools
  - 兼容性：medium
  - 补丁：2 个
    - `0001-config-guess-harmonyos.patch` — config.guess 平台识别
    - `0002-config-sub-harmonyos.patch` — config.sub 三元组支持
  - 测试：官方测试套件 44 项全部失败（SELinux 软链接限制），但手动验证基本同步、增量传输、`--delete` 均通过。
  - 说明：核心文件同步功能正常，测试套件因 SELinux 策略无法创建软链接而失败。

##### S

- **strace 6.19**
  - 状态：partial
  - 构建系统：autotools
  - 兼容性：low
  - 补丁：3 个
    - `0001-add-harmonyos-support-to-config.sub.patch` — config.sub 添加 ohos 支持
    - `0002-fix-unused-function-warning-in-sigreturn.patch` — 修复 clang `-Werror` 编译错误
    - `0003-add-harmonyos-support-to-config.guess.patch` — config.guess 添加 HarmonyOS 识别
  - 说明：编译产物正确，但 ptrace 系统调用被 SELinux `adhoc_bin` 域完全禁止，核心追踪功能不可用。需 `--disable-mpers` 禁用多架构支持。

##### W

- **wget 1.19.1**
  - 状态：partial
  - 构建系统：autotools
  - 兼容性：medium
  - 补丁：2 个
    - `0001-config-guess-harmonyos.patch` — config.guess 平台识别
    - `0002-config-sub-harmonyos.patch` — config.sub 三元组支持
  - 测试：34/39 通过（87%），失败项为 HTTPS 证书固定测试。
  - 依赖：openssl、zlib、pkg-config
  - 说明：已替换系统 toybox wget，功能更完整。HTTPS 下载需配合 `--no-check-certificate` 使用（缺少系统 CA 证书）。

#### 知识文档

新增 **8** 篇知识文档（总计 19 篇）：

- `knowledge/filesystem-analysis.md` — 鸿蒙文件系统架构与差异分析
  - 实机探索 `/proc/mounts` 全量分析
  - tmpfs/proc/sysfs/devpts 挂载差异
  - SELinux 上下文与标签系统

- `knowledge/filesystem-impact-assessment.md` — 文件系统差异用户场景影响评估
  - 用户画像 × 差异维度 × 场景走查
  - 影响评估矩阵

- `knowledge/musl-glibc-developer-impact.md` — musl 与 glibc 差异对开发者的全面影响分析
  - 从 glibc/Linux 迁移到 OpenHarmony musl 的完整指导

- `knowledge/musl-glibc-full-comparison-gnu-linux.md` — musl vs glibc GNU 扩展 + Linux 特有接口全量对比表
  - GNU 特有函数、Linux syscalls 差异详表

- `knowledge/musl-glibc-full-comparison-iso-posix.md` — musl vs glibc ISO C + POSIX 全量接口对比表
  - 标准 C / POSIX 接口兼容性逐项对比

- `knowledge/packaging.md` — HarmonyOS 可移植打包指南
  - RPATH 处理、ELF 签名、软链接限制应对

- `knowledge/ptrace-alternatives.md` — 鸿蒙系统 ptrace 限制及替代方案
  - SELinux adhoc_bin 域分析
  - strace/gdb 替代调试策略

- `knowledge/sudo-analysis.md` — 鸿蒙 sudo 深度分析报告
  - 目标分析法（角色→场景→功能需求→鸿蒙覆盖）
  - sudo 能力与限制

### 改进优化

#### 错误模式库扩展

- `knowledge/error-patterns.md` 从 26 个错误模式扩展到 **44** 个（E001–E044）
  - 新增模式覆盖：扩展模块 RPATH、HiShell 兼容性、可移植包 PYTHONHOME 等场景

#### Python 3.9.0 增强报告

- 新增 **4** 份深度分析报告：
  - `UPSTREAM_ADAPTATION_ANALYSIS.md` — 上游适配分析报告
  - `PATCH_DETAIL_ANALYSIS.md` — 移植补丁详细分析报告
  - `MISSING_ADAPTATION_SCAN.md` — 适配遗漏扫描报告
  - `HARMONYOS_SUBPROCESS_GUIDE.md` — HarmonyOS 子进程执行完整指南（v2.0）
- 补丁从 10 个增加到 **11** 个
  - 新增 `0011-Lib-venv-HarmonyOS-symlink-fix.patch` — venv 软链接修复

#### gen_summary.py 双 Schema 兼容性

- `scripts/gen_summary.py` 增加 manifest.yaml 双 schema 兼容性支持
  - Schema A：`patches_applied` / `dependencies` / `compatibility` 字段
  - Schema B：`build.patches` / `build.dependencies` / `issues` 字段
  - 自动检测并适配两种格式，确保所有软件档案可被正确索引

#### 元数据修复

- 修复多个 manifest.yaml 元数据腐化问题：
  - `sed` 档案 manifest 内容被 sed 命令损坏（文件内容意外替换）
  - `rsync` 档案 manifest 中部分字段名不合规
  - `patch` 档案 manifest 声明 2 个补丁但实际仅有 1 个补丁文件

### 统计信息

- **知识文件**: 19 个（+8）
- **软件档案**: 26 个软件，27 个版本（+9）
- **编译状态**:
  - 成功 (success): 18 个（+3）
  - 部分成功 (partial): 8 个（+6）
  - 失败 (failed): 0 个
- **构建系统分布**:
  - autotools: 23 个（+8）
  - cmake: 1 个
  - makefile: 1 个
  - custom-perl: 1 个
  - script: 1 个（+1，help2man 归类调整）

### 升级指南

如果您从 v2.0.0 升级到 v2.1.0：

1. **新增软件档案**: 9 个新软件编译档案可用（file、htop、jq、libpipeline、man-db、patch、rsync、strace、wget）
2. **知识文档扩展**: 8 篇新知识文档，覆盖文件系统、musl/glibc 对比、ptrace 替代方案、sudo 分析等主题
3. **错误模式库**: 从 26 个扩展到 44 个，覆盖更多 HarmonyOS 特有问题
4. **Python 3.9.0**: 新增 1 个补丁（venv 软链接修复）和 4 份分析报告
5. **gen_summary.py**: 已支持双 schema 兼容，可正确处理所有 manifest 格式

---

## [v2.0.0] - 2024-03-22

### 重大变更

#### 知识库模块化重构

将原有的单一 SKILL.md 知识库拆分为多个专题知识文件，提高检索效率和可维护性。

**新增知识文件：**

- `knowledge/build-systems.md` - 构建系统知识
  - autotools 构建系统详解
  - CMake 构建系统适配
  - Meson 构建系统说明
  - 自定义构建系统处理

- `knowledge/environment.md` - HarmonyOS 环境特性
  - 系统环境变量
  - 编译器配置
  - 工具链路径

- `knowledge/troubleshooting.md` - 问题排查指南
  - 常见编译错误
  - 依赖问题解决
  - 配置错误处理

- `knowledge/error-patterns.md` - 错误模式库
  - 链接错误模式
  - 配置错误模式
  - 运行时错误模式

- `knowledge/musl-compat.md` - musl 兼容性
  - musl 与 glibc 差异
  - 常见兼容性问题
  - 解决方案集合

- `knowledge/best-practices.md` - 最佳实践
  - 编译优化建议
  - 依赖管理策略
  - 测试验证方法

- `knowledge/FAQ.md` - 常见问题解答
  - 快速问题定位
  - 常用解决方案

- `knowledge/harmonyos-specifics.md` - HarmonyOS 特性说明
  - 平台识别
  - 系统调用差异
  - SELinux 域转换

- `knowledge/dependencies.md` - 依赖关系图谱
  - 软件依赖关系
  - 编译顺序建议

- `knowledge/python-extensions.md` - Python 扩展模块
  - 扩展模块编译
  - 常见问题处理

- `knowledge/autotools-patterns.md` - autotools 模式库
  - 常见 autotools 问题
  - 通用修复模式

### 新增功能

#### 模板系统

在 `templates/` 目录下新增标准化模板：

- `templates/manifest.yaml` - 软件档案元数据模板
  - 完整的字段说明
  - 必填字段标记
  - 示例配置

- `templates/README.md` - 编译说明文档模板
  - 标准化结构
  - 必要信息清单

- `templates/build-report.md` - 编译报告模板
  - 编译过程记录格式
  - 问题记录模板

- `templates/test-report.md` - 测试报告模板
  - 测试结果格式
  - 兼容性评估模板

- `templates/compatibility.md` - 兼容性评估模板
  - 兼容性等级定义
  - 评估标准

#### 辅助脚本

在 `scripts/` 目录下新增实用脚本：

- `scripts/detect-build-system.sh` - 构建系统自动检测
  - 支持 autotools、CMake、Meson 等多种构建系统
  - 提供配置建议

- `scripts/create-archive.sh` - 档案创建脚本
  - 自动创建标准目录结构
  - 从模板生成配置文件

- `scripts/validate-patch.sh` - 补丁验证脚本
  - 验证补丁格式
  - 测试补丁应用

- `scripts/generate_manifests.py` - 批量生成 manifest
  - 从源码提取版本信息
  - 自动生成基础配置

### 软件档案

新增 **17** 个软件的编译档案：

#### A

- **automake 1.16.5**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：high

#### B

- **bash 5.3**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：high

- **bzip2 1.0.8**
  - 状态：success
  - 构建系统：makefile
  - 兼容性：high

#### C

- **coreutils 9.10**
  - 状态：partial
  - 构建系统：autotools
  - 兼容性：medium
  - 备注：部分工具需要特殊处理

#### G

- **gawk 5.3.0**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：high

- **gdbm 1.23**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：high

#### H

- **help2man 1.49.3**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：high

#### L

- **libffi 3.4.4 / 3.5.2**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：high
  - 版本：2 个版本

- **libtool 2.4.7**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：high

- **lzma 5.6.2**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：high

#### N

- **ncurses 6.4**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：high

#### O

- **openssl 1.1.1w**
  - 状态：success
  - 构建系统：custom-perl
  - 兼容性：high
  - 补丁：1 个

#### P

- **python 3.9.0**
  - 状态：partial
  - 构建系统：autotools
  - 兼容性：medium
  - 补丁：10 个
  - 备注：
    - 60 个扩展模块中约 40 个可用
    - subprocess 需要使用管道语法
    - PTY 功能不可用

#### R

- **readline 8.2**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：high

#### S

- **sed 4.9**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：high

#### T

- **tar 1.35**
  - 状态：success
  - 构建系统：autotools
  - 兼容性：high

#### Z

- **zlib 1.3.1**
  - 状态：success
  - 构建系统：cmake
  - 兼容性：high

### 改进优化

#### 文档改进

- 新增 `CONTRIBUTING.md` 贡献指南
  - 详细的添加软件档案流程
  - 补丁命名规范
  - manifest.yaml 必填字段说明
  - 测试报告要求
  - PR 提交流程

- 优化 SKILL.md 文档结构
  - 简化主文档内容
  - 引用外部知识文件
  - 提高可读性

#### 档案结构优化

- 规范化目录结构
- 清理 patches 目录异常嵌套（移除 patches/ 下的 logs/reports/scripts 子目录）
- 统一文件命名规范

#### 索引优化

- 新增 `archives/_index.yaml` 软件索引文件
  - 快速检索软件信息
  - 版本列表维护
  - 状态统计

### 统计信息

- **知识文件**: 11 个
- **模板文件**: 5 个
- **辅助脚本**: 4 个
- **软件档案**: 17 个软件，19 个版本
- **编译状态**:
  - 成功 (success): 15 个
  - 部分成功 (partial): 2 个
  - 失败 (failed): 0 个
- **构建系统分布**:
  - autotools: 15 个
  - cmake: 1 个
  - makefile: 1 个
  - custom-perl: 1 个

### 升级指南

如果您从 v1.x 升级到 v2.0.0：

1. **知识库结构变化**: 原有 SKILL.md 中的知识已拆分到 `knowledge/` 目录
2. **模板位置**: 新增的模板文件位于 `templates/` 目录
3. **辅助工具**: 新增脚本位于 `scripts/` 目录
4. **索引文件**: 检查 `archives/_index.yaml` 是否需要更新

---

## 版本历史

### 版本对比

| 特性 | v1.x | v2.0.0 | v2.1.0 |
|------|------|--------|--------|
| 知识库结构 | 单文件 | 模块化（11 篇） | 模块化（19 篇） |
| 模板系统 | 无 | 5 个模板 | 5 个模板 |
| 辅助脚本 | 无 | 4 个脚本 | 4 个脚本 |
| 软件档案 | 基础 | 17 个软件 | 26 个软件 |
| 错误模式 | — | 26 个 | 44 个 |
| 文档完善度 | 基础 | 完整 | 全面 |
| 贡献指南 | 无 | 完整 | 完整 |

---

## 未来规划

### v2.2.0 (计划中)

- [ ] 支持更多构建系统（如 QMake）
- [ ] 新增依赖关系可视化
- [ ] 完善兼容性评估体系

---

## 贡献者

感谢所有为项目做出贡献的开发者！

---

## 许可证

本项目遵循 MIT 许可证。详见 [LICENSE](LICENSE) 文件。