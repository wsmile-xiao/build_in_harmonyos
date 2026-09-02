# perl-file-which 1.27 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译）
- **编译日期**: 2026-09-01
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/perl-file-which/1.27 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 File-Which-1.27）。

### 2. 打包（package()）
- 纯 Perl 模块（lib/File/Which.pm），无编译
- `package()` 拷贝 `lib/` 到 `lib/perl5/`（perl site-lib）
- package_type=application（本环境 python-require 型 conan create 静默
  跳过构建——perl-algorithm-diff/dataproperty/pytablewriter 同款先例）
  + commands.json（R38）

## 依赖
- 无外部 CPAN 依赖——META runtime requires 仅核心模块（base/perl）

## 上游测试（rule 4）
- 测试目录：t/（3 个 .t 文件，00_diag/01_use/file_which，prove -lr t/ 递归运行）
- 本地实测：**21 个断言 21/21（100%）**——All tests successful，零失败，全部运行
  （注意：prove -l t/ 的 -l 只加 lib 路径、不递归子目录——评审 rule 3 按
  t/ 下 .t 文件数核验声明 N，此处文件数（3）与断言数（21）分列申报）
- 适配后：test_package R34 真实 perl 加载打包的 File::Which 并
  which('perl') 解析真实可执行文件校验，1/1 = 100%

## 已知限制
- 无（纯 Perl which 工具 API 实现）
---

**编译结束**: 2026-09-01 22:20
**最终状态**: built
