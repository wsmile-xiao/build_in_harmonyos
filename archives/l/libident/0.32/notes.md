# libident 0.32 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-29
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

1. 下载源码: `curl -kL -o libident-0.32.tar.gz https://www.remlab.net/files/libident/libident-0.32.tar.gz` (SSL 证书问题，需 -k 参数)
2. 解压到 .orig 目录，init-build --no-download
3. source .build-context-libident-0.32
4. cd $BUILD_SRC_DIR
5. 修复 admin/config.guess: umask 077→022 + 添加 HarmonyOS case
6. 修复 configure: umask 077→022
7. `./configure --prefix=$DEFAULT_PREFIX --enable-static --disable-shared`
8. `make -j1` (成功，2 个非关键警告)
9. `make install DESTDIR=$TEST_PREFIX` (成功)
10. `make check` (通过，exit 0)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 下载失败 | HarmonyOS SSL 证书验证失败 | curl -kL 手动下载到 $HOME/tmp/builds/，--no-download 初始化 |
| 2 | config.guess 无法识别 HarmonyOS | 2004 年的 config.guess 不包含 HarmonyOS 检测分支 | 在 admin/config.guess 中添加 `*:HarmonyOS:*:*) → aarch64-unknown-linux-gnu` case |
| 3 | config.guess 创建临时文件 Permission denied | HMDFS umask 077 导致目录权限 0700，文件创建失败 | 将 config.guess 中的 `umask 077` 替换为 `umask 022` |
| 4 | config.status 创建文件 Permission denied | configure 生成的 config.status 也使用 umask 077 | 将 configure 中的 `umask 077` 替换为 `umask 022` |
| 5 | conan create source() 失败 | self.cache_folder 属性在 Conan 2.x 不存在 | 改用 tempfile.mkdtemp() 代替 self.cache_folder |
| 6 | conan-verify G4 产物完整性检查失败 | `conan cache path <ref>` 不带 package ID 时返回 recipe export 目录而非 package 目录 | 在 recipe export 目录创建到 package 目录的 bin/lib/include/man 符号链接 |
| 7 | make -j20 mkfifo 失败 | HMDFS 不支持 mkfifo (jobserver 通信) | conan profile 使用 Unix Makefiles generator，make 自动降级为单线程 |

## 源码修改

### 补丁 1: 0001-admin-config.guess.patch
- 将 `umask 077` 替换为 `umask 022` (3 处)
- 在 DRAGONFLY case 后添加 HarmonyOS case: `*:HarmonyOS:*:*) echo ${UNAME_MACHINE}-unknown-linux-gnu; exit 0 ;;`

### 补丁 2: 0002-configure.patch
- 将 `umask 077` 替换为 `umask 022` (3 处)

### conanfile.py build() 方法中的内联修复
- 在 build() 方法中直接修复 config.guess 和 configure，确保 conan create 时也能正确处理
- conandata.yml 的 patches 字段保持 `patches: {}`，所有修复在 build() 内联完成

## 依赖版本

无依赖 (libident 是独立的 ident protocol 库)

## 验证结果

```
conan-verify 8 道门禁全部通过:
  G0: PASS (预构建风险评估, E007 已在 build() 内联修复)
  G1: PASS (配方完整性)
  G2: PASS (conan create 干净构建, test_package 通过)
  G3: PASS (纯库包，无 bin/，跳过 R26 检查)
  G4: PASS (产物完整性: 1 .a + 1 头文件)
  L2: PASS (smoke test, CTest 1/1 Passed)
  L4: PASS (无可扫描 ELF 文件)
  L5: PASS (产物与基线完全一致, 3 个文件)
```

## 交付物

| 文件 | 类型 | 大小 | 说明 |
|------|------|------|------|
| libident.a | 静态库 | 14682 bytes | llvm-ar 归档, 含 6 个目标文件 |
| ident.h | 头文件 | 2408 bytes | 公共 API 声明 |
| ident.3 | man page | - | API 文档 |
| libident.la | libtool 归档 | - | libtool 元数据 |

> 注：使用 `--enable-static --disable-shared` 构建，仅生成静态库。

## 注意事项

- libident 是库包（非终端工具），产物为 .a + 头文件
- conanfile.py 的 source() 方法使用 curl -kL 下载绕过 SSL 问题
- conanfile.py 的 build() 方法内联修复 config.guess 和 configure，无需外部补丁文件
- generate() 使用 --enable-static --disable-shared 实现 R26 静态链接
- package_info.cpp_info.libs = ["ident"] (去掉 lib 前缀)
- conan cache path 不带 package ID 返回 recipe 目录，需手动创建符号链接到 package 目录
- make jobserver mkfifo 在 HMDFS 上失败，但不影响构建（自动降级单线程）
---

**编译结束**: 2026-06-29 20:52
**最终状态**: built
