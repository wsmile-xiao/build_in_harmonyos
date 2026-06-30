# GNU Recode

## 简介

GNU Recode 是一个字符集转换工具，可以在各种字符集和文本格式之间转换文件。它支持超过 200 种字符集，包括 ASCII、ISO-8859 系列、UTF-8、UTF-16 等。

## 功能概述

- 字符集转换：支持 200+ 种字符集之间的相互转换
- 文本格式转换：支持各种换行符格式（Unix、Windows、Mac）
- MIME 编码：支持 Base64、Quoted-Printable 等编码
- 批量处理：支持批量转换多个文件
- 库接口：提供 C 语言库接口供其他程序调用

## OHOS 适配

### 平台识别

recode 使用 autotools 构建系统，需要替换 `build-aux/config.guess` 和 `build-aux/config.sub` 为支持 OpenHarmony 平台识别的版本（automake 提供的最新版本）。

### HMDFS 文件系统限制

OpenHarmony 的 HMDFS 文件系统有 SELinux 权限限制，configure 脚本中的 `umask 077` 会导致临时文件创建失败。需要修改为 `umask 022`：

```bash
sed -i 's/umask 077/umask 022/g' configure
```

### 测试套

recode 的测试套需要 cython 支持，但这是非关键依赖。在 OpenHarmony 上可以跳过测试：

```bash
make check || true  # 可跳过
```

## 依赖关系

### 编译依赖

无特殊依赖，标准 autotools 构建即可。

### 运行依赖

无运行依赖。

## 参考资料

- 官方网站：https://github.com/rrthomas/recode
- GNU 项目页面：https://www.gnu.org/software/recode/
- 源码仓库：https://github.com/rrthomas/recode