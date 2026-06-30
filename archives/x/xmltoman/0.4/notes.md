# xmltoman 0.4 适配笔记

# 编译环境
- 构建系统: makefile（简单 Makefile，非 autotools）
- 编译日期: 2026-06-11
- 编译器: clang/clang++（实际未使用——xmltoman 是纯 Perl 脚本工具）
- Perl 版本: v5.42.2 (harmonyos-thread-multi)
- XML::Parser 版本: 2.59（通过 CPAN 安装）
- 状态: published

# 编译步骤

1. 初始化编译环境：`python3 $SKILL_ROOT/scripts/ohc-run.py init-build xmltoman 0.4 --url=...`
2. 安装运行时依赖 XML::Parser Perl 模块（通过 CPAN 安装，依赖 expat 库）
3. 修复 shebang 路径：将 `#!/usr/bin/perl -w` 改为 `#!/storage/Users/currentUser/usr/local/bin/perl -w`
4. 构建 man 页面：`make PREFIX=$DEFAULT_PREFIX`
5. DESTDIR 安装：`make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX`
6. 预编译包制作：`python3 $SKILL_ROOT/scripts/ohc-run.py package xmltoman 0.4`
7. 本地安装验证：`make install PREFIX=$DEFAULT_PREFIX`（不带 DESTDIR）
8. 质量门禁验证：`python3 $SKILL_ROOT/scripts/ohc-run.py verify-build xmltoman 0.4`
9. 收尾：`python3 $SKILL_ROOT/scripts/ohc-run.py finish xmltoman 0.4 published`

# 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识图谱关联 |
|---|------|------|----------|------------|
| 1 | xmltoman/xmlmantohtml 脚本无法执行 | shebang `#!/usr/bin/perl` 指向不存在的路径 | 修改为 `#!/storage/Users/currentUser/usr/local/bin/perl -w` | E049, E105(draft) |
| 2 | XML::Parser Perl 模块缺失 | xmltoman 运行需要 XML::Parser 模块 | 通过 CPAN 安装 XML::Parser 2.59（需先有 expat 库） | 本版特有 |
| 3 | Python3 无法启动（libintl.so.8 缺失） | musl 系统不自动加载 python.org lib 目录 | 设置 LD_LIBRARY_PATH 包含 `/data/service/hnp/python.org/python_3.12/lib` | 环境问题 |
| 4 | G4 门禁首次失败 | manifest 缺少 `build_system` 字段 | 添加 `build_system: makefile` 字段 | 流程问题 |
| 5 | 构建系统标注错误 | 原标注 autotools，实际是简单 Makefile | 更正为 `system: makefile` | R15 历史纠错 |

# 源码修改

- **0001-xmlmantohtml.patch**: 修复 xmlmantohtml 的 Perl shebang 路径（`#!/usr/bin/perl` → `#!/storage/Users/currentUser/usr/local/bin/perl -w`）
- **0002-xmltoman.patch**: 修复 xmltoman 的 Perl shebang 路径（`#!/usr/bin/perl -w` → `#!/storage/Users/currentUser/usr/local/bin/perl -w`）

# 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| Perl | 5.42.2 (harmonyos-thread-multi) | 系统预装（~/usr/local/bin/perl） |
| XML::Parser | 2.59 | CPAN 安装 |
| expat | 2.7.3 | 系统预编译（~/usr/local/lib） |
| xsltproc | (libxslt) | 系统预装（xmlmantohtml 可选依赖） |

# 功能验证结果

```bash
# xmltoman 基本功能验证
$ /storage/Users/currentUser/usr/local/bin/xmltoman xml/xmltoman.1.xml
.TH xmltoman 1 User Manuals
.SH NAME
xmltoman \- xml to man converter
...
# ✅ 正确输出 man page 格式，退出码 0

# xmlmantohtml 功能验证
$ /storage/Users/currentUser/usr/local/bin/xmlmantohtml xml/xmlmantohtml.1.xml
<body text="#000000" ...><table width="80%">
...
# ⚠️ 正确输出 HTML 格式，有 Perl 良性警告，退出码 0

# 错误处理验证
$ /storage/Users/currentUser/usr/local/bin/xmltoman
You need to specify a file to parse
# ✅ 退出码 1

$ /storage/Users/currentUser/usr/local/bin/xmlmantohtml
You need to specify a file to parse
# ✅ 退出码 1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| xmltoman-0.4-ohos-aarch64.tar.gz | 21KB (21527 bytes) | 预编译包（内含 bin/ 和 share/xmltoman/ 目录） |
| 0001-xmlmantohtml.patch | 616 bytes | shebang 路径修复补丁 |
| 0002-xmltoman.patch | 604 bytes | shebang 路径修复补丁 |

# 注意事项

- xmltoman 是纯 Perl 脚本工具，无 ELF 二进制文件，无需编译（仅需修复 shebang 路径）
- 运行时依赖：需要 Perl + XML::Parser 模块 + expat 库
- xmlmantohtml 运行时有 Perl 良性警告（`Name "main::opt" used only once`），属于上游代码质量问题，不影响功能
- 质量门禁 G2 显示 ⚠️1（Perl 脚本无 --version 输出），属正常现象
- 知识图谱草稿 E105 已创建：记录 Perl 脚本 shebang 路径修复模式

---

**编译结束**: 2026-06-11 03:06
**最终状态**: published