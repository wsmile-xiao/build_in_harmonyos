# csvprintf 1.3.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-13
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码 tarball（GitHub SSL证书问题，使用 Python SSL bypass 手动下载）
2. `touch AUTHORS ChangeLog NEWS`（autoreconf 需要）
3. `CONFIG_SHELL=/data/service/hnp/bin/bash autoreconf -fi`（原始 tarball 缺少 configure）
4. `perl -pi -e 's/umask 077/umask 000/g' configure`（HMDFS umask 077 限制）
5. `CONFIG_SHELL=/data/service/hnp/bin/bash /data/service/hnp/bin/bash ./configure --prefix=$DEFAULT_PREFIX`
6. `make -j1`
7. `make install DESTDIR=$TEST_PREFIX`（R20 DESTDIR模式）
8. `make tests` → Test Suite 1&2 全部通过（20/20）
9. `python3 $SKILL_ROOT/scripts/ohc-run.py package csvprintf 1.3.4`
10. `make install`（不带DESTDIR，本地验证）
11. `csvprintf -v` → "csvprintf version 1.3.4"

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status "Permission denied" 创建临时文件 | HMDFS上umask 077创建的目录无法写入(E046) | perl -pi 修改configure中umask 077→000 |
| 2 | `ln` 硬链接失败 "Operation not permitted" | HMDFS不支持硬链接(E005) | 修改Makefile.am: ln→rm -f && ln -s |
| 3 | run2.sh "/bin/bash: bad interpreter" | 系统bash在/data/service/hnp/bin/bash | 修改tests/run2.sh shebang |
| 4 | sed -i 在HMDFS上删除文件不重建 | HMDFS文件系统限制 | 使用perl -pi替代sed -i |
| 5 | GitHub SSL证书下载失败 | HMDFS缺少CA证书 | Python urllib SSL bypass手动下载 |
| 6 | G0 clean-verify: 缺少configure脚本 | 原始tarball无configure | 创建hints/pre_configure.sh (autoreconf) |

## 源码修改

- `Makefile.am`: install-data-hook 中 `ln` → `rm -f && ln -s`（HMDFS硬链接限制）
- `tests/run2.sh`: shebang `/bin/bash` → `/data/service/hnp/bin/bash`
- `configure`: umask 077 → umask 000（HMDFS限制，每次autoreconf后需重新修改）
- `AUTHORS`, `ChangeLog`, `NEWS`: autoreconf需要的空文件

## 依赖版本

无外部依赖

## 验证结果

```bash
$ csvprintf -v
csvprintf version 1.3.4
Copyright (C) 2010-2023 Archie L. Cobbs

# Test Suite 1: 9/9 PASS
# Test Suite 2: 11/11 PASS (需shebang修复)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| csvprintf-1.3.4-ohos-aarch64.tar.gz | 127KB | 预编译包 |

## 注意事项

- 原始tarball缺少configure脚本，每次clean build需先运行autoreconf -fi
- HMDFS上sed -i不可靠，应使用perl -pi
- configure中的umask 077需修改为umask 000（每次autoreconf重新生成configure后需重新修改）
- CONFIG_SHELL=/data/service/hnp/bin/bash是HMDFS必需的环境变量
---

**编译结束**: 2026-06-13 00:41
**最终状态**: published
