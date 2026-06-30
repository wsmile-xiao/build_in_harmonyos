# ruby-install

ruby-install 是一个用于安装 Ruby、JRuby、TruffleRuby 和 mruby 的工具。

## 功能特性

- 支持从 ruby-versions 下载最新版本和校验和
- 支持安装到 /opt/rubies/（root）或 ~/.rubies/（用户）
- 支持安装到任意目录
- 支持从镜像下载
- 支持下载和应用补丁
- 支持传递任意 configure 选项
- 支持通过 wget 或 curl 下载
- 支持通过 MD5、SHA1、SHA256 或 SHA512 校验和验证下载
- 支持从包管理器安装构建依赖
- 支持多种操作系统：Linux、macOS、FreeBSD

## 依赖

- bash >= 3.x
- grep
- wget > 1.12 或 curl
- md5sum/md5、sha1sum/sha1、sha256sum/sha256、sha512sum/sha512
- tar、bzip2、xz
- patch（可选）
- gcc >= 4.2 或 clang（用于编译 Ruby，ruby-install 本身不需要）

## 使用方法

```bash
# 列出支持的 Ruby 版本
ruby-install

# 安装最新版本的 Ruby
ruby-install --update ruby

# 安装特定版本
ruby-install ruby 3.1.2

# 安装到指定目录
ruby-install --install-dir /path/to/dir ruby
```

## 注意事项

此工具本身为纯 shell 脚本，无需编译。安装 Ruby 时需要编译器支持。