# E547: ltrace 缺少 aarch64 支持

## 问题描述
ltrace 0.7.3 不包含 aarch64 架构的 sysdeps 实现，导致在 aarch64 平台上构建失败。

## 错误特征
```
No rule to make target 'sysdeps/linux-gnu/aarch64/trace.c'
sysdeps/linux-gnu/aarch64: No such file or directory
```

## 根本原因
ltrace 0.7.3 发布于 2013 年，当时 aarch64 (ARM 64-bit) 尚未普及。源码只包含：
- `sysdeps/linux-gnu/arm/` - ARM 32-bit 支持
- `sysdeps/linux-gnu/x86/` - x86 支持
- 没有 `sysdeps/linux-gnu/aarch64/`

## 解决方案

### 方法：创建符号链接复用 ARM32 实现

```bash
ln -sf arm sysdeps/linux-gnu/aarch64
```

### 在 Conan 配方中集成

```python
def build(self):
    # ⚠️ 顺序很重要：符号链接 → 补丁 → 构建
    
    # 1. 创建 aarch64 → arm 符号链接
    symlink_dir = os.path.join(self.source_folder, "sysdeps", "linux-gnu")
    aarch64_link = os.path.join(symlink_dir, "aarch64")
    if not os.path.exists(aarch64_link):
        os.symlink("arm", aarch64_link)
    
    # 2. 应用补丁（补丁会修改 arm/ 目录的文件）
    self.apply_conandata_patches()
    
    # 3. 继续构建
    autotools = Autotools(self)
    autotools.configure()
    autotools.make()
```

### 为什么要在补丁之前？

如果后续补丁修改 `sysdeps/linux-gnu/arm/*.c` 文件，而符号链接还不存在，补丁应用会失败：
```
can't find file to patch at input line 5
Perhaps you used the wrong -p or --strip option?
```

## 实际案例

**ltrace 0.7.3** 适配流程：
1. 创建符号链接 `aarch64 → arm`
2. 应用 17 个补丁（其中 4 个修改 arm/ 目录）
3. configure + make

## 替代方案

### 方案 1：升级到更新版本
ltrace 0.8.0+ 可能已原生支持 aarch64（需验证）

### 方案 2：手动移植
复制 `arm/` 到 `aarch64/` 并修改架构相关代码（工作量大）

## 验证
```bash
# 检查符号链接
ls -l sysdeps/linux-gnu/aarch64
# 应输出: aarch64 -> arm

# 检查构建目标
make -n | grep aarch64
```

## 相关知识
- E546: aarch64 pt_regs 结构差异
- E548: 其他架构移植问题
