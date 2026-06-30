# dex 1.0 — OpenHarmony 编译归档

## 软件信息

| 字段 | 值 |
|------|-----|
| 名称 | dex |
| 版本 | 1.0 |
| 描述 | Dextrous text editor — 小巧易用、支持 ctags 的终端文本编辑器 |
| 许可证 | MIT |
| 主页 | https://github.com/tihirvon/dex |
| 构建系统 | Makefile (纯 Makefile，非 autotools) |
| 编译器 | clang 15 |
| 目标架构 | aarch64 (armv8) |
| 编译状态 | built |

## 源码

- **下载地址**: https://github.com/tihirvon/dex/archive/refs/tags/v1.0.tar.gz
- **SHA256**: `4468b53debe8da6391186dccb78288a8a77798cb4c0a00fab9a7cdc711cd2123`

## 依赖

| 依赖 | 来源 | 说明 |
|------|------|------|
| ncurses | 系统预装静态库 | libncursesw.a，位于 /storage/Users/currentUser/usr/local/lib/ |
| libc | 系统库 | 动态链接 |

无 Conan @ohpcd/stable 依赖（ncurses 为系统级预装库）。

## 构建命令

```bash
export CPATH=/storage/Users/currentUser/usr/local/include
export LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib
make prefix=/usr/local CC=clang HOST_CC=clang -j2
make install prefix=/usr/local DESTDIR=$TEST_PREFIX CC=clang HOST_CC=clang
make test CC=clang HOST_CC=clang
```

## 产物

| 路径 | 说明 |
|------|------|
| bin/dex | 主可执行文件 (867K, ELF 64-bit arm64) |
| share/dex/binding/default | 按键绑定配置 |
| share/dex/color/* | 颜色方案 (darkgray, light, light256) |
| share/dex/compiler/* | 编译器集成配置 (gcc, go) |
| share/dex/syntax/* | 语法高亮定义 (20+ 种语言) |
| share/man/man1/dex.1 | man 手册页 |

## Conan 配方

- **引用**: `dex/1.0@ohpcd/stable`
- **Profile**: ohos-aarch64
- **静态链接 (R26)**: BUILD_SHARED_LIBS=OFF，ncurses 使用 .a 静态库
- **test_package**: 验证 bin/dex 存在且为有效 ELF 文件

## 验证结果

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 | PASS | 预构建风险评估通过 |
| G1 | PASS | 配方完整性检查通过 |
| G2 | PASS | conan create 干净构建成功 |
| G3 | PASS | 静态链接验证通过 |
| G4 | PASS | 产物完整性检查通过 |
| L2 | FAIL | dex 是终端全屏编辑器，需 TTY，--version/--help 不支持 |
| L4 | PASS | 安全扫描通过 (PIE=enabled, RELRO=full) |
| L5 | PASS | 产物基线对比通过 |

## 注意事项

- dex 是终端全屏文本编辑器，L2 smoke test 因需 TTY 而失败，属预期行为
- 构建系统为纯 Makefile（conan-init 误检测为 autotools，已手动修正）
- 需创建 libcurses.a → libncursesw.a 符号链接
- PKGDATADIR 在编译时通过 -D 标志固化到二进制中
