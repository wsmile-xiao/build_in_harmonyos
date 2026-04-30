# E081: config.sub kernel-os 验证缺少 linux-ohos

## 问题识别

### 典型错误日志
```
Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'.
configure: error: /bin/sh ./build-aux/config.sub aarch64-unknown-linux-ohos failed
```

### 触发条件
- 已应用 patch-autotools-ohos.pl 补丁
- config.guess 正确输出 aarch64-unknown-linux-ohos
- config.sub 在 kernel-os 组合验证阶段失败

## 根因分析

GNU config.sub 脚本的最后一步是验证 kernel-os 组合是否合理：
```bash
case $kernel-$os-$obj in
    linux-gnu*- | linux-android*- | ... | linux-uclibc*- )
        ;;
    ...
esac
```

patch-autotools-ohos.pl 脚本只修改了：
1. OS 列表（添加 ohos*）
2. 基本三元组（添加 ohos-linux）

但**未修改 kernel-os 验证列表**，导致即使 OS 被识别为 ohos，
kernel-os 组合验证仍然失败。

## 解决方案

### 方法 1: 手动修改 config.sub
定位到 `case $kernel-$os-$obj in` 分支，在 `linux-uclibc*- )` 后添加：

```bash
case $kernel-$os-$obj in
    linux-gnu*- | linux-android*- | ... | linux-uclibc*- | linux-ohos*- )
        ;;
```

### 方法 2: 使用 sed 命令
```bash
sed -i '/linux-uclibc\*- )/a\            | linux-ohos*- )/' build-aux/config.sub
```

### 方法 3: 更新 patch-autotools-ohos.pl 脚本
将 linux-ohos 添加到脚本的补丁列表中，使其自动处理。

## 验证修复

```bash
# 检查补丁是否应用
grep "linux-ohos" build-aux/config.sub

# 测试 config.sub
./build-aux/config.sub aarch64-unknown-linux-ohos
# 应输出：aarch64-unknown-linux-ohos
```

## 影响范围

所有 autotools 项目在 HarmonyOS 上编译时，即使应用了 patch-autotools-ohos.pl，
仍可能遇到此问题。

## 关联知识

- E007: config.guess 无法识别 HarmonyOS 系统
- patch-autotools-ohos.pl 脚本需要更新以包含此修复

## 案例

- libseccomp 2.6.0 编译遇到此问题