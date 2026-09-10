# comprez 2.7.3 适配笔记

## 编译环境
- 构建系统: makefile（纯 shell 脚本工具，无编译）
- 编译日期: 2026-09-08
- 编译器: N/A（z/zzcat 为 /bin/sh 脚本，无 C/C++ 编译需求）
- 状态: published

## 软件简介
comprez（上游项目名 z，Debian 包装名 comprez）是 Steve Kinzler 编写的压缩/解压前端工具：
`z SOMETHING` 会根据文件/目录类型自动选择合适的 compress/gzip/bzip2/lzip/xz/zip/tar 组合，
提供 `z -gz/-I/-lz/-xz/-Z/-zip` 等压缩格式选项与 `-t/-T/-v/-l/-L` 等操作选项。
上游仓库：https://kinzler.com/me/z/（源码 tarball：z-2.7.3.tgz）

## 编译步骤
1. 下载并解压上游源码包 z-2.7.3.tgz（7 个文件：z、zzcat、Makefile、README、z.man、z.html、COPYING）
2. lang-preflight 语言预检通过（detected=c，Makefile 顶层 manifest，c↔cpp 兼容族）
3. staging 隔离安装：`cp z zzcat → bin/，cp z.man → man/man1/`（Makefile 的 install 目标是绝对路径 /usr/local/bin，不支持 DESTDIR，故直接手动 staging）
4. 功能验证：gzip(.tgz)/bzip2(.tbz2)/xz(.txz)/zip(.zip) 压缩解压、zzcat 解压、z -t 列表，全部通过

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | z/zzcat 硬编码 `/tmp/z$$` 临时文件 | HarmonyOS `/tmp` 只读文件系统 | 改用 `${TMPDIR:-${HOME:-/tmp}/tmp}` 并 mkdir -p（补丁 0001-z.patch / zzcat） |
| 2 | z 解压 `.tgz`/`.tar.z` 时 `gzip -d -n file.z` 失败 | HarmonyOS gzip 为 toybox 0.8.12，只识别 `.gz` 后缀 | 解压调用改为 `gzip -d -n -c "$arg" > "$tarf"` 管道输出（补丁 0001-z.patch），失败时回退原命令 |
| 3 | 上游无测试套件 | 上游仅脚本+man 页，无 make check | 自研 test_package 功能测试（gzip/bzip2/xz/zip 压缩解压、zzcat、-t 列表） |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|----------------|
| z | ① tmp 临时目录改为 ${TMPDIR:-$HOME/tmp} ② gzip 解压改 -c 管道输出兼容 toybox | ✅ 0001-z.patch |
| zzcat | tmp 临时目录改为 ${TMPDIR:-$HOME/tmp} | ✅ 0002-zzcat.patch |

## 依赖版本
- 运行时依赖（系统命令，非 conan 依赖）：gzip(toybox 0.8.12)、bzip2、xz、tar、zip、unzip
- 可选后端（未适配，缺失不影响主功能）：lzip、compress

## 验证结果
```bash
z -gz -L dir    # → dir.tgz，压缩成功
z docs.tgz      # → 解压恢复目录，内容 diff 一致 ✅
z -t docs.tgz   # → tar 列表正常 ✅
z -I -L dir     # → dir.tbz2（bzip2）✅
z -xz .../docs.txz  # → xz 解压 ✅
z -zip 文件     # → zip 压缩/解压 ✅
zzcat file.gz   # → 解压到 stdout ✅
```
全部通过（详见 test_package 测试）。

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| z / zzcat | 15KB / 2KB | 可执行 shell 脚本（bin/） |
| z.1 | 12KB | man 手册（share/man/man1/） |

## 注意事项
- comprehend 是纯脚本工具，conan 包仅打包脚本+man 页，无编译产物
- 首次执行命令时鸿蒙可能弹出安全确认窗口
- lzip/compress 后端为可选能力，HarmonyOS 默认不含，使用 `-lz/-Z` 时需系统自带对应命令
- 已合入同生态先例：help2man（纯 Perl 脚本，build_system: script，published）---

**编译结束**: 2026-09-08 14:50
**最终状态**: built
---

**编译结束**: 2026-09-08 15:33
**最终状态**: published
