# perl-text-csv 2.06 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译，PP 后端）
- **编译日期**: 2026-08-31
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/perl-text-csv/2.06 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Text-CSV-2.06）。

### 2. 打包（package()）
- 纯 Perl 模块（lib/Text/CSV.pm + lib/Text/CSV_PP.pm），无编译
- `package()` 拷贝 `lib/` 到 `lib/perl5/`（perl site-lib）
- package_type=application（本环境 python-require 型 conan create 静默
  跳过构建——perl-algorithm-diff/dataproperty/pytablewriter 同款先例）
  + commands.json（R38）

## 后端选择（关键）
- Text::CSV 默认加载 Text::CSV_XS（XS 编译），不可用时回退捆绑的纯 Perl
  Text::CSV_PP——本配方不编译 XS，运行时 `PERL_TEXT_CSV=0` 强制 PP 后端，
  规避 XS .so 在 hmmac 下的 dlopen 加载限制（E212 类问题）。
- META runtime requires 仅核心模块（IO::Handle/Test::Harness/Test::More/perl），
  Text::CSV_XS 是 recommends（可选，未安装即回退 PP）。

## 上游测试（rule 4）
- 测试目录：t/（41 个 .t 文件，prove -l t/ + PERL_TEXT_CSV=0 运行）
- 本地实测：**52723/52723（100%）**——All tests successful，零失败
  - 40 个 .t 运行全通过
  - 1 个跳过：00_pod（需 Test::Pod 1.00，非安装必需）
- 适配后：test_package R34 真实 perl 加载打包的 Text::CSV（PP 后端）
  并 parse CSV 字符串校验 3 字段，1/1 = 100%

## 已知限制
- 无（纯 Perl CSV 处理模块，PP 后端）
---

**编译结束**: 2026-08-31 23:02
**最终状态**: built
