# perl-test-harness 3.52 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译）
- **编译日期**: 2026-08-31
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/perl-test-harness/3.52 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Test-Harness-3.52）。

### 2. 打包（package()）
- 纯 Perl 测试驱动框架，无编译
- `package()` 拷贝 `lib/`（TAP::Harness/TAP::Parser/App::Prove 等）
  到 `lib/perl5/`，并把 `bin/prove` 拷到 `bin/`
- package_type=application（本环境 python-require 型 conan create 静默
  跳过构建——dataproperty/pytablewriter 同款先例）+ commands.json（R38）

## 依赖
- META.json runtime requires 为空（仅依赖 Perl 核心模块）

## 上游测试（rule 4）
- 测试目录：t/（47 个 .t 测试文件，prove -l t/ 运行）
- 本地实测：**12017/12017（100%）**——All tests successful，零失败
- 注：沙箱工作目录含空格会导致 source_handler.t 的子进程测试假失败
  （非库缺陷，2 个用例），在无空格目录实测全过（两轮修复确认）
- 适配后：test_package R34 真实 perl 加载打包的 TAP::Harness 并运行
  bin/prove，1/1 = 100%

## 已知限制
- 无（纯 Perl 核心依赖模块）
