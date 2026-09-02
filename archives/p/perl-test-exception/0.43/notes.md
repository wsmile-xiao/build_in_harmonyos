# perl-test-exception 0.43 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译）
- **编译日期**: 2026-09-01
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/perl-test-exception/0.43 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Test-Exception-0.43）。

### 2. 打包（package()）
- 纯 Perl 模块（lib/Test/Exception.pm），无编译
- `package()` 拷贝 `lib/` 到 `lib/perl5/`（perl site-lib）
- package_type=application（本环境 python-require 型 conan create 静默
  跳过构建——perl-algorithm-diff/dataproperty/pytablewriter 同款先例）
  + commands.json（R38）

## 依赖
- **perl-sub-uplevel/0.2800**（Sub::Uplevel >= 0.18，ohpcd + main 已发布）
- 其余为核心模块（Carp/Exporter/Test::Builder/Test::Builder::Tester/
  Test::Harness），随 perl 提供

## 上游测试（rule 4）
- 测试目录：t/（11 个 .t 文件，prove -l t/ 运行）
- 本地实测：**53/53（100%）**——All tests successful，零失败
  - 10 个 .t 运行全通过：Exception/caller/import/isa/lives_and/preserve/
    return/rt/stacktrace/throws_ok
  - 1 个跳过：edge-cases（上游未修复 RT#24678）
- 适配后：test_package R34 真实 perl 加载打包的 Test::Exception 并
  dies_ok 真实异常测试校验，1/1 = 100%

## 已知限制
- 无（纯 Perl 异常测试模块）
---

**编译结束**: 2026-09-01 00:33
**最终状态**: built
