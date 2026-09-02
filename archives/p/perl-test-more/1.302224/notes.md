# perl-test-more 1.302224 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译）
- **编译日期**: 2026-09-01
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/perl-test-more/1.302224 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Test-Simple-1.302224）。

### 2. 打包（package()）
- 纯 Perl 模块（Test::More，与 perl-test-simple 同源 Test-Simple 发行），无编译
- `package()` 拷贝 `lib/` 到 `lib/perl5/`（perl site-lib）
- package_type=application（本环境 python-require 型 conan create 静默
  跳过构建——perl-algorithm-diff/dataproperty/pytablewriter 同款先例）
  + commands.json（R38）

## 同源说明
- Test::More 1.302224 与 Test::Simple 1.302224 同源——均由 CPAN 发行
  Test-Simple-1.302224.tar.gz 提供（无独立 Test-More-1.302224 发行，
  已实测 metacpan 404）。本包按 perl-test-more 名适配，打包 Test::More
  供下游 requires 引用。

## 依赖
- 无外部 CPAN 依赖——Test::More 是 perl 核心双生命周期模块，META runtime
  requires 全部为核心模块

## 上游测试（rule 4）
- 测试目录：t/（5 个 .t 文件，prove -l t/ 运行，同源 Test-Simple 发行）
- 本地实测：**85/85（100%）**——All tests successful，零失败，全部运行
  （00-report/00compile/HashBase/load_manual/zzz-check-breaks）
- 适配后：test_package R34 真实 perl 加载打包的 Test::More 并
  is(2+2,4) 断言校验，1/1 = 100%

## 已知限制
- 无（纯 Perl 测试框架）
---

**编译结束**: 2026-09-01 21:46
**最终状态**: built
