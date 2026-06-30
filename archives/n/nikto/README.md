# nikto

nikto 是一个基于 Perl 的 Web 服务器安全扫描器，用于发现潜在的漏洞和安全问题。

## 功能概述

- 扫描 Web 服务器的潜在安全问题
- 检查超过 6700 个潜在危险文件/CGI
- 检查服务器软件版本过旧问题
- 检查服务器配置问题
- 支持 SSL 加密扫描
- 支持多种输出格式（HTML、XML、CSV、文本）
- 支持插件扩展

## OHOS 适配要点

### Perl 脚本特性

nikto 是一个 Perl 脚本工具，无需传统编译流程：

```bash
# 直接运行
perl nikto.pl -h <target>

# 或打包为可执行包
```

### Perl 环境要求

需要 Perl 解释器和相关模块：

- Perl 5.x 或更高版本
- Net::SSLeay（SSL 支持）
- JSON::PP（JSON 输出）

### 打包方式

在 OHOS 上，nikto 打包为：

- 可执行脚本包（包含所有配置文件和插件）
- 资源文件（数据库、模板等）

## 依赖关系

### 运行依赖
- Perl 5.x
- Net::SSLeay（可选，用于 SSL）
- libssl（Net::SSLeay 的依赖）

## 使用示例

```bash
# 基本扫描
nikto -h http://example.com

# SSL 扫描
nikto -h https://example.com -ssl

# 输出为 HTML
nikto -h http://example.com -output result.html -Format htm
```

## 参考资料

- 官方仓库：https://github.com/sullo/nikto
- 官方文档：https://cirt.net/nikto2-docs
- GitHub Releases：https://github.com/sullo/nikto/releases