# e2tools

## 简介

e2tools 是一组用于读取、写入和操作 ext2/ext3 文件系统中文件的 GPL 工具集。它允许用户在不挂载文件系统的情况下，直接访问 ext2/ext3/ext4 文件系统镜像中的文件。

## 版本信息

- 当前版本: 0.1.2
- 发布日期: 2024-09-16
- 源码地址: https://github.com/e2tools/e2tools

## 提供的工具

e2tools 包含以下命令：

| 命令 | 说明 | 类似命令 |
|------|------|----------|
| e2cp | 复制文件到/从 ext2 文件系统 | cp |
| e2ln | 在 ext2 文件系统中创建链接 | ln |
| e2ls | 列出 ext2 文件系统中的文件 | ls |
| e2mkdir | 在 ext2 文件系统中创建目录 | mkdir |
| e2mv | 移动/重命名 ext2 文件系统中的文件 | mv |
| e2rm | 删除 ext2 文件系统中的文件 | rm |
| e2tail | 显示 ext2 文件系统中文件的尾部 | tail |

## 功能特点

1. **无需挂载**：直接操作 ext2/ext3/ext4 文件系统镜像或设备，无需挂载
2. **脚本友好**：所有命令支持标准命令行参数，便于脚本调用
3. **轻量级**：单个主程序通过符号链接实现所有子命令
4. **兼容性好**：支持 ext2/ext3/ext4 文件系统格式

## 使用场景

- 嵌入式系统开发：修改根文件系统镜像
- 系统维护：在不挂载的情况下访问文件系统
- 镜像制作：创建和修改 ext 文件系统镜像
- 灾难恢复：从损坏的文件系统中提取文件

## HarmonyOS 编译说明

### 依赖

- e2fsprogs >= 1.27（提供 libext2fs 和 libcom_err）
- pkg-config

### 编译命令

```bash
# 设置环境变量
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig"
export TMPDIR=/storage/Users/currentUser/tmp

# 配置
./configure --prefix=$DEFAULT_PREFIX

# 编译
make -j2

# 安装
make install DESTDIR=$TEST_PREFIX
```

### 注意事项

1. e2fsprogs 预编译包可能缺少部分头文件，需要补充
2. configure 生成的 config.status 需要使用外部临时目录（HMDFS 限制）

## 许可证

GPL-2.0-or-later

## 参考

- GitHub: https://github.com/e2tools/e2tools
- 文档: https://e2tools.github.io/