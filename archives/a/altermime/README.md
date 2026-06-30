# alterMIME

## 简介

alterMIME 是一个邮件 MIME 编码处理工具，用于自动修改邮件 MIME 内容。它可以：

- 在邮件中插入文本或 HTML 免责声明
- 修改邮件头信息
- 移除或替换附件
- 处理 multipart MIME 消息

## 版本信息

- **当前版本**: 0.3.10
- **发布日期**: November 2008
- **作者**: Paul L Daniels
- **官网**: http://www.pldaniels.com/altermime

## 功能特性

1. **免责声明插入**: 自动在邮件末尾添加文本或 HTML 格式的免责声明
2. **邮件头修改**: 支持添加、修改、删除邮件头字段
3. **附件处理**: 支持移除、替换附件
4. **MIME 解码**: 支持多种 MIME 编码格式（base64、quoted-printable 等）

## 编译说明

### 编译要求

- C 编译器（clang/gcc）
- make 工具

### 编译步骤

alterMIME 使用简单的 Makefile，无需 configure 步骤：

```bash
# 编译
make

# 安装（自定义路径）
export prefix=/usr/local
export DESTDIR=/path/to/staging
make install
```

### 补丁说明

**版本 0.3.10** 需要以下补丁：

1. **0001-Makefile.patch**:
   - 移除 `-Werror` 标志（适配新版 clang）
   - 添加 `prefix` 变量和 `DESTDIR` 支持

## 使用示例

### 添加免责声明

```bash
altermime --input=email.eml --disclaimer=disclaimer.txt
```

### 添加 HTML 免责声明

```bash
altermime --input=email.eml --disclaimer-html=disclaimer.html --htmltoo
```

### 移除附件

```bash
altermime --input=email.eml --removeall
```

### 修改邮件头

```bash
altermime --input=email.eml --xheader="X-Custom-Header: Value"
```

## 依赖关系

alterMIME 是独立的 C 程序，无外部库依赖：
- 动态链接：musl libc

## 注意事项

1. **上游停止维护**: 最后更新于 2008 年，建议关注替代方案
2. **编译警告**: 源码存在编译器警告，但不影响功能
3. **ELF 签名**: HarmonyOS 上需要签名才能执行

## OpenHarmony 编译状态

- **状态**: built
- **编译日期**: 2026-06-18
- **架构**: aarch64
- **测试**: 通过

## 相关链接

- [官方网站](http://www.pldaniels.com/altermime)
- [源码下载](http://www.pldaniels.com/altermime/altermime-0.3.10.tar.gz)