# UUID Library

> Universally Unique Identifier library - extracted from util-linux

## 简介

UUID 库提供生成和分析 UUID（Universally Unique Identifier）的功能。UUID 是 128 位的全局唯一标识符，广泛用于分布式系统中的对象标识。

本库从 util-linux 项目提取，只编译 libuuid 组件，避免编译整个 util-linux 工具集。

主要功能：
- **UUID 生成**：生成基于时间、随机数、哈希的 UUID
- **UUID 解析**：将字符串转换为 UUID 结构
- **UUID 格式化**：将 UUID 结构转换为字符串
- **UUID 比较**：比较两个 UUID 是否相同

## OHOS 适配要点

### 编译建议

只编译 uuid 组件，不编译整个 util-linux：

```bash
./configure \
  --prefix=$HOME/usr/local \
  --disable-all-programs \
  --enable-libuuid
```

### 补丁说明

util-linux 在 HarmonyOS 上编译会生成大量平台相关补丁（10 个），主要是：
- Makefile 路径调整
- config.h 平台定义
- libtool 配置调整

这些补丁由 `ohc-run.py refresh-patch --auto` 自动生成，不需要手动干预。

## 排除与替代

不建议编译整个 util-linux，因为：
- 包含大量工具（mount, fdisk, kill 等）
- 许多工具依赖系统特定功能
- 只需要 libuuid 即可满足依赖需求

替代方案：只编译 libuuid 组件。

## 依赖

无外部依赖。

## 功能验证

```bash
# 验证库文件已安装
ls ~/usr/local/lib/libuuid.so

# 验证 pkg-config 可检测
pkg-config --modversion uuid
# 输出：2.40.0

# 测试头文件
ls ~/usr/local/include/uuid/uuid.h
```

## 参考

- [util-linux 官网](https://cdn.kernel.org/pub/linux/utils/util-linux/)
- [UUID 规范 RFC 4122](https://tools.ietf.org/html/rfc4122)
- [GitHub 镜像](https://github.com/util-linux/util-linux)