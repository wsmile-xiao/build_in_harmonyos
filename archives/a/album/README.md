# album

Themeable HTML photo album generator (pure Perl) — creates thumbnail + HTML
photo albums from directories of images.

- Homepage: https://marginalhacks.com/Hacks/album/
- License: BSD-style (Marginal Hacks license)
- Version: 4.18

## OHOS 适配

- 纯 Perl 脚本，无 C/C++ 编译；`build()` 仅做 `perl -c` 语法校验。
- 运行时依赖：Perl 解释器（`/data/service/hnp/bin/perl`）+ ImageMagick
  `convert`/`identify`（生成缩略图用，为运行时依赖非 Conan 构建依赖）。
- test_package 实质性验证：`album --version` / `--help` 真实调用打包产物；
  相册生成场景在 ImageMagick 缺失时跳过并记录崩溃点原因。

## 使用

```
album [options] <dir>
```
