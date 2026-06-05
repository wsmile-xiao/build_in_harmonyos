# E091 — meson subdir 顺序导致的变量未定义错误

## 错误特征
meson setup 失败，报错：
```
silk/meson.build:28:45: ERROR: Unknown variable "have_arm_intrinsics_or_asm".
```

## 触发条件
- 构建系统: meson
- 阶段: configuration (meson setup)
- 软件: opus 1.4

## 根因分析
opus 1.4 的 meson.build 中，subdir() 调用顺序为：
1. `subdir('include')`
2. `subdir('silk')` — 使用 `have_arm_intrinsics_or_asm` 变量
3. `subdir('celt')` — 定义 `have_arm_intrinsics_or_asm` 变量

silk/meson.build 第 28 行使用 `have_arm_intrinsics_or_asm`，但此变量在 celt/meson.build 中才被定义，导致 silk 执行时变量未定义。

这是一个典型的 meson 跨 subdir 变量依赖问题，subdir 的执行顺序决定了变量的可见性。

## 解决方案

### 推荐方案（优先级 1）
在主 meson.build 的第一个 subdir() 调用之前，将变量定义从 celt/meson.build 移到主文件：

```meson
# Define have_arm_intrinsics_or_asm before silk subdir
have_arm_intrinsics_or_asm = have_arm_ne10
if (intrinsics_support.length() + asm_optimization.length() + inline_optimization.length()) > 0
  have_arm_intrinsics_or_asm = true
endif

subdir('include')
subdir('silk')
subdir('celt')
```

### 回退方案（优先级 2）
调整 subdir 调用顺序，将 celt 放在 silk 之前：
```bash
sed -i "s/subdir('silk')/subdir('celt')/; s/subdir('celt')/subdir('silk')/" meson.build
```

### 禁止做法
- ❌ 直接设置 `have_arm_intrinsics_or_asm = true` 而不使用条件判断
  - 原因：可能在不支持 ARM intrinsics 的平台上启用错误的优化路径
  - 后果：编译失败或运行时崩溃

## 验证
```bash
# 验证变量使用位置
grep -n "have_arm_intrinsics_or_asm" */meson.build

# 验证修复后 meson setup 成功
meson setup builddir --prefix=$HOME/usr/local
```

## 关联条目
- 相关: E090 (meson host_system 检查)
