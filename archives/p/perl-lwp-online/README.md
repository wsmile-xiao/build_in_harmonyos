# LWP::Online

> Perl module to check if your process has access to the web

## 简介

LWP::Online 是一个 Perl 模块，用于检测当前进程是否可以访问互联网。它尝试回答一个复杂的技术问题："我是否在线？"

该模块通过检查 LWP 连接性（HTTP/HTTPS）来判断网络状态，支持检测多种网络环境下的连接情况，包括防火墙、代理等场景。

## OHOS 适配要点

- 这是一个纯 Perl 模块，无需编译 XS/C 代码
- 依赖 LWP::Simple 和 URI 模块，需要预先安装
- 测试需要网络连接，在编译环境中测试会被跳过
- 安装后可直接加载使用

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| perl | 5.42.0+ | Perl 解释器 |
| perl-libwww | 6.81+ | LWP::Simple 模块 |
| URI | 5.28+ | URI 处理模块 |

## 功能验证

```bash
# 检查模块版本
perl -MLWP::Online -e 'print $LWP::Online::VERSION'

# 测试在线检测（需要实际网络）
perl -MLWP::Online -e 'print online() ? "Online" : "Offline"'
```

## 参考

- [CPAN 文档](https://metacpan.org/pod/LWP::Online)
- [源码仓库](http://svn.ali.as/cpan/trunk/LWP-Online)