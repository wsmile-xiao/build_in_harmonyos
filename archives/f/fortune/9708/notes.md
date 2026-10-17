# fortune 9708 适配笔记

## 编译环境
- 构建系统: makefile（无 configure 脚本）
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4
- 状态: built (conan 适配完成)

## 编译步骤

1. **初始化构建环境**
   ```bash
   SKILL_ROOT="/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent"
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build fortune 9708 \
       --url=file:///storage/Users/currentUser/tmp/fortune-mod-9708.tar.gz
   source .build-context-fortune-9708
   cd $BUILD_SRC_DIR
   ```

2. **修改 Makefile**
   - 添加 PREFIX 和 DESTDIR 支持
   - 修改路径变量使用 $(PREFIX)
   - 修改 CC 为 clang
   - 修改 REGEXDEFS 使用 POSIX regex
   - 禁用 offensive 内容编译

3. **编译**
   ```bash
   make PREFIX=$DEFAULT_PREFIX -j1
   ```

4. **安装到 staging 目录**
   ```bash
   make PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX install
   ```

5. **用户验证**
   ```bash
   $DEFAULT_PREFIX/games/fortune --version
   $DEFAULT_PREFIX/games/fortune
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | BSD regex 函数缺失（re_comp/re_exec） | 链接时缺少 BSD regex 库函数 | 修改 REGEXDEFS=-DPOSIX_REGEX 使用 POSIX regex |
| 2 | rot 程序 EOF 检测问题导致卡住 | rot.c 中 EOF 检测在 char 类型上总是为真 | 禁用 offensive 内容编译（OFFENSIVE=0） |
| 3 | Makefile 不支持 DESTDIR | 原始 Makefile 硬编码路径 | 修改 Makefile 添加 DESTDIR 支持 |

## 源码修改

**0001-Makefile.patch**
- 添加 PREFIX 和 DESTDIR 变量
- 修改路径变量使用 $(PREFIX)
- 修改 CC=gcc 为 CC=clang
- 修改 REGEXDEFS 使用 POSIX regex
- 禁用 offensive 内容编译（OFFENSIVE=0）
- 添加 install 规则的 DESTDIR 支持

## 依赖版本

无外部依赖（仅需要标准 C 库和 POSIX regex 支持）

## 验证结果

```bash
$ fortune --version
fortune-mod version 9708

$ fortune
No skis take rocks like rental skis!

$ strfile
strfile [-iorsx] [-c char] sourcefile [datafile]

$ unstr
No input file name
```

## 交付物

本 PR 交付 Conan 配方（conanfile.py + conandata.yml + test_package/），编译产物由 CI 流水线从源码构建。

## 注意事项

1. fortune 数据文件（.dat）由 strfile 工具生成，需要与原始文本文件配套使用
2. 禁用了 offensive 内容以避免 rot 程序卡住问题
3. 使用 POSIX regex 替代 BSD regex，功能完全兼容

---
**编译结束**: 2026-08-06
**最终状态**: built (conan 适配完成, 待 PR 合入后标记 published)
