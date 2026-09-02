# perl-test-simple 1.302224 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译）
- **编译日期**: 2026-09-01
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/perl-test-simple/1.302224 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Test-Simple-1.302224）。

### 2. 打包（package()）
- 纯 Perl 模块（Test-Simple 发行，lib/ 大量 .pm），无编译
- `package()` 拷贝 `lib/` 到 `lib/perl5/`（perl site-lib）
- package_type=application（本环境 python-require 型 conan create 静默
  跳过构建——perl-algorithm-diff/dataproperty/pytablewriter 同款先例）
  + commands.json（R38）

## 依赖
- 无外部 CPAN 依赖——Test-Simple 是 perl 核心双生命周期模块
  （Test::Simple/Test::More/Test2/Test::Builder 等），META runtime
  requires 全部为核心模块

## 上游测试（rule 4）
- 测试目录：t/（374 个 .t 文件，含 t/Test2/、t/Legacy/ 子目录，prove -lr t/ 递归运行）
- 本地实测：**3554 个断言 3554/3554（100%）**——All tests successful，零失败
  （注意：prove -l t/ 的 -l 只加 lib 路径、不递归子目录——曾误用 -l 只跑
  顶层 5 个文件 85 断言被评审 rule 4 少报打回；必须 -lr 递归全量，
  374 个 .t、3554 断言 100% 通过）
- 适配后：test_package R34 真实 perl 加载打包的 Test::Simple 并
  ok(1+1==2) 断言校验，1/1 = 100%

## 已知限制
- 无（纯 Perl 测试工具集）
---

**编译结束**: 2026-09-01 21:30
**最终状态**: built
