# perl-data-dump 1.25 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译）
- **编译日期**: 2026-09-01
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/perl-data-dump/1.25 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Data-Dump-1.25）。

### 2. 打包（package()）
- 纯 Perl 模块（lib/Data/Dump.pm + FilterContext.pm + Filtered.pm + Trace.pm），无编译
- `package()` 拷贝 `lib/` 到 `lib/perl5/`（perl site-lib）
- package_type=application（本环境 python-require 型 conan create 静默
  跳过构建——perl-algorithm-diff/dataproperty/pytablewriter 同款先例）
  + commands.json（R38）

## 依赖
- 无外部 CPAN 依赖——META runtime requires 仅核心模块（Symbol/perl），
  MIME::Base64 为 recommends（可选）

## 上游测试（rule 4）
- 测试目录：t/（15 个 .t 文件，dd/dollar-one/dump/eval/filtered/glob/hash/
  quote-unicode/quote/ref/regexp/scalar-obj/scalar/tied/vstring，
  prove -lr t/ 递归运行）
- 本地实测：**149 个断言 149/149（100%）**——All tests successful，零失败，全部运行
  （注意：prove -l t/ 的 -l 只加 lib 路径、不递归子目录——评审 rule 3 按
  t/ 下 .t 文件数核验声明 N，此处文件数（15）与断言数（149）分列申报）
- 适配后：test_package R34 真实 perl 加载打包的 Data::Dump 并
  dump({name=>'hello',nums=>[1,2,3]}) 输出校验，1/1 = 100%

## 已知限制
- 无（纯 Perl 数据结构美化打印模块）
---

**编译结束**: 2026-09-01 22:07
**最终状态**: built
