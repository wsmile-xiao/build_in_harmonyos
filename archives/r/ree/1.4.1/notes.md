# ree 1.4.1 适配笔记

## 编译环境
- 构建系统: makefile（手写 `makefile`，无 configure）
- 编译日期: 2026-09-23
- 编译器: clang 15（OHOS SDK 26.0.0.18）
- 状态: built

## 编译步骤

1. 从官方 codeload 取 tag `1.4.1` 的源码包（`ree-1.4.1.tar.gz`）。
2. `make -f makefile CC=<clang> CFLAGS="-O2 -Wall" -j1`，产出 `ree` 与 `fontdump`。
3. `package()` 安装 `bin/ree`、`bin/fontdump`、`ree.8`、`fontdump.1`、README 与 LICENSE。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 默认目标选择 | 上游同时存在手写 `makefile` 与 CMake 生成的 `Makefile` | GNU make 优先小写 `makefile`；为明确起见构建时用 `make -f makefile` |
| 2 | `ree` 运行时依赖 /dev/mem | 需 root 才能读物理内存 | 消费者测试接受 `could not open /dev/mem`（退出 1）或 `scanning`（退出 0）两种结果 |
| 3 | `fontdump` 的可测性 | 需要一个含有效 VGA 字体的 ROM | 测试用 `head -c /dev/zero` + `printf` 合成 2048 字节的 8x8 字体 ROM，验证提取结果字节一致 |

## 依赖版本

无三方依赖。

## 验证结果

```bash
# 上游测试：无（N=0）
# 消费者（test_package/test_ree.sh）
REE_CHECK_SUMMARY checks=9 fails=0
```

## 注意事项

- `ree` 扫描物理内存（c0000–f0000），在无 /dev/mem 读权限时按设计打印错误并退出 1；`fontdump` 是纯文件工具，测试不依赖特权。
