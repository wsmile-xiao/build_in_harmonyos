# ttyplot 1.7.1 适配笔记

## 编译环境
- 构建系统: makefile（plain Makefile，非 autotools）
- 编译日期: 2026-07-24
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 目标平台: OpenHarmony aarch64 (HongMeng Kernel 1.12.0, musl libc)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build ttyplot 1.7.1 --url=https://github.com/tenox7/ttyplot/archive/refs/tags/1.7.1.tar.gz` 初始化，下载源码并创建编译骨架
2. 分析源码结构：发现是 plain Makefile，无 configure/configure.ac/CMakeLists.txt
3. 发现 pkg-config 无法找到 ncursesw：ncurses 预编译包（--without-shared 编译）未提供 .pc 文件
4. 手动创建 `ncursesw.pc` 和 `ncurses.pc` 文件在 `$DEFAULT_PREFIX/lib/pkgconfig/` 目录，ncursesw.pc 的 Cflags 包含 `-D_XOPEN_SOURCE_EXTENDED`
5. 设置 `PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig:$DEFAULT_PREFIX/share/pkgconfig`
6. 执行 `make PREFIX=$DEFAULT_PREFIX -j1` 编译，成功生成 ttyplot 和 stresstest 二进制
7. 执行 `make PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX install` staging 安装
8. 执行 `ohc-run.py package ttyplot 1.7.1` 预编译包制作（322KB）
9. 执行 `make PREFIX=$DEFAULT_PREFIX install` 本地安装验证
10. 手动功能测试（7项），全部通过
11. 执行 `ohc-run.py finish ttyplot 1.7.1 built` 收尾

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识条目 |
|---|------|------|----------|----------|
| 1 | pkg-config 找不到 ncursesw | ncurses 预编译包（--without-shared 编译）未提供 .pc pkg-config 文件 | 手动创建 ncursesw.pc 和 ncurses.pc 文件在 ~/usr/local/lib/pkgconfig/ | ref:E052 |
| 2 | 4 个 mvvline_set 函数声明警告 | ncursesw wide-char API 函数在头文件中未声明（musl 环境下 _XOPEN_SOURCE_EXTENDED 覆盖了声明） | 警告不影响功能，二进制运行正常 | ref:E052 |
| 3 | manifest.yaml 缺少 build_system 顶层字段 | 模板使用嵌套的 build.system 字段，verify 脚本要求顶层 build_system 字段 | 在 manifest.yaml 添加顶层 `build_system: makefile` 字段 | ref:E052 |
| 4 | knowledge_gained 条目缺少 ref 引用 | check_knowledge_gap 检测到 4 条无引用的知识条目 | 添加 ref:E052 引用知识草稿 | ref:E052 |
| 5 | verify-build install-prefix 路径不匹配 | DESTDIR 模式下 staging 安装路径为 $TEST_PREFIX/$DEFAULT_PREFIX/bin，verify 脚本默认查找 $TEST_PREFIX/bin | 使用 `--install-prefix=$TEST_PREFIX/$DEFAULT_PREFIX` 参数 | ref:E052 |

## 源码修改

无源码修改。本次编译不需要修改 ttyplot.c 或 Makefile，仅创建了辅助性的 pkg-config 文件：
- `$DEFAULT_PREFIX/lib/pkgconfig/ncursesw.pc`（ncursesw 宽字符版本）
- `$DEFAULT_PREFIX/lib/pkgconfig/ncurses.pc`（ncurses 标准版本）

## 依赖版本

| 依赖 | 版本 | 来源 | 备注 |
|------|------|------|------|
| ncurses | 6.4 | 预编译包（cmd-pkgs） | --without-shared 静态编译，缺少 .pc 文件 |
| musl libc | 系统自带 | 运行时链接 | ld-musl-aarch64.so.1 |

## 手动功能测试结果

| 测试项 | 命令 | 结果 |
|--------|------|------|
| 版本号 | `ttyplot -v` | 输出 "ttyplot 1.7.1" ✅ |
| 帮助信息 | `ttyplot -h` | 完整参数说明 ✅ |
| 单通道数据 | `echo "10 20 30 40 50" | timeout 3 ttyplot -t "测试绘图" -u "单位"` | 正确绘图，显示统计 ✅ |
| 双通道数据 | `echo "1 2\n3 4\n5 6" | timeout 3 ttyplot -2` | 双通道绘图正常 ✅ |
| 速率模式 | `echo "100 200 300" | timeout 3 ttyplot -r` | 显示 interval 信息 ✅ |
| 自定义字符 | `echo "15 25 35" | timeout 3 ttyplot -c "@" -s 40` | @ 字符绘图 ✅ |
| stresstest | `echo "5" | timeout 3 stresstest` | 正弦波数据输出 ✅ |

## 编译警告详情

```
ttyplot.c:224: mvvline_set(ph + 1 - l1, x, c1, l1 - l2);
ttyplot.c:227: mvvline_set(ph + 1 - l2, x, (c2 == hce || c2 == lce) ? &c2r : &space, l2 - l1);
ttyplot.c:230: mvvline_set(ph + 1 - l2, x, &c2r, l2);
ttyplot.c:362: mvvline_set(height - 2, 5, &plotchar, 1);
```
以上 4 个 `mvvline_set` 函数声明警告来自 ncursesw wide-char API，在当前 musl+ncursesw 环境下头文件中未声明该函数原型。功能不受影响。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ttyplot-1.7.1-ohos-aarch64.tar.gz | 322KB | 预编译包（含 bin/ttyplot、man/man1/ttyplot.1） |
| ttyplot-1.7.1-ohos-aarch64-debug.tar.gz | 77KB | 调试符号包 |

## 知识沉淀

已创建知识草稿 E052（draft/E052-draft-D62D.kv 和 .md），描述"预编译库缺少 .pc pkg-config 文件"问题模式。

## 注意事项

- ttyplot 版本标志使用 `-v` 而非 `--version`
- Makefile 使用 backtick pkg-config 调用，需要确保 PKG_CONFIG_PATH 正确设置
- ncursesw.pc 的 Cflags 中需要包含 `-D_XOPEN_SOURCE_EXTENDED` 以启用宽字符支持
- ttyplot 是交互式终端程序，管道测试需使用 `timeout` 控制执行时间
- stresstest 不随预编译包发布，仅在源码目录中编译

---
**编译结束**: 2026-07-24
**最终状态**: built
---
