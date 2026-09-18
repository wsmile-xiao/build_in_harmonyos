# AdaCGI

AdaCGI 是一个 Ada 95 语言的 Common Gateway Interface (CGI) 接口库，由
David A. Wheeler 开发。它提供 `CGI` 和 `Ustrings` 两个 Ada 包，使 Ada
程序能够被 Web HTTP 服务器通过标准 CGI 接口调用。

## 功能概述

- **CGI 包**：解析 GET/POST 请求，按位置或键名访问参数，支持重复键、
  URL 编解码、HTML 转义、Cookie 处理、多行数据等
- **Ustrings 包**：简化 `Ada.Strings.Unbounded` 的使用

## OHOS 适配

AdaCGI 是纯 Ada 源码库，没有 C/C++ 依赖，不需要交叉编译 C 代码。适配
方式：

1. 依赖 `gcc-ada/9.5.0`（GNAT Ada 编译器）作为构建工具链
2. 打包未修改的上游 `CGI`/`Ustrings` 源单元到 `adainclude/`
3. 下游消费者用 `gnatmake -I<adainclude>` 现场编译
4. 生成的可执行文件需用 `binary-sign-tool` 签名后才能运行

## 许可证

- 主库（CGI）：LGPL-2.1-or-later（含修改与澄清，见 `cgi.ads`）
- Ustrings：public domain

## 依赖关系

- 构建工具链：`gcc-ada/9.5.0`（GNAT）
- 运行时依赖：无（纯源码库，编译进消费者程序）

## 参考资料

- 官网：http://www.dwheeler.com/adacgi
- Debian 源码包：https://packages.debian.org/source/adacgi
- Conan 引用：`adacgi/1.6@ohpcd/stable`
