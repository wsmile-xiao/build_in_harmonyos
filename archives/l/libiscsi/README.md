# libiscsi

## 简介

libiscsi 是一个客户端库，用于实现 iSCSI 协议，可以访问 iSCSI target 的资源。

## 主要特性

- 完全异步的 iSCSI 命令和 SCSI 任务处理
- 同步层 API，简化应用开发
- 低级 SCSI 库，用于创建 SCSI CDBs 和解析 data-in 结构
- 支持所有建立和维护 iSCSI 会话所需的功能

## 工具

编译后提供以下工具：

- **iscsi-ls**: 列出 portal 上的所有 targets 和 devices
- **iscsi-inq**: SCSI INQUIRY 命令工具
- **iscsi-perf**: 性能测试工具
- **iscsi-readcapacity16**: READCAPACITY16 命令工具
- **iscsi-swp**: 设置/清除 write protect 标志
- **ld_iscsi.so**: 用于 GNU ld 的链接器插件

## OpenHarmony 编译说明

### 构建系统

autotools (autoconf + automake + libtool)

### 编译步骤

```bash
# 1. 运行 autogen.sh 生成 configure
./autogen.sh

# 2. 应用 OpenHarmony 平台修复
./patches/apply-ohos-fixes.sh

# 3. 配置
./configure --prefix=$DEFAULT_PREFIX

# 4. 编译
make -j1

# 5. 安装
make install DESTDIR=$TEST_PREFIX  # staging
make install                        # 本地安装
```

### 平台适配问题

| 问题 ID | 描述 | 解决方案 |
|---------|------|---------|
| E011 | HMDFS umask 077 权限问题 | 应用 apply-ohos-fixes.sh |
| 函数声明 | socket.c 函数缺少参数类型 | 应用 0001-fix-function-declaration.patch |

### 已编译版本

- 1.19.0 (2026-05-25)

## 许可证

- LGPL-2.1 (库)
- GPL-2.0 (工具和示例)

## 来源

- GitHub: https://github.com/sahlberg/libiscsi
- 版本: 1.19.0