# perl-exporter 5.79 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译）
- **编译日期**: 2026-08-31
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/perl-exporter/5.79 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Exporter-5.79）。

### 2. 打包（package()）
- 纯 Perl 模块（lib/Exporter.pm + Heavy.pm），无编译
- `package()` 拷贝 `lib/` 到 `lib/perl5/`（perl site-lib）
- package_type=application（本环境 python-require 型 conan create 静默
  跳过构建——perl-algorithm-diff/dataproperty/pytablewriter 同款先例）
  + commands.json（R38）

## 依赖
- 无外部 CPAN 依赖——Exporter 是 perl 核心模块，独立打包供下游引用；
  META runtime requires 仅 Carp（核心模块），Test::Pod 为 recommends（可选）

## 上游测试（rule 4）
- 测试目录：t/（4 个 .t 文件，prove -l t/ 运行）
- 本地实测：**37/37（100%）**——All tests successful，零失败
  - 3 个 .t 运行全通过：Exporter/use/warn
  - 1 个 pod 测试跳过：需 Test::Pod 1.18（非安装必需）
- 适配后：test_package R34 真实 perl 加载打包的 Exporter 并定义
  继承包 + import 符号（greet）校验，1/1 = 100%

## 已知限制
- 无（纯 Perl 核心符号导出模块）
---

**编译结束**: 2026-08-31 23:51
**最终状态**: built
