# fcron

fcron 是一个周期性命令调度器，是传统 cron 的现代化替代品，支持更灵活的定时任务配置。

## 软件描述

fcron 是一个功能强大的任务调度器，提供以下特性：
- 支持 systemd 和传统 init 系统
- 支持 crontab 格式的任务定义
- 支持系统级和用户级任务配置
- 提供详细的日志和错误处理机制
- 支持 anacron 风格的任务调度（适合非持续运行的系统）

## 版本列表

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 3.4.1pre | built | 2026-05-26 | 开发预览版本，已适配鸿蒙系统 |

## 编译状态

### 最新版本：3.4.1pre

**状态**: ✅ built（编译成功）

**编译环境**:
- 构建系统：autotools
- 编译器：clang/clang++
- 平台：OpenHarmony

**已知限制**:
- 需要手动处理配置文件生成（临时目录权限问题）
- 邮件发送功能已禁用（--without-sendmail）
- 测试套件跳过（缺少 cmocka 库）

**交付物**:
- fcron：主守护进程
- fcrontab：定时任务管理工具
- fcronsighup：配置重载工具
- fcrondyn：动态控制工具

### 功能测试结果

**测试日期**: 2026-05-26

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 二进制完整性 | ✅ PASS | 所有文件 ELF PIE arm64 格式正确 |
| 版本一致性 | ✅ PASS | 所有工具版本 3.4.1pre |
| 配置完整性 | ✅ PASS | 配置文件路径正确 |
| 功能运行 | ⚠️ LIMITATION | 需要 fcron 用户（设计要求） |

**详细测试报告**: [3.4.1pre/reports/test-report.md](./3.4.1pre/reports/test-report.md)

### 部署前提条件

fcron 是系统级守护进程，部署前需要创建系统用户：

```bash
# 创建 fcron 用户和组
groupadd fcron
useradd -g fcron -s /bin/false fcron

# 设置配置文件权限
chown root:fcron /etc/fcron.conf
chmod 640 /etc/fcron.conf

# 创建运行目录
mkdir -p /var/spool/fcron /var/run

# 启动守护进程
fcron
```

**注意**: 部署脚本应包含用户创建步骤，否则 fcron 无法运行。

## 文档链接

- 详细编译笔记：[3.4.1pre/notes.md](./3.4.1pre/notes.md)
- 编译配置清单：[3.4.1pre/manifest.yaml](./3.4.1pre/manifest.yaml)
- 补丁文件：[3.4.1pre/patches/](./3.4.1pre/patches/)

## 相关资源

- 官方网站：http://fcron.free.fr
- 源码下载：fcron-3.4.1pre.tar.gz