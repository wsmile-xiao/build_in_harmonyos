# fig2dev 3.2.9a 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06 (conan 适配)
- 首次编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `python3 $SKILL_ROOT/scripts/ohc-run.py init-build fig2dev 3.2.9a` - 成功
2. 应用补丁: 0001-configure.patch (umask 077→022, E050)
3. `./configure --prefix=$DEFAULT_PREFIX` - 成功
4. `make -j2` - 成功
5. `make install DESTDIR=$TEST_PREFIX` - 成功
6. 验证: `fig2dev --version` → Version 3.2.9a
7. `make check` - 85 tests, 6 failed (platform limits), 29 skipped

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status Permission denied | HMDFS umask 077创建临时目录权限不足(E050) | 补丁: configure中umask 077→022 |
| 2 | 6 test failures (tests 15,17,19,20,77,78) | 缺少gzip/compress工具(15,17,19,20)和ghostscript(77,78) | 平台限制，非代码问题 |

## 源码修改

- `configure` — umask 077→022 (0001-configure.patch)

## 依赖版本

- zlib/1.3.1 (Conan 制品仓)

## Conan 适配 (2026-08-06)

### conanfile.py
- package_type: application (命令行工具)
- 依赖: zlib/1.3.1
- 构建系统: Autotools (configure + make)
- test_package: 执行 fig2dev --version 验证

### conandata.yml
- 源码 URL: https://github.com/deepin-community/fig2dev/archive/9c859195f06e88c3337f991342b9da524dcff0c6.tar.gz
- SHA256: 8c98c28f30e41d621022c15786c9ce8dbea84f09facffe7a9fc57556e2835911
- 补丁: 0001-configure.patch (portability)

### commands.json
- 已创建 (R38): fig2dev 为命令行工具

## 验证结果

```bash
$TEST_PREFIX/.../bin/fig2dev --version
fig2dev Version 3.2.9a
```

## 注意事项

- 缺少libpng支持(configure中检测到png_read_info=no)，图象输出PNG功能受限
- 缺少ghostscript(gs)，EPS输出受限
- 源码来自deepin-community fork (Deepin发行版社区维护，非个人fork)
---

**编译结束**: 2026-08-06 11:18
**最终状态**: built
