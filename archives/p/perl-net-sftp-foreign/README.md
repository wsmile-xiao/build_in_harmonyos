# perl-net-sftp-foreign

Secure File Transfer Protocol (SFTP) client — pure Perl implementation.

## 软件描述

Net::SFTP::Foreign 是一个纯 Perl 实现的 SFTP 客户端模块，通过外部 `ssh` 命令实现
SFTP 协议通信。与需要 XS/C 编译的模块不同，本模块完全由 Perl 编写，
在鸿蒙平台上无需任何适配即可编译和使用。

## 版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 1.93-r0 | built | 2026-06-26 | conan-verify 全部通过, 功能测试通过 |

## 关键特性

- **纯 Perl 模块** — 无 XS/C 代码，无需 C 编译器
- **无外部依赖** — 所有依赖均为 Perl 核心模块
- **无 SELinux 限制** — 不受 HMDFS 限制，可从用户目录直接加载
- **无需补丁** — 源码无需任何修改即可在鸿蒙平台编译
- **完整 API** — 50+ 方法: 文件传输、目录操作、属性查询、链接操作等

## 使用方法

```bash
# 通过 Conan 安装
conan install --requires=perl-net-sftp-foreign/1.93-r0@ohpcd/stable

# 设置环境变量
source conanrun.sh

# Perl 中使用
perl -MNet::SFTP::Foreign -e '
  my $sftp = Net::SFTP::Foreign->new(host => "example.com");
  $sftp->get("/remote/file.txt", "/local/file.txt");
  $sftp->put("/local/file.txt", "/remote/file.txt");
  my @files = $sftp->ls("/remote/dir");
'
```

## 运行时要求

- Perl 5.42.0+
- ssh 命令 (用于 SFTP 连接)
