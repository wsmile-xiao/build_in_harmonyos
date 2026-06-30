# perl-mail-spamassassin

SpamAssassin - Apache 基金会的开源垃圾邮件过滤器

## 描述

SpamAssassin 是一个强大的邮件过滤器，使用多种技术来识别垃圾邮件：

- **贝叶斯分类器**: 通过学习垃圾邮件和正常邮件样本来提高识别精度
- **网络黑名单 (RBL)**: 查询 DNS 黑名单服务
- **邓普斯规则集**: 默认的垃圾邮件检测规则
- **内容分析**: 检查邮件头、正文、链接等特征

## 版本历史

| 版本 | 状态 | 编译日期 | 备注 |
|-----|------|---------|------|
| 4.0.2 | built | 2026-06-15 | 功能测试通过，可立即使用 |

## 依赖

### 运行时依赖
- Perl 5.42.0+
- perl-mail-dkim
- perl-mail-domainkeys
- perl-net-dns
- perl-http-date
- perl-io-socket-ssl
- perl-mailtools
- perl-mime-base64

### 可选依赖
- perl-dbi (用于 SQL 后端存储)
- Redis (用于贝叶斯存储)
- MySQL/PostgreSQL (用于贝叶斯存储)

## 使用方法

### 1. 安装

```bash
# 解压预编译包到 ~/usr/local/
tar xzf perl-mail-spamassassin-4.0.2-ohos-aarch64.tar.gz -C ~/usr/local/
```

### 2. 获取规则

首次使用需要运行 `sa-update` 获取垃圾邮件检测规则：

```bash
sa-update
```

### 3. 配置

编辑配置文件 `~/usr/local/etc/mail/spamassassin/local.cf`。

### 4. 使用

```bash
# 扫描单个邮件
spamassassin -t < mail.txt

# 启动守护进程
spamd -d

# 使用 C 客户端快速扫描
spamc < mail.txt

# 学习垃圾邮件样本
sa-learn --spam spam_folder/

# 学习正常邮件样本
sa-learn --ham ham_folder/
```

## 主要组件

| 命令 | 说明 |
|-----|------|
| spamassassin | 主命令，扫描邮件 |
| spamc | C 客户端，快速扫描 |
| spamd | 守护进程，服务模式 |
| sa-learn | 贝叶斯学习工具 |
| sa-update | 规则更新工具 |
| sa-compile | 规则编译工具 |
| sa-awl | 自动白名单管理 |
| sa-check_spamd | spamd 检查工具 |

## 测试结果

见 `4.0.2/reports/test-report.md`。

- ✅ 所有命令正常工作
- ✅ Perl 模块正常加载
- ✅ spamc 二进制已签名可执行

## 许可证

Apache License 2.0

## 主页

https://spamassassin.apache.org/