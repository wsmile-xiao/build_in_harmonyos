# Judy

**类别**: 数据结构库
**语言**: C
**许可证**: LGPL

## 简介

Judy是一个高性能的动态数组库，实现了多种高效的内存数据结构：

- **Judy1**: 位图数组（用于快速集合操作）
- **JudyL**: 线性数组（索引到值的映射）
- **JudySL**: 字符串数组（字符串到值的映射）
- **JudyHS**: 哈希数组（快速哈希查找）

## 特性

- 内存效率高：根据数据量动态调整内存使用
- 查找速度快：O(1)到O(log n)的时间复杂度
- 灵活的索引类型：支持任意整数索引
- 无需预分配：自动扩展和收缩

## 已编译版本

| 版本 | 状态 | 编译日期 | 预编译包 |
|------|------|---------|---------|
| 1.0.5 | published | 2026-05-29 | ✅ judy-1.0.5-ohos-aarch64.tar.gz |

## 使用方法

通过cmd-pkgs安装：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- judy 1.0.5
```

编译链接：

```bash
clang -I$HOME/usr/local/include -L$HOME/usr/local/lib your_program.c -lJudy -lm
```

## API示例

```c
#include <Judy.h>

// Judy1 (位图)
Pvoid_t PJ1Array = NULL;
Word_t Index = 100;
int Rc_int;

J1S(Rc_int, PJ1Array, Index);  // Set bit
J1T(Rc_int, PJ1Array, Index);  // Test bit

// JudyL (数组)
Pvoid_t PJLArray = NULL;
PPvoid_t PPValue;

JLI(PPValue, PJLArray, Index);  // Insert
*((Word_t*)PPValue) = 999;
JLG(PPValue, PJLArray, Index);  // Get
```

## 官方资源

- 主页: http://judy.sourceforge.net/
- 源码: https://sourceforge.net/projects/judy/
- 文档: 包含详细的man pages（安装后可查看）

## 鸿蒙适配说明

1.0.5版本已适配鸿蒙平台，主要修改：
- 更新config.guess/config.sub以识别aarch64-ohos
- 修复configure脚本的pipe语法问题

详见版本级notes.md。