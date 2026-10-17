# MyThes

MyThes 是一个使用结构化文本数据（.idx 索引 + .dat 数据）的简单同义词库，
被 LibreOffice 与 Hunspell 用于同义词查询（MyThes::Lookup）。

## OHOS 适配

- **构建系统**: Autotools（configure + make，libtool）。
- **依赖**: hunspell（configure 的 PKG_CHECK_MODULES 强制要求；
  库本体 mythes.cxx 不含 hunspell，仅示例程序 example.cxx 用其做 stemming）。
- **编译选项**: `--disable-werror`（上游默认 -Werror 在 clang 15 下误杀）；
  `make -j1`（OHOS 沙箱无 mkfifo jobserver）。
- **上游测试**: `make check` 仅构建 `check_PROGRAMS = example`，无 TESTS，
  零自动化断言；实质验证由 test_package 自研最小词库承担。
- **HMDFS**: package() 内把 `.so` 别名链替换为真实文件副本并删除 `.la`。

## 依赖

- hunspell 1.7.3

## 功能验证

```bash
pkg-config --modversion mythes
```

## 参考

- 官网: https://hunspell.github.io
- 源码: https://github.com/hunspell/mythes
