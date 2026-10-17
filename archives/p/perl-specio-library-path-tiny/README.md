# perl-specio-library-path-tiny

Path::Tiny types and coercions for Specio (Pure Perl module).

## 软件信息

- **官网**: https://metacpan.org/dist/Specio-Library-Path-Tiny
- **源码**: https://github.com/houseabsolute/Specio-Library-Path-Tiny
- **许可证**: Apache-2.0
- **分类**: perl

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.05 | built | 2026-07-01 | 编译成功，conan-verify 全部通过 |

## 运行依赖

- perl (>=5.010)
- perl-specio (>=0.29)
- Path::Tiny (>=0.087)
- Scalar::Util
- Specio::Declare
- Specio::Library::Builtins
- Specio::PartialDump
- Specio::Exporter

## 编译依赖

- perl (ExtUtils::MakeMaker)

## 使用说明

Specio::Library::Path::Tiny 为 Specio 类型系统提供 Path::Tiny 相关的类型约束和强制转换。
提供以下类型：Path, AbsPath, RealPath, File, AbsFile, RealFile, Dir, AbsDir, RealDir。

### 安装

Conan 安装：`conan install --requires=perl-specio-library-path-tiny/0.05@ohpcd/stable`

安装后 .pm 文件位于 `lib/perl5/site_perl/5.42.0/` 目录。

### ⚠️ 鸿蒙平台注意事项

1. **必须设置 `SPECIO_IMPLEMENTATION=PP`**
   - 依赖 Specio，鸿蒙系统的 Clone 模块不支持 CODE 引用克隆
   - Conan 配方已通过 `runenv_info.define("SPECIO_IMPLEMENTATION", "PP")` 自动设置

2. **必须安装 `Path::Tiny` 模块**
   - 运行时需要 Path::Tiny (>=0.087)，需安装到系统 Perl site_perl 目录

3. **纯 Perl 模块，无需 ELF 签名**

## 测试结果

| 测试类型 | 结果 | 详情 |
|----------|------|------|
| Conan 验证 (G0-G4, L2-L5) | ✅ 全部 PASS | 2026-07-02T16:45:29 |
| 消费者视角测试 | ✅ 44/44 通过 | test_specio_library_path_tiny.pl |
| 功能测试 | ✅ 146/146 通过 | 10 大类场景全覆盖 |
| 上游 t/basic.t | ✅ 47/47 通过 | 9 种类型约束 + 强制转换 + 错误消息 |
| 上游 t/00-report-prereqs.t | ✅ 1/1 通过 | 依赖版本全部满足 |
| Conan 集成测试 | ✅ 通过 | 环境变量传播 + 消费者加载 |
| **合计** | **✅ 238/238 通过** | **全部通过** |

### 功能测试覆盖场景
- 模块加载与环境验证 (SPECIO_IMPLEMENTATION=PP)
- 9 种类型约束创建 (Path/AbsPath/RealPath/File/AbsFile/RealFile/Dir/AbsDir/RealDir)
- 类型验证：接受有效值 + 拒绝无效值 (字符串/整数/undef/hashref/arrayref)
- 强制转换：字符串 → Path::Tiny、数组引用 → Path::Tiny
- 错误消息生成与异常抛出
- 鸿蒙特有场景：HMDFS 路径、系统服务路径、只读 /tmp、深层嵌套、Unicode 文件名、符号链接
- 真实应用：类型约束子程序、路径拼接、目录遍历、文件读写、临时目录
- 内联约束代码生成
- 类型层级关系验证 (扁平结构：所有类型都是 Path 的直接子类型)

---
*OpenHarmony 编译归档 · 2026-07-02*
