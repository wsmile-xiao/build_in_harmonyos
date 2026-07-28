# atool

## 简介

atool 是一个用于管理多种文件档案格式（tar、tar+gzip、zip 等）的脚本工具。
主命令 `aunpack` 从档案中提取文件，会先提取到新目录避免文件散落；如果档案中
只有单个文件，则将该文件移动到原始目录。`aunpack` 还可防止本地文件被误覆盖。

其他命令包括 `apack`（创建档案）、`als`（列出档案内容）、`acat`（提取文件到
标准输出）。atool 通过调用外部程序处理档案，因此并非所有命令都支持所有档案类型。

atool 通过文件扩展名识别档案格式。当无法通过扩展名识别时（如 rar 档案通常使用
数字扩展名），会使用 `file` 命令识别。atool 使用 Perl 编写。

- **官方网站**: https://www.nongnu.org/atool/
- **项目页面**: https://savannah.nongnu.org/projects/atool/
- **License**: GPL-2.0-or-later
- **Homebrew formula**: https://github.com/Homebrew/homebrew-core/blob/master/Formula/a/atool.rb

## 已编译版本

- **版本**: homebrew（对应上游 0.39.0）

## 编译方式（OHOS）

上游使用 Autotools 构建系统，atool 本身是 Perl 脚本工具，无 C 编译。Homebrew
formula 使用标准的 `./configure --prefix` + `make install` 流程。

OHOS 适配关键点：
1. **configure shebang**: OHOS 无 /bin/sh，将 configure 脚本的 `#! /bin/sh`
   替换为 `#!/system/bin/sh`。
2. **Perl shebang**: atool 的脚本模板使用 `#!@PERL@`，通过设置 `PERL` 环境变量，
   由 configure 将 `@PERL@` 替换为 OHOS 上的 `/data/service/hnp/bin/perl`。
3. **无编译依赖**: atool 是纯 Perl 脚本，构建期无 C 编译，无 Conan 依赖。

```bash
# Conan 构建流程
conan create . --user=ohpcd --channel=stable \
  -pr:h=$HOME/.conan2/profiles/ohos -pr:b=$HOME/.conan2/profiles/ohos \
  --build=missing
```

### OHOS 适配要点

- **configure shebang 修复**: `#! /bin/sh` → `#!/system/bin/sh`（E165）
- **Perl shebang 配置**: 设置 `PERL=/data/service/hnp/bin/perl`，由 configure 替换模板中的 `@PERL@`
- **无 config.guess/config.sub**: atool 的 configure.ac 无 AC_CANONICAL_HOST

详见 `homebrew/notes.md`。

## 依赖

- perl（运行时，OHOS 位于 /data/service/hnp/bin/perl）
- 外部压缩工具：tar、gzip、bzip2、zip、unzip 等（运行时按需调用）

## 安装产物

- `bin/atool` — 主命令
- `bin/aunpack` — 解压档案
- `bin/apack` — 创建档案
- `bin/als` — 列出档案内容
- `bin/acat` — 提取文件到标准输出
- `bin/adiff` — 比较两个档案
- `bin/arepack` — 重新打包档案

## 功能验证

```bash
atool --version        # 查看版本信息
echo "test" > a.txt && apack test.tar.gz a.txt   # 创建档案
als test.tar.gz        # 列出档案内容
```
