# pdf2json 0.71 适配笔记

## 编译环境
- 软件: pdf2json
- 版本: 0.71
- ID: 5547
- 构建系统: autotools
- 语言: C/C++
- 许可证: GPL-2.0-only
- 编译日期: 2026-06-12
- 编译器: clang/clang++ 15.0.4
- 状态: built
- 主页: https://github.com/flexpaper/pdf2json

## 编译步骤

1. **下载**: 从 GitHub codeload 镜像获取源码包 (`pdf2json-0.71.tar.gz`, 1155923 bytes)
2. **init-build**: `ohc-run.py init-build pdf2json 0.71 --url=...`
3. **configure**: E011 umask 022 修复后执行 `./configure --prefix=$DEFAULT_PREFIX`
4. **make**: `make -j1` 编译 goo/fofi/splash/xpdf/src 五个子库
5. **XmlLinks.h 修复**: `sys/unistd.h` → `unistd.h` (编译中途发现并修复)
6. **继续 make**: `cd src && make` 完成 pdf2json 二进制构建
7. **INSTALL 路径修复**: Makefile 中 `/usr/bin/install` → `$DEFAULT_PREFIX/bin/install`
8. **make install DESTDIR=$TEST_PREFIX**: staging 安装
9. **功能验证**: `pdf2json -v`, PDF→JSON 转换测试
10. **make install**: 本地安装验证
11. **ohc-run.py verify-build**: 质量门禁 G1-G4 全部通过
12. **ohc-run.py package pdf2json 0.71**: 预编译包制作 (7385KB)
13. **ohc-run.py finish pdf2json 0.71 published**: 归档收尾 (G0 clean verify 通过)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识匹配 |
|---|------|------|----------|----------|
| 1 | configure config.status Permission denied (can't create subs1.awk) | E011: HMDFS UID映射导致 umask 077 临时目录不可写 | `sed -i 's/umask 077/umask 022/g' configure` | E011 ✅ |
| 2 | src/XmlLinks.h: fatal error: 'sys/unistd.h' file not found | OpenHarmony musl 不提供 sys/unistd.h | `sed -i 's/sys\/unistd.h/unistd.h/g' src/XmlLinks.h` | 新发现 |
| 3 | make install: /usr/bin/install No such file or directory | Makefile 稺编码了 /usr/bin/install | `sed -i 's|/usr/bin/install -c|$DEFAULT_PREFIX/bin/install -c|g' Makefile` | 平台特有 |
| 4 | 下载超时: GitHub URL 无法直接访问 | 网络限制 | 使用 codeload.github.com 镜像下载 | 网络问题 |

## 源码修改 (2 处补丁 + 1 处 conanfile.py)

- `configure`: umask 077 → 022 (E011 HMDFS 权限修复) → 0002-configure.patch
- `src/XmlLinks.h`: `#include <sys/unistd.h>` → `#include <unistd.h>` (平台头文件适配) → 0003-src-XmlLinks.h.patch
- `Makefile`: 原 0001-Makefile.patch 已移除, INSTALL 路径问题改由 conanfile.py package() 手动拷贝产物解决

## 补丁列表 (2 个)

| 补丁 | 修改文件 | 类型 | 说明 |
|------|----------|------|------|
| 0002-configure.patch | configure | platform | E011: umask 077→022 |
| 0003-src-XmlLinks.h.patch | src/XmlLinks.h | platform | sys/unistd.h→unistd.h |

## 依赖版本

无外部依赖. pdf2json 基于 XPDF 3.02 内置库 (Goo/fofi/splash/Xpdf), 所有库在源码树内部构建, 无需预编译包.

## 验证结果

### 版本信息
```
$ pdf2json -v
pdf2json version 0.70 http://flexpaper.devaldi.com/pdf2json/, based on Xpdf version 3.02
```

### 功能验证: PDF→JSON
```
$ pdf2json si.pdf si.js   # 20页PDF→145KB JSON, 退出码0
$ python3 -c "import json; data=json.load(open('si.js', encoding='latin-1')); print(len(data))"
# 输出: 20
```

### 压缩模式
```
$ pdf2json -compress si.pdf compress.js   # 55KB (压缩比38.3%)
```

### 页范围
```
$ pdf2json -f 1 -l 3 si.pdf pages.js   # 仅3页
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pdf2json-0.71-ohos-aarch64.tar.gz | 7,562,389 bytes (7.2MB) | 预编译包 (含6二进制+配置+文档) |
| pdf2json-0.71-ohos-aarch64-debug.tar.gz | 1,156,806 bytes (1.1MB) | 调试符号包 |

### 预编译包内容
```
bin/pdf2json     (1,206,208 bytes)
bin/pdftops      (1,431,488 bytes)
bin/pdftotext    (1,271,744 bytes)
bin/pdfinfo      (1,198,016 bytes)
bin/pdffonts     (1,198,016 bytes)
bin/pdfimages    (1,202,112 bytes)
etc/xpdfrc       (配置文件)
man/man1/*.1     (5个man页面)
man/man5/xpdfrc.5 (1个man页面)
lib/external/    (空目录)
```

## 注意事项

- pdf2json 版本字符串显示为 "0.70" (代码内硬编码), 实际为 0.71 tag 版本
- 编译产生大量 ISO C++11 writable-strings 警告, 不影响功能
- 无 make check 测试套件, 通过手动功能验证确认正确性
- 预编译包包含6个二进制: pdf2json(核心) + pdftops/pdftotext/pdfinfo/pdffonts/pdfimages(XPDF工具集)
- JSON 输出编码为 latin-1, UTF-8 解析可能失败, 需指定 encoding='latin-1'
- Makefile INSTALL 路径问题原通过 0001-Makefile.patch 修复, 现已移除该补丁, 改由 conanfile.py package() 手动拷贝产物解决
- configure.ac 中 AC_CHECK_LIB 检查的 Goo/Xpdf/fofi/splash 为内部库, 不需预安装

**编译结束**: 2026-07-24 11:40
**最终状态**: built
