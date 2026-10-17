# kgb 1.0b5 适配笔记

## 编译环境
- 构建系统: makefile（手写 Makefile，无 configure）
- 编译日期: 2026-09-23
- 编译器: clang++ 15（OHOS SDK 26.0.0.18）
- 状态: built

## 编译步骤

1. 从官方 codeload 取 tag `1.0b5` 的源码包（`kgb-1.0b5.tar.gz`）。
2. 显式传入 `CXXFLAGS` 后运行 `make CXX=<ohos clang++> CXXFLAGS=<完整编译参数> LDFLAGS="" -j1`，产出 `kgb`。参数保留 CI 的 `-fPIC -O2`，并补回上游要求的 `-Wall -std=c++0x -O3 -DPROGNAME='"KGB_arch"'`。
3. `package()` 安装 `bin/kgb`、`licenses/LICENSE`、`share/doc/kgb/README.md`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认 `LDFLAGS = -s` | 上游让链接器直接 strip，OHOS 工具链应统一处理 strip | 命令行传 `LDFLAGS=""` 覆盖 |
| 2 | CI 注入的 `CXXFLAGS` 覆盖上游默认参数 | Makefile 用 `CXXFLAGS ?=`；CI 已设置 `-fPIC -O2`，因此默认参数不会生效 | 配方显式传完整 `CXXFLAGS`，保留 CI 参数并补回 `-Wall -std=c++0x -O3` 与 `PROGNAME` 定义 |
| 3 | 归档格式兼容 | 归档头写入 `PROGNAME`（`KGB_arch`） | 显式定义 `PROGNAME='"KGB_arch"'`，并保持 `MAGIC=KGB_arch` 不变 |

## 依赖版本

无三方依赖。

## 验证结果

```bash
# 上游测试：无（N=0）
# 消费者（test_package/test_kgb.sh）
KGB_CHECK_SUMMARY checks=9 fails=0
# 其中包含与 Debian 自带测试一致的确定性校验：
#   gpl.kgb md5 = 86369edb8ca943089b5691f1e4ddfd81
```

## 注意事项

- KGB 为高内存/高 CPU 的 PAQ6 压缩器；消费者测试用 `-0`（2 MB）压缩小文件，另用默认级别压缩随包 `LICENSE`（18 KB）以复现 Debian 的确定性校验，避免长时间/大内存占用。
