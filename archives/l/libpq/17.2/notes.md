# libpq 17.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 修复 config.guess/config.sub：
   - 使用 patch-autotools-ohos.pl 补丁脚本
   - 手动添加 `linux-ohos*` 到 config.sub 内核验证列表

2. 运行 configure：
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX --without-readline --without-zlib --without-icu
   ```

3. 编译 libpq：
   ```bash
   cd src/interfaces/libpq && make -j2 && make install DESTDIR=$TEST_PREFIX
   ```

4. 配置时临时目录权限问题：
   - 修改 config.status 使用 `$HOME/tmp/confwork` 作为临时目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 脚本不包含 HarmonyOS 检测分支 | 使用 patch-autotools-ohos.pl 补丁 |
| 2 | Invalid configuration 'aarch64-unknown-linux-ohos' | config.sub 内核列表缺少 linux-ohos* | 手动修改 config.sub |
| 3 | config.status 无法创建临时文件 | 源码目录所在文件系统限制 | 修改 config.status 使用 $HOME/tmp |
| 4 | ICU library not found | libpq 不需要 ICU | 使用 --without-icu 禁用 |

## 源码修改

修改的文件：
- config/config.guess: 使用补丁脚本添加 HarmonyOS 检测
- config/config.sub: 添加 linux-ohos* 到内核验证列表
- configure: 修改临时目录从 ./confXXXXXX 改为 $TMPDIR/confXXXXXX

## 依赖版本

无额外依赖（--without-readline, --without-zlib, --without-icu）

## 验证结果

```bash
# 检查编译产物
ls -la $TEST_PREFIX/$DEFAULT_PREFIX/lib/libpq.*
# libpq.so.5.17, libpq.so.5, libpq.so, libpq.a
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libpq.so.5.17 | 318K | 共享库 |
| libpq.a | 248K | 静态库 |

## 注意事项

libpq 是 PostgreSQL 的客户端库，仅包含客户端功能，不包含服务器组件。
---

**编译结束**: 2026-05-27 03:27
**最终状态**: built
