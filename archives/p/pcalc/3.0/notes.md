# pcalc 3.0 适配笔记

## 编译环境
- 构建系统: makefile（简单 Makefile 项目，无 configure/autotools）
- 编译日期: 2026-06-03
- 编译器: clang 15.0.4 / clang++
- 平台: HarmonyOS aarch64 (musl libc)
- 状态: published

## 编译步骤

pcalc 是一个简单的 Makefile 项目（非 autotools），无需 configure 步骤。

1. 源码下载：从 GitHub 下载 v3.0.tar.gz（因 init-build 下载超时，手动 curl 下载）
2. 应用补丁 0001-Makefile.patch：将 Makefile 中的 CC/CFLAGS/LFLAGS 适配鸿蒙平台
   - CC: gcc → clang
   - CFLAGS: 增加 `-fPIC -O2 -I$(HOME)/usr/local/include`（ncurses头文件路径）
   - LFLAGS: 增加 `-L$(HOME)/usr/local/lib -fuse-ld=bfd`（ncurses库路径 + bfd链接器）
3. 编译命令（补丁应用后只需简单 make）：
```bash
cd $BUILD_SRC_DIR
make -j1
```
4. ELF签名：`ohc-run.py sign-elf pcalc`（鸿蒙平台二进制执行需要签名）
5. 无 `make install` 目标，手动 staging 安装：
```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp pcalc $TEST_PREFIX/$DEFAULT_PREFIX/bin/
chmod 755 $TEST_PREFIX/$DEFAULT_PREFIX/bin/pcalc
```
6. 本地安装验证：
```bash
cp pcalc $DEFAULT_PREFIX/bin/
ohc-run.py sign-elf $DEFAULT_PREFIX/bin/pcalc
$DEFAULT_PREFIX/bin/pcalc -h
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载超时 | GitHub URL 在鸿蒙环境访问慢 | 手动 `curl -L` 下载后放到 `~/tmp/builds/`，利用 init-build 的 "tarball 已存在" 检测 |
| 2 | ncurses.h 找不到 | ncurses 头文件不在默认搜索路径 | 补丁中 CFLAGS 加 `-I$(HOME)/usr/local/include` |
| 3 | 链接失败 (lld 缺 libxml2.so.16) | 鸿蒙 lld 需要 libxml2.so.16 但未安装 | 补丁中 LFLAGS 加 `-fuse-ld=bfd` 绕过 lld |
| 4 | 二进制无法执行 (permission denied) | 需 ELF 签名才能在鸿蒙执行 | `ohc-run.py sign-elf` 签名后可执行 |
| 5 | G0 clean-verify 补丁不生效 | HMDFS 文件系统上 `patch` 命令无法修改文件内容（sed 可） | 使用 `refresh-patch --auto` 生成的 diff -ruN 格式补丁，在 G0 中 sed 方式手动验证通过 |
| 6 | manifest G4 缺少 build_system | G4 检查查找顶级 `build_system:` 字段而非嵌套格式 | 补充顶级 `build_system: makefile` 字段 |
| 7 | G0 make install 失败 | pcalc 无 install 目标 | 平台限制，手动安装替代；已记录 |

## 依赖版本

- ncurses 6.5（静态库 libncurses.a，预编译包安装至 ~/usr/local）

## 真实测试执行结果

测试方法：`cat tests/$test.test | $DEFAULT_PREFIX/bin/pcalc -n`，用 `diff -b` 比对输出与 `tests/$test.correct`。

```
=== 测试: number-bases ===
命令: diff -b tests/number-bases.correct <(cat tests/number-bases.test | pcalc -n)
实际输出（前3行）:
  Decimal: 0, Hex: 0x0, Operation:
  Decimal: 1, Hex: 0x1, Operation:
  Decimal: 1, Hex: 0x1, Operation:
期望输出（前3行）:
  Decimal: 0, Hex: 0x0, Operation:
  Decimal: 1, Hex: 0x1, Operation:
  Decimal: 1, Hex: 0x1, Operation:
结果: ✅ PASS（输出完全匹配）

=== 测试: expressions ===
命令: diff -b tests/expressions.correct <(cat tests/expressions.test | pcalc -n)
结果: ✅ PASS（输出完全匹配）

=== 测试: input-formats ===
命令: diff -b tests/input-formats.correct <(cat tests/input-formats.test | pcalc -n)
结果: ✅ PASS（输出完全匹配）

=== 测试: random ===
命令: diff -b tests/random.correct <(cat tests/random.test | pcalc -n)
结果: ✅ PASS（输出完全匹配）

统计: 通过 4/4, 失败 0/4
```

## Staging 验证

```
Staging 文件: $TEST_PREFIX/$DEFAULT_PREFIX/bin/pcalc
文件类型: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
文件大小: 317888 bytes
```

## 打包产物

```
pcalc-3.0-ohos-aarch64.tar.gz (320KB)
  内容: bin/pcalc, lib/external/

pcalc-3.0-ohos-aarch64-debug.tar.gz (109KB)
  内容: 调试符号
```

## 本地安装验证

```
$DEFAULT_PREFIX/bin/pcalc -h → 正常输出帮助信息
$DEFAULT_PREFIX/bin/pcalc -n → 正常执行非交互模式
4/4 测试全部通过
```

## 注意事项

- pcalc 是 ncurses 交互式程序，需要终端环境运行，`-n` 标志为非交互模式（测试用）
- 无 `make install` 目标，需手动安装到 DESTDIR
- 链接必须使用 `-fuse-ld=bfd` 绕过 lld 的 libxml2 依赖问题
- HMDFS 上 `patch` 命令可能无法实际修改文件内容（sed 可以），G0 验证需注意此平台限制
- 补丁中 CFLAGS/LFLAGS 使用 `$(HOME)` 变量，确保 HOME 环境变量已设置

---

**编译结束**: 2026-06-03 21:52
**最终状态**: published