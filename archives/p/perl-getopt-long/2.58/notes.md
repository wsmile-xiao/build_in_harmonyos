# perl-getopt-long 2.58 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译）
- **编译日期**: 2026-08-31
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/perl-getopt-long/2.58 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Getopt-Long-2.58）。

### 2. 打包（package()）
- 纯 Perl 模块（lib/Getopt/Long.pm + Parser.pm），无编译
- `package()` 拷贝 `lib/` 到 `lib/perl5/`（perl site-lib）
- package_type=application（本环境 python-require 型 conan create 静默
  跳过构建——perl-algorithm-diff/dataproperty/pytablewriter 同款先例）
  + commands.json（R38）

## 依赖
- 无外部 CPAN 依赖——Getopt::Long 是 perl 核心模块，作为独立 CPAN 发行
  打包供下游引用（perl/Pod::Usage 等核心模块随 perl 提供）

## 上游测试（rule 4）
- 测试目录：t/（8 个 .t 文件，prove -l t/ 运行）
- 本地实测：**109/109（100%）**——All tests successful，零失败，全部运行
  （gol-basic/compat/linkage/load1/load2/oo/xargv/xstring）
- 适配后：test_package R34 真实 perl 加载打包的 Getopt::Long 并
  GetOptions 解析真实命令行参数（-v -f test.txt）校验，1/1 = 100%

## 已知限制
- 无（纯 Perl 命令行参数解析模块）
---

**编译结束**: 2026-08-31 23:38
**最终状态**: built
