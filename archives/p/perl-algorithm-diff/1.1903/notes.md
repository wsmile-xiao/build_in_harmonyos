# perl-algorithm-diff 1.1903 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译）
- **编译日期**: 2026-08-31
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/perl-algorithm-diff/1.1903 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Algorithm-Diff-1.1903）。

### 2. 打包（package()）
- 纯 Perl 模块（lib/Algorithm/Diff.pm + DiffOld.pm），无编译
- `package()` 拷贝 `lib/` 到 `lib/perl5/`（perl site-lib）
- package_type=application（本环境 python-require 型 conan create 静默
  跳过构建——dataproperty/pytablewriter 同款先例）+ commands.json（R38）

## 依赖
- META.json runtime requires 为空（无外部 CPAN 依赖）

## 上游测试（rule 4）
- 测试目录：t/（base.t + oo.t，prove -l t/ 运行）
- 本地实测：**1004/1004（100%）**——All tests successful，零失败
- 适配后：test_package R34 真实 perl 加载打包的 Algorithm::Diff 并
  diff 两组数组校验，1/1 = 100%

## 已知限制
- 无（纯 Perl 核心依赖模块）
