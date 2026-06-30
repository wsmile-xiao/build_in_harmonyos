# help2man 1.49.3 编译记录

## 编译环境
- 构建系统: script（纯 Perl）
- 编译日期: 2026-04-30
- 编译器: N/A（Perl 脚本）
- 状态: success

## 编译步骤

### Step 1: 初始化
- 下载源码: https://ftp.gnu.org/gnu/help2man/help2man-1.49.3.tar.xz
- 解压到: ~/tmp/builds/help2man-1.49.3.work
- 软件类型识别: 纯 Perl 脚本

### Step 2: 构建
- configure 遇到临时文件权限问题（鸿蒙系统限制）
- 解决方案: 直接使用 help2man.PL 生成脚本
- 执行: `perl help2man.PL --stdout > help2man.generated`
- 自动检测并嵌入正确的 perl 路径: `/data/service/hnp/perl.org/perl_5.42.0/bin/perl`

### Step 3: 安装
- DESTDIR 模式安装到 staging 目录
- 安装路径: ~/tmp/test-install-help2man-1.49.3/$DEFAULT_PREFIX
- 安装文件:
  - bin/help2man (20097 bytes)
  - share/man/man1/help2man.1 (4131 bytes)
  - share/info/help2man.info (18042 bytes)

### Step 4: 验证
- help2man --version 输出正确: GNU help2man 1.49.3
- 无二进制文件需要 ELF 签名（纯 Perl 脚本）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 临时文件权限问题 | 鸿蒙系统对临时目录创建的限制 | 直接运行 help2man.PL 生成脚本 |
| 2 | 无 ELF 签名要求 | 纯 Perl 脚本，非二进制文件 | 无需处理，脚本可直接执行 |

## 依赖版本
- perl 5.42.0（系统预装）
- GNU sed（用于管道文本处理）

## 验证结果
- help2man --version → GNU help2man 1.49.3 ✅
- help2man --help 正常工作 ✅

---

**编译开始**: 2026-04-30 01:07
**编译结束**: 2026-04-30 01:10
**最终状态**: success