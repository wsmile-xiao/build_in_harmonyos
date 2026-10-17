# perl-path-class 0.37 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译）
- **编译日期**: 2026-08-31
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/perl-path-class/0.37 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Path-Class-0.37）。

### 2. 打包（package()）
- 纯 Perl 模块（lib/Path/Class.pm + Dir.pm + Entity.pm + File.pm），无编译
- `package()` 拷贝 `lib/` 到 `lib/perl5/`（perl site-lib）
- package_type=application（本环境 python-require 型 conan create 静默
  跳过构建——perl-algorithm-diff/dataproperty/pytablewriter 同款先例）
  + commands.json（R38）

## 依赖
- 无外部 CPAN 依赖——META runtime requires 全部为核心模块
  （Carp/Cwd/Exporter/File::Copy/File::Path/File::Spec/File::Temp/File::stat/
  IO::Dir/IO::File/Perl::OSType/Scalar::Util/overload/parent/strict/warnings）

## 上游测试（rule 4）
- 测试目录：t/（8 个 .t 文件，prove -l t/ 运行）
- 本地实测：**248/248（100%）**——All tests successful，零失败
  - 7 个 .t 运行全通过：01-basic/02-foreign/03-filesystem/04-subclass/
    05-traverse/06-traverse_filt/07-recurseprune
  - 1 个 author 测试跳过：author-critic（仅供作者）
- 适配后：test_package R34 真实 perl 加载打包的 Path::Class 并
  file->parent->stringify 路径操作校验，1/1 = 100%

## 已知限制
- 无（纯 Perl 核心路径操作模块）
---

**编译结束**: 2026-08-31 23:27
**最终状态**: built
