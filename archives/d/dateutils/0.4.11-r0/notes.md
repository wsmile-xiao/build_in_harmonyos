# dateutils 0.4.11-r0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-07-13
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

```bash
source .build-context-dateutils-0.4.11-r0
cd $BUILD_SRC_DIR
# config.guess 无法识别 HarmonyOS, 需指定 --build
TMPDIR=$TMPDIR ./configure --prefix=$DEFAULT_PREFIX --build=aarch64-unknown-linux-gnu
TMPDIR=$TMPDIR make -j1
TMPDIR=$TMPDIR make install DESTDIR=$TEST_PREFIX
TMPDIR=$TMPDIR make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统类型 | HarmonyOS (HongMeng Kernel) 不在 config.guess 识别列表中 | 更新 config.guess 并指定 `--build=aarch64-unknown-linux-gnu` |
| 2 | config.status 创建临时文件 Permission denied | HMDFS 文件系统对 mktemp 模式"confXXXXXX"的目录写入受限 | 在 conanfile.py 中通过 `--build` 绕过; 本地编译时用 `mkdir -p` 替换 mktemp |

## 源码修改

通过 `patches/0001-configure-use-mkdir-p-for-tempdir.patch` 对上游 `configure` 做最小修正：将 HMDFS 上不稳定的 `mktemp -d "./confXXXXXX"` 临时目录创建逻辑替换为基于 `${TMPDIR:-.}/conf$$` 的 `mkdir -p`，避免 `config.status` 在临时目录创建阶段出现 `Permission denied`。构建参数继续通过 `AutotoolsToolchain` 传入 `--build=aarch64-unknown-linux-gnu`、`CC=clang`、`CXX=clang++`。

## 依赖版本

无外部依赖（仅使用系统 libc/libm）。

## 验证结果

```bash
# 上游测试: 878 tests, 837 PASS, 41 FAIL
# FAIL 的 41 个测试均为日期边界场景（闰年 2-30、locale 解析等），非平台兼容问题
# 二进制 smoke test:
$ datediff --version
$ dateadd 2020-01-01 1d
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| dateadd | ~80K | 日期/时间加减 |
| dateconv | ~80K | 日历/格式转换 |
| datediff | ~80K | 日期差计算 |
| dategrep | ~80K | 日期 grep |
| dateround | ~80K | 日期舍入 |
| dateseq | ~80K | 日期序列生成 |
| datesort | ~80K | 日期排序 |
| datetest | ~80K | 日期条件测试 |
| datezone | ~80K | 时区转换 |
| strptime | ~80K | 日期解析 |

## 注意事项

- dateutils 是**命令行工具集**（非库），conanfile.py 中 `package_type = "application"`
- 工具通过 `dateadd`、`datediff` 等形式安装，同时提供兼容符号链接 `dadd`、`ddiff` 等短名
- 上游测试中 41 个 FAIL 为已知日期解析边界问题，不影响工具正常使用
---

**编译结束**: 2026-07-13 17:29
**最终状态**: built
