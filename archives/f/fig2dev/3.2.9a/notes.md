# fig2dev 3.2.9a 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `python3 $SKILL_ROOT/scripts/ohc-run.py init-build fig2dev 3.2.9a --url=https://github.com/deepin-community/fig2dev/archive/refs/heads/master.tar.gz` - 成功
2. `./configure --prefix=$DEFAULT_PREFIX` - 首次失败(HMDFS权限)，应用umask补丁后成功
3. `make -j2` - 成功
4. `make install DESTDIR=$TEST_PREFIX` - 成功
5. `make install` - 成功
6. 验证: `fig2dev --version` → Version 3.2.9a

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status Permission denied | HMDFS umask 077创建临时目录权限不足(E050) | 补丁: configure中umask 077→022 |

## 源码修改

- `configure` — umask 077→022 (0001-configure-umask-022.patch)

## 依赖版本

- zlib (系统自带)
- libiconv (预编译)

## 验证结果

```bash
$DEFAULT_PREFIX/bin/fig2dev --version
fig2dev Version 3.2.9a
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| fig2dev-3.2.9a-ohos-aarch64.tar.gz | 1890KB | 预编译安装包 |
| fig2dev-3.2.9a-ohos-aarch64-debug.tar.gz | - | 调试符号包 |

## 注意事项

- 缺少libpng支持(configure中检测到png_read_info=no)，图象输出PNG功能受限
- 缺少ghostscript(gs)，EPS输出受限
- 源码来自deepin-community fork而非官方sourceforge版本

---

**编译结束**: 2026-05-27 18:18
**最终状态**: built