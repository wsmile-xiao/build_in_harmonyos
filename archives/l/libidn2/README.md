# libidn2

> IDNA 2008 国际化域名处理库

## 简介

libidn2 是 GNU IDN 库的现代化版本，实现了 IDNA 2008 标准（RFC 5890-5893），用于处理国际化域名（Internationalized Domain Names，IDN）。它可以将包含非 ASCII 字符的域名转换为符合 DNS 协议要求的 ASCII 格式（Punycode），反之亦然。

libidn2 是 libidn 的升级版本，支持更新的 IDNA 2008 标准，相比 IDNA 2003（libidn 实现），IDNA 2008 提供了更完善的国际化域名处理规则，解决了许多边界情况和兼容性问题。该库提供了 C 语言 API 和命令行工具 `idn2`，广泛应用于邮件客户端、Web 浏览器、DNS 工具等需要处理国际化域名的软件中。

## OHOS 适配要点

- **依赖处理**：libidn2 依赖 libunistring 库，需先编译安装 libunistring
- **配置选项**：标准 autotools 构建系统，使用 `--prefix=/data/data/com.example.harmonyapp/files/usr/local`
- **musl 动态链接器限制**：用户环境下动态库不可用，需采用静态链接方案
- **静态链接**：idn2-static 静态链接成功，功能验证通过

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libunistring | 1.4.2 | Unicode 字符串处理库 |

## 功能验证

```bash
# 验证 idn2 工具
idn2 --version

# 测试国际化域名转换
echo "测试.中国" | idn2
# 输出: xn--0zwm56d.xn--fiqs8s

# 反向转换
echo "xn--0zwm56d.xn--fiqs8s" | idn2 -d
# 输出: 测试.中国
```

## 参考

- [官方文档](https://www.gnu.org/software/libidn/libidn2/manual/)
- [源码仓库](https://gitlab.com/libidn/libidn2)
- [IDNA 2008 标准](https://datatracker.ietf.org/doc/html/rfc5890)