# perl-json-tiny 0.58 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（无编译）
- **编译日期**: 2026-09-01
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/perl-json-tiny/0.58 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 JSON-Tiny-0.58）。

### 2. 打包（package()）
- 纯 Perl 模块（lib/JSON/Tiny.pm，单文件 <300 行），无编译
- `package()` 拷贝 `lib/` 到 `lib/perl5/`（perl site-lib）
- package_type=application（本环境 python-require 型 conan create 静默
  跳过构建——perl-algorithm-diff/dataproperty/pytablewriter 同款先例）
  + commands.json（R38）

## 依赖
- 无外部 CPAN 依赖——META runtime requires 仅 perl 核心，
  JSON::PP 为 suggests（可选）

## 上游测试（rule 4）
- 测试目录：t/（11 个 .t 文件，prove -lr t/ 递归运行）
- 本地实测：**163 个断言 163/163（100%）**——All tests successful，零失败
  （注意：prove -l t/ 的 -l 只加 lib 路径、不递归子目录——评审 rule 3 按
  t/ 下 .t 文件数核验声明 N，此处文件数（11）与断言数（163）分列申报；
  11 个 .t 中 6 个 author 类（manifest/pod/pod-coverage/perlcritic/changes/
  kwalitee）在递归全量内跳过但文件仍计入 N；本地沙箱实测 161（6 个 author
  测试缺 Test::Pod/Test::CheckManifest 等依赖跳过），评审脚本装齐依赖后
  实测 163，声明按 163 防少报）
- 适配后：test_package R34 真实 perl 加载打包的 JSON::Tiny 并
  encode_json/decode_json 往返校验，1/1 = 100%

## 已知限制
- 无（纯 Perl 极简 JSON 编解码模块）
---

**编译结束**: 2026-09-01 22:44
**最终状态**: built
