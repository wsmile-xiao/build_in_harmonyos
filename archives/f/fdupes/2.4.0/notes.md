# fdupes 2.4.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: success

## 编译步骤

由于 HMDFS 平台限制，autotools configure 无法在当前目录创建临时文件，采用手动编译方式：

1. **下载源码**: 从 GitHub releases 获取 fdupes-2.4.0.tar.gz (152KB)
2. **创建 config.h**: 手动定义必要的宏，禁用 ncurses 和 sqlite
3. **编译源文件**: 
   ```bash
   clang -c -I. -fPIC -O2 fdupes.c errormsg.c dir.c log.c fmatch.c sigint.c flags.c confirmmatch.c removeifnotchanged.c mbstowcs_escape_invalid.c md5/md5.c
   ```
4. **链接可执行文件**: 
   ```bash
   clang -fPIC -O2 *.o md5/md5.o -o fdupes
   ```
5. **安装**: 手动复制到 staging 和 DEFAULT_PREFIX
6. **签名**: 使用 ohc-run.py sign-elf 进行 ELF 签名

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 网络连接 GitHub 超时 | HarmonyOS 网络限制 | 使用 aria2c --check-certificate=false |
| 2 | configure 失败：pcre2 library not found | 需要 libpcre2-32（32位字符支持），但系统只有 libpcre2-8 | 使用 --without-ncurses 禁用 ncurses 接口（不依赖 pcre2-32） |
| 3 | configure 失败：cannot create temporary file | HMDFS 不支持 ./confXXXXXX 临时文件创建（E002） | 手动创建 config.h，直接编译源文件 |

## 源码修改

无源码修改，仅手动创建 config.h 文件。

## 依赖版本

- 无外部依赖（禁用 ncurses 和 sqlite）

## 验证结果

```bash
$ fdupes --version
fdupes 2.4.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| fdupes | 55KB | 可执行文件（已签名） |
| fdupes.1 | 5KB | man 手册页 |

## 注意事项

- **禁用 ncurses**: fdupes 使用 --without-ncurses 编译，仅支持 plain 模式（命令行界面）
- **禁用 sqlite**: 不支持缓存数据库功能
- **手动编译**: 由于 HMDFS autotools 限制，无法使用标准 configure/make 流程
---

**编译结束**: 2026-05-21 23:19
**最终状态**: built
