# 更新日志 (Changelog)

本项目的所有重要更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

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

| 特性 | v1.x | v2.0.0 |
|------|------|--------|
| 知识库结构 | 单文件 | 模块化 |
| 模板系统 | 无 | 5 个模板 |
| 辅助脚本 | 无 | 4 个脚本 |
| 软件档案 | 基础 | 17 个软件 |
| 文档完善度 | 基础 | 完整 |
| 贡献指南 | 无 | 完整 |

---

## 未来规划

### v2.1.0 (计划中)

- [ ] 新增更多软件档案
- [ ] 完善测试报告模板
- [ ] 添加自动化测试脚本
- [ ] 优化补丁生成工具

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