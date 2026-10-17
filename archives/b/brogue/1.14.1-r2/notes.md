# brogue 1.14.1-r2 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# config.mk 和 Makefile 都在源根目录（非 src/），configure 阶段 cwd=源根
sed -i 's/TERMINAL := NO/TERMINAL := YES/' config.mk
sed -i 's/GRAPHICS := YES/GRAPHICS := NO/' config.mk
make CC=clang CFLAGS='-fPIC -O2'
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SDL2 在 OHOS 上不可用 | 鸿蒙无 SDL2 图形库 | 使用终端模式 (TERMINAL=YES, GRAPHICS=NO) |
| 2 | config.mk 默认开启图形模式 | 上游默认 SDL 图形 | sed 内联修改 config.mk 启用终端模式 |

---

**编译结束**: 2026-07-19 12:42
**最终状态**: built
