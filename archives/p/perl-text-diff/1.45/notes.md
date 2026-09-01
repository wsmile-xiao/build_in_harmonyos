# perl-text-diff 1.45 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译）
- **编译日期**: 2026-08-31
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/perl-text-diff/1.45 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Text-Diff-1.45）。

### 2. 打包（package()）
- 纯 Perl 模块（lib/Text/Diff.pm + Config.pm + Table.pm），无编译
- `package()` 拷贝 `lib/` 到 `lib/perl5/`（perl site-lib）
- package_type=application（本环境 python-require 型 conan create 静默
  跳过构建——perl-algorithm-diff/dataproperty/pytablewriter 同款先例）
  + commands.json（R38）

## 依赖
- **perl-algorithm-diff/1.1903**（Algorithm::Diff >= 1.19，ohpcd + main 已发布）
- Exporter（perl 核心模块，随 perl 提供）
- 编译验证：`conan install --requires=perl-algorithm-diff/1.1903` 安装
  依赖后注入 PERL5LIB=<pkg>/lib/perl5 跑通上游测试

## 上游测试（rule 4）
- 测试目录：t/（9 个 .t 文件，prove -l t/ 运行）
- 本地实测：**33/33（100%）**——All tests successful，零失败
  - 6 个运行：ext_format/general/inputs/keygen/outputs/table
  - 3 个 author 测试跳过：97_meta/98_pod/99_pmv（非安装必需）
- 适配后：test_package R34 真实 perl 加载打包的 Text::Diff 并
  diff 两组文本校验，1/1 = 100%

## 已知限制
- 无（纯 Perl 核心差异计算模块）
---

**编译结束**: 2026-08-31 22:26
**最终状态**: built
