# dcron (Dillon's Cron Daemon)

## 简介

dcron 是一个轻量级的 cron 守护进程实现，由 Matt Dillon 开发。它是类 Unix 系统中用于定时执行任务的标准工具，相比其他 cron 实现（如 vixie-cron），dcron 更加简洁轻量。

## 功能说明

### 核心组件

- **crond**: cron 守护进程，负责在后台定期执行定时任务
- **crontab**: 用户任务管理工具，用于创建、编辑和管理用户的定时任务列表

### 主要功能

1. **定时任务执行**: 根据 crontab 文件中定义的时间表执行命令
2. **多用户支持**: 每个用户可以拥有自己的 crontab 文件
3. **系统级任务**: 支持系统管理员定义的全局定时任务
4. **日志记录**: 记录任务执行情况和错误信息
5. **时间戳管理**: 跟踪任务执行状态

### Crontab 格式

```
* * * * * command
│ │ │ │ │
│ │ │ │ └─ 星期几 (0-7, 0 和 7 表示周日)
│ │ │ └─── 月份 (1-12)
│ │ └───── 日期 (1-31)
│ └─────── 小时 (0-23)
└───────── 分钟 (0-59)
```

## 使用方法

### 基本命令

```bash
# 编辑当前用户的 crontab
crontab -e

# 列出当前用户的 crontab
crontab -l

# 删除当前用户的 crontab
crontab -r

# 启动 cron 守护进程
crond

# 以调试模式运行
crond -d
```

### 配置文件位置

- **系统级 crontab**: `/etc/cron.d/`
- **用户 crontab**: `/var/spool/cron/`
- **时间戳文件**: `/var/spool/cronstamps/`

### 示例任务

```bash
# 每天凌晨 2 点备份
0 2 * * * /usr/local/bin/backup.sh

# 每小时检查日志
0 * * * * /usr/local/bin/check-logs.sh

# 每周一早上 8 点清理
0 8 * * 1 /usr/local/bin/cleanup.sh

# 每 5 分钟检查服务状态
*/5 * * * * /usr/local/bin/check-service.sh
```

## 版本信息

### 当前版本: 4.2

**发布日期**: 2010-01-11

**已编译版本**: 4.2

**编译状态**: ✅ built

**编译日期**: 2026-05-25

**测试日期**: 2026-05-25

**目标平台**: OpenHarmony aarch64

**编译器**: clang

### 编译选项

```makefile
CC = clang
CFLAGS = -O2 -Wall -Wstrict-prototypes -fPIC
LDFLAGS = -Wl,-rpath,$(PREFIX)/lib
```

### 依赖

- **运行时依赖**: 无外部库依赖（静态编译）
- **构建依赖**: clang, make

## 安装

### 从源码编译

```bash
# 解压
tar -xzf dcron-4.2.tar.gz
cd dcron-4.2

# 应用补丁（鸿蒙平台）
patch -p1 < patches/0001-Makefile.patch

# 编译
make

# 安装
make install DESTDIR=/path/to/install PREFIX=/usr/local
```

### 从预编译包安装

```bash
# 下载预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- dcron 4.2
```

## 功能测试结果

### 测试状态: ✅ 基本功能通过

| 功能项 | 状态 | 说明 |
|--------|------|------|
| crond 版本显示 | ✅ PASS | "dillon's cron daemon 4.2" |
| crond 参数解析 | ✅ PASS | 所有选项正常识别 |
| crontab 基本功能 | ⚠️ WARN | 需用户数据库支持 |
| ELF 签名 | ✅ PASS | 已签名，可执行 |
| RPATH 设置 | ✅ PASS | 正确指向 ~/usr/local/lib |

### 已知限制

1. **用户数据库限制**: crontab 需要 getpwuid() 支持，鸿蒙系统用户数据库不完整
2. **临时目录限制**: crond 启动需要可写 TMPDIR（/tmp 只读，E002）

### 部署建议

```bash
# 1. 创建必需目录
mkdir -p /etc/cron.d /var/spool/cron /var/spool/cronstamps /var/log

# 2. 设置临时目录
export TMPDIR=/data/local/tmp  # 或其他可写目录

# 3. 使用系统级任务替代用户任务
echo "* * * * * root /path/to/script.sh" > /etc/cron.d/mytask
```

## 文档

- **man crontab(1)**: crontab 命令手册
- **man crond(8)**: crond 守护进程手册
- **README**: 源码包中的说明文件

## 许可证

dcron 使用 BSD 许可证，允许自由使用、修改和分发。

## 相关链接

- **官方网站**: http://www.jimpryor.net/linux/dcron.html
- **源码仓库**: (原项目已停止维护)
- **OpenHarmony 移植**: 由 OpenHarmonyPCDeveloper 社区维护

## 更新历史

- **2026-05-25**: 功能测试完成，验证基本功能正常
- **2026-05-25**: 完成 OpenHarmony aarch64 平台适配
- **2010-01-11**: dcron 4.2 发布