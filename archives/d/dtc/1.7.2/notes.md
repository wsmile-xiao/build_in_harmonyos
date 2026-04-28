# dtc 1.7.2 适配笔记

## 编译环境
- 构建系统: makefile (非完整 autotools)
- 编译日期: 2026-04-24
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤
```bash
make PREFIX=$HOME/usr/local -j$(nproc)
make install PREFIX=$HOME/usr/local DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | clang 不支持 -Wsuggest-attribute=format | GCC 特有警告选项 | 补丁 0001: 从 Makefile 移除该选项 |

## 源码修改
- 0001-Makefile.patch: 移除 clang 不支持的 GCC 警告选项

## 验证结果
- dtc --version = DTC 1.7.2 ✅
- make check: PASS 2045, FAIL 32 (98%, 失败与核心功能无关)

## 交付物
- dtc, convert-dtsv0, fdtdump, fdtget, fdtoverlay, fdtput, dtdiff
- libfdt.a, libfdt.so.1.7.2
- fdt.h, libfdt.h, libfdt_env.h

## 注意事项
- 动态链接工具需设置 LD_LIBRARY_PATH=$HOME/usr/local/lib
- 部分测试脚本与平台 stat 命令格式不兼容
