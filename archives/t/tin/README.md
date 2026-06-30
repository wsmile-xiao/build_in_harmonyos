# tin - 新闻阅读器（NNTP client）

## 简介
tin 是一个功能强大的文本模式新闻阅读器（NNTP client），支持：
- 多新闻服务器连接
- MIME 支持（base64、qp 编码）
- 多语言界面（da, de, en_GB, es, et, fr, ru, sv, tr, zh_CN, zh_TW）
- 线程化阅读
- 搜索和过滤功能
- PGP/GPG 支持
- NNTPS（SSL/TLS）支持

## 编译信息
- 版本：2.6.4
- 构建系统：autotools
- 平台：HarmonyOS (OpenHarmony) aarch64
- 编译器：clang 15.0.4
- 状态：built

## 使用方法
安装预编译包后，运行：
```bash
tin -r news.example.com
```

常用选项：
- `-r` 指定新闻服务器
- `-f` 指定新src文件
- `-n` 只读模式

## 依赖
- ncurses >= 6.4（终端库，用于屏幕显示）
- icu4c >= 77（Unicode 转换库，用于字符编码）
- zlib（系统内置，用于压缩支持）

## 已知问题
- HarmonyOS 上需要 /etc/passwd 文件才能正常运行（平台限制）
- 缺少 termcap/terminfo 数据库可能导致部分终端功能受限

## 源码
- 官方主页：https://www.tin.org/
- 下载地址：http://ftp.icm.edu.pl/packages/tin/

## 版权
tin 采用 BSD-like 许可证，详见源码中的版权声明。
