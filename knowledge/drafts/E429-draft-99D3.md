# E429 — musl 下 FILE 为不透明类型导致 sizeof(FILE) 编译失败

## 错误特征
```
error: arithmetic on a pointer to an opaque type
error: invalid application of 'sizeof' to an incomplete type 'FILE'
```
典型出现于老式 C 代码（解释器/嵌入式常见）以 `sizeof(FILE)` 估算 FILE 存储布局，在 OHOS/musl 工具链（clang，`-DUNIX_HOST` 类）编译期报错。

## 触发条件
- 构建系统: make / autotools / cmake 均可能
- 阶段: make（编译期，触及 stdio 相关源文件时）
- 平台: OHOS PC / 任何 musl libc 目标

## 根因分析
musl 的 `FILE` 为不透明类型（内部布局不外露），`sizeof(FILE)` 非法。glibc 时代源码常用 `sizeof(FILE)` 作 FILE 存储上限估算，迁移 musl/OHOS 必须改造为常量。

## 解决方案

### 推荐方案
libc 能力守卫（非平台宏）：`__GLIBC__` 分支保留 `sizeof(FILE)`，其余 libc 使用固定上限（实测 picoc 用 512）。安全性前提：该尺寸仅作解释器侧结构存储布局、真实 FILE 对象全程经指针使用时，上限取值不影响正确性。
案例：`archives/p/picoc/2.1/patches/0001-cstdlib-stdio.c.patch`（R8 口径：`__GLIBC__` 为 libc 能力检测例外，PR 正文附理由）。

### 禁止做法
- ❌ 用 `#ifdef __OHOS__` 平台宏做分支（patches 新增行禁平台宏，R8/PF5）
- ❌ 把不透明类型强转为已知结构猜测字段偏移
- ❌ 无指针语义论证就直接缩小缓冲区（可能截断真实 FILE 数据）

## 验证
```bash
printf '#include <stdio.h>\nint s;\nint main(){s=sizeof(FILE);return 0;}\n' | clang -xc -c - 2>&1 | grep -iE "opaque|incomplete"
# 命中 opaque/incomplete 即确认为本模式；补丁后同命令零输出
```

## 关联
- 软件/版本: picoc 2.1（patches/0001-cstdlib-stdio.c.patch）
- 相邻条目: E093（glibc 专有函数族缺失，同类 libc 能力守卫思路）
