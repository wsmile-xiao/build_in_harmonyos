# libmetalink 0.1.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-10
- 编译器: clang 15.0.4 / clang++
- 目标平台: aarch64-unknown-linux-ohos (HarmonyOS / HongMeng Kernel 1.12.0)
- 状态: built（待升级为 published）

## 编译步骤

1. **初始化**: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build libmetalink 0.1.3 --url=...`
2. **替换 config.guess/config.sub**: 使用 automake-1.17 的新版文件替换旧版（2014），支持识别 `aarch64-unknown-linux-ohos`
3. **修补 configure 中的 umask**: 将 `umask 077` 改为 `umask 002`，解决 HMDFS setgid 目录下的临时文件权限问题
4. **编译**: `umask 002 && ./configure --prefix=$DEFAULT_PREFIX && make -j1`
5. **安装**: `make install DESTDIR=$TEST_PREFIX`（DESTDIR 模式）
6. **测试**: `make check` → TOTAL=0（CUnit 缺失，无可用测试套件）
7. **本地安装**: `make install`（不带 DESTDIR）
8. **版本验证**: `pkg-config --modversion libmetalink` → 0.1.3

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| P1 | `config.guess: unable to guess system type` | 旧版 config.guess (2014) 无法识别 HarmonyOS (aarch64) | 替换为 automake-1.17 新版，识别为 `aarch64-unknown-linux-ohos` |
| P2 | `can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 目录有 setgid 位，当前用户通过组权限访问；config.status 使用 `umask 077 && mktemp -d` 创建临时目录，剥夺组写权限 | 修改 configure 脚本中两处 `umask 077` → `umask 002`（影响 config.status 临时目录创建） |
| P3 | G0 clean-verify `Invalid configuration '[]'` | manifest.yaml 中 `configure_options: []`（YAML 空列表）被脚本正则解析为字符串 `"[]"`，传给 configure 作为参数 | 修改 manifest.yaml：将 `configure_options: []` 改为 `configure_options:`（不带方括号） |
| P4 | 首次补丁策略违规（R6） | config.status.patch 修改了生成文件（config.status 由 configure 生成），在 G0 干净构建时无法生效 | 删除 config.status.patch，改为修补 configure 脚本本身（源文件级别修改） |

## 源码修改

3 个补丁文件：

| 补丁 | 修改文件 | 内容 |
|------|----------|------|
| 0001-config.guess.patch | config.guess | 替换为 automake-1.17 新版，支持 HarmonyOS 平台识别 |
| 0002-config.sub.patch | config.sub | 替换为 automake-1.17 新版，支持 `linux-ohos` 三段式系统类型 |
| 0003-configure.patch | configure | 将两处 `umask 077` 改为 `umask 002`，解决 HMDFS setgid 目录临时文件权限问题 |

## 依赖版本

- 无编译依赖（libmetalink 是纯 C 库）
- 运行时依赖: expat（系统已预装，configure 通过 `-lexpat` 链接）
- 测试依赖: CUnit（未安装，测试套件为空）

## 验证结果

```bash
# pkg-config 版本
PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig pkg-config --modversion libmetalink
# → 0.1.3 ✅

# pkg-config 库路径
PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig pkg-config --libs libmetalink
# → -L/storage/Users/currentUser/usr/local/lib -lmetalink ✅

# 动态库依赖
llvm-readelf -d $DEFAULT_PREFIX/lib/libmetalink.so.3.1.0 | grep NEEDED
# → libexpat.so, libc.so ✅

# G0 干净构建验证
# → PASS ✅

# G1-G4 质量门禁
# → 全部 PASS ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmetalink-0.1.3-ohos-aarch64.tar.gz | 689KB | 预编译包（含动态库+静态库+头文件+pkg-config） |
| libmetalink-0.1.3-ohos-aarch64-debug.tar.gz | 214KB | 调试符号包 |

## 注意事项

1. **HMDFS umask 问题**: 在 HarmonyOS 的 HMDFS 文件系统上，autotools 项目 config.status 内部使用 `umask 077 && mktemp -d` 创建临时目录时，会剥夺目录的组写权限。由于 HMDFS 目录使用 setgid 位管理组归属，且当前用户通过组权限访问源码目录，这导致 config.status 无法在临时目录中创建 awk 脚本文件。解决方式是修改 configure 中对应位置为 `umask 002`。
2. **CUnit 缺失**: libmetalink 的测试套件完全依赖 CUnit 框架，无 CUnit 时 TOTAL=0。这不阻塞编译发布。
3. **configure_options YAML 格式**: 在 manifest.yaml 中，`configure_options: []`（YAML 空列表）会被 clean-verify 脚本误解析为字符串 `"[]"`，导致 configure 报错。应使用 `configure_options:` （不带方括号）避免此问题。

---

**编译结束**: 2026-06-11
**最终状态**: built
---

**编译结束**: 2026-06-11 14:16
**最终状态**: published
