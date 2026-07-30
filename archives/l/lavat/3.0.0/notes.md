# lavat 3.0.0 适配笔记

## 编译环境
- 构建系统: makefile（简单 Makefile，非 autotools）
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4 / clang++
- 平台: OpenHarmony aarch64 (musl libc)
- 状态: built

## 编译步骤

1. **下载源码**: 从 GitHub API 下载
   - 实际 URL: `https://api.github.com/repos/AngelJumbo/lavat/tarball/v3.0.0`
   - 原始 URL `https://github.com/angel-pazos/lavat/archive/refs/tags/v3.0.0.tar.gz` 不可用（仓库名错误）
   - tarball SHA256: `bb73fdf5f843b0179660da7f0eb5fcbea847cca8016d173cb27f689b9a439af4`

2. **修改 Makefile**: 添加 DESTDIR 支持（R20 铁律）
   - 将 `$(PREFIX)/bin` 改为 `$(DESTDIR)$(PREFIX)/bin`

3. **编译**: `make PREFIX=/storage/Users/currentUser/usr/local CC=clang CFLAGS="-fPIC -O2"`
   - 输出: `clang lavat.c -o lavat` → 编译成功

4. **安装 (staging)**: `make install PREFIX=/storage/Users/currentUser/usr/local DESTDIR=/storage/Users/currentUser/tmp/test-install-lavat-3.0.0`
   - 安装路径: `$TEST_PREFIX/$DEFAULT_PREFIX/bin/lavat`
   - 安装成功: 1 个二进制文件

5. **安全弹窗验证**: `timeout 2 ~/usr/local/bin/lavat` → 无弹窗，正常退出（退出码 124）

6. **本地安装**: `make install PREFIX=/storage/Users/currentUser/usr/local`
   - 安装到 `$DEFAULT_PREFIX/bin/lavat` → 成功

7. **make check**: 跳过（Makefile 中无 test/check 目标）

8. **打包**: `ohc-run.py package lavat 3.0.0` → 成功生成预编译包

9. **G0 干净构建验证**: 从原始 tarball 解压 + 应用补丁 + 重新编译 → PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub URL `angel-pazos/lavat` 不可达 (连接超时+404) | 仓库实际名为 `AngelJumbo/lavat`（非 `angel-pazos/lavat`） | 通过 GitHub API 搜索找到正确仓库，使用 API tarball URL 下载 |
| 2 | Makefile install 目标不支持 DESTDIR | 原始 Makefile 使用 `$(PREFIX)/bin` 而非 `$(DESTDIR)$(PREFIX)/bin`，违反 R20 铁律 | 补丁修改：`$(PREFIX)/bin` → `$(DESTDIR)$(PREFIX)/bin` |
| 3 | init-build 标记构建系统为 autotools | lavat 实际是简单 Makefile 项目，无 configure 脚本 | 更正 manifest.yaml: `build.system: makefile` 和 `build_system: makefile` |
| 4 | 许可证标记为 GPL-2.0-or-later | 源码仓库实际许可证为 MIT（AngelJumbo/lavat/LICENSE） | 更正 manifest 和 README 中许可证为 MIT |
| 5 | G0 clean-verify 首次失败（安装产物为空） | manifest configure_options 中包含 DESTDIR 路径，导致 G0 传入两个冲突的 DESTDIR 参数 | 移除 DESTDIR 从 configure_options（DESTDIR 是动态安装参数，不应作为静态配置项） |
| 6 | G4 门禁首次失败（manifest 缺少 build_system） | 版本级 manifest 未包含 `build_system` 顶层字段 | 添加 `build_system: makefile` 顶层字段 |

## 源码修改

- **0001-makefile.patch**: 修改 Makefile install 目标
  - 变更: `mkdir -p $(PREFIX)/bin` → `mkdir -p $(DESTDIR)$(PREFIX)/bin`
  - 变更: `install lavat $(PREFIX)/bin/lavat` → `install lavat $(DESTDIR)$(PREFIX)/bin/lavat`
  - 影响: 2 行删除, 2 行新增
  - 分类: platform_only（平台适配补丁，DESTDIR 模式是 OpenHarmony 预编译包必需）

## 依赖版本

无外部依赖。lavat 是纯 C 程序，编译和运行仅依赖：
- musl libc (系统自带)
- clang 15.0.4 (编译器)

## 验证结果

```bash
# 编译产物检查
$ file ~/tmp/builds/lavat-3.0.0.work/lavat
lavat: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

# 动态链接检查
$ readelf -d lavat | grep NEEDED
 0x0000000000000001 (NEEDED)   Shared library: [libc.so]

# Staging 安装检查
$ file ~/tmp/test-install-lavat-3.0.0/storage/Users/currentUser/usr/local/bin/lavat
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

# 本地安装检查
$ file ~/usr/local/bin/lavat
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
$ ls -lh ~/usr/local/bin/lavat
-rwxrwx--- 94K

# 安全弹窗验证
$ timeout 2 ~/usr/local/bin/lavat
退出码: 124 (timeout 正常退出，无弹窗)

# make check（不存在）
$ grep -i "test\|check" makefile
# 无输出（退出码=1），Makefile 没有 test/check 目标
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lavat-3.0.0-ohos-aarch64.tar.gz | 149KB | 预编译主包（含 bin/lavat，已 strip + ELF 签名） |
| lavat-3.0.0-ohos-aarch64-debug.tar.gz | 36KB | debug 符号包 |
| 0001-makefile.patch | 402B | Makefile DESTDIR 适配补丁 (+2/-2) |

## 注意事项

- lavat 是终端图形 demo（lava lamp 模拟），不支持 `--version` 参数，运行时需要终端环境显示动画效果
- 许可证实际为 **MIT**（不是任务描述中的 GPL-2.0-or-later）
- 仓库实际名为 **AngelJumbo/lavat**（不是任务描述中的 angel-pazos/lavat）
- DESTDIR 不应写入 manifest.yaml 的 configure_options，否则会导致 G0 clean-verify 传入两个冲突的 DESTDIR 参数
- lavat 源码仅包含 3 个核心文件: `lavat.c`（18KB）、`makefile`（244B）、`termbox.h`（117KB）
---

**编译结束**: 2026-07-15 16:19
**最终状态**: built
