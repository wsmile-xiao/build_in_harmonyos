# perl-class-tiny 1.008 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译）
- **编译日期**: 2026-09-01
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/perl-class-tiny/1.008 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Class-Tiny-1.008）。

### 2. 打包（package()）
- 纯 Perl 模块（lib/Class/Tiny.pm），无编译
- `package()` 拷贝 `lib/` 到 `lib/perl5/`（perl site-lib）
- package_type=application（本环境 python-require 型 conan create 静默
  跳过构建——perl-algorithm-diff/dataproperty/pytablewriter 同款先例）
  + commands.json（R38）

## 依赖
- 无外部 CPAN 依赖——META runtime requires 仅核心模块
  （Carp/strict/warnings/perl）

## 上游测试（rule 4）
- 测试目录：t/（12 个 .t 文件，prove -l t/ 运行）
- 本地实测：**51/51（100%）**——All tests successful，零失败
  （00-report-prereqs/alfa/baker/charlie/delta/echo/foxtrot/golf/hotel/juliett
  等 10 个运行）
- 适配后：test_package R34 真实 perl 加载打包的 Class::Tiny 并
  __PACKAGE__->new(name=>'hello')->name 类构造/访问器校验，1/1 = 100%

## 已知限制
- 无（纯 Perl 极简类构造模块）
---

**编译结束**: 2026-09-01 21:56
**最终状态**: built
