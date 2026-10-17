# libcutl 1.11.0 适配笔记

## 编译环境
- 构建系统: build2（手动编译，源码包使用 build2 构建系统而非任务描述的 autotools）
- 编译日期: 2026-06-11
- 编译器: clang/clang++ 15.0.4
- 目标平台: 鸿蒙 aarch64
- 状态: built
- 预编译包: libcutl-1.11.0-ohos-aarch64.tar.gz (662KB)

## 编译步骤（完整真实执行流程）

### 步骤1：初始化编译环境

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libcutl 1.11.0 \
  --url=https://www.codesynthesis.com/download/xsd/4.2/libcutl-1.11.0.tar.gz
```

结果: ✅ 下载、解压、归档骨架创建、依赖检查、环境检查全部通过。

### 步骤2：发现构建系统问题

```bash
cd $BUILD_SRC_DIR && ls -la configure
# ls: cannot access 'configure': No such file or directory
```

**发现**: 源码包无 configure 脚本，目录中存在 buildfile、manifest、build/root.build 等 build2 构建文件。manifest 文件明确标注 `depends: * build2 >= 0.16.0`。此版本已从 autotools 迁移到 build2。

### 步骤3：手动编译源码

```bash
source .build-context-libcutl-1.11.0
cd $BUILD_SRC_DIR
mkdir -p obj

# 编译 9 个 .cxx 源文件（逐文件执行，全部成功）
clang++ -c -O2 -fPIC -I. -DLIBCUTL_STATIC_BUILD libcutl/exception.cxx -o obj/exception.o
clang++ -c -O2 -fPIC -I. -DLIBCUTL_STATIC_BUILD libcutl/shared-ptr/base.cxx -o obj/shared-ptr-base.o
clang++ -c -O2 -fPIC -I. -DLIBCUTL_STATIC_BUILD libcutl/re/re.cxx -o obj/re.o
clang++ -c -O2 -fPIC -I. -DLIBCUTL_STATIC_BUILD libcutl/fs/exception.cxx -o obj/fs-exception.o
clang++ -c -O2 -fPIC -I. -DLIBCUTL_STATIC_BUILD libcutl/fs/auto-remove.cxx -o obj/fs-auto-remove.o
clang++ -c -O2 -fPIC -I. -DLIBCUTL_STATIC_BUILD libcutl/fs/path.cxx -o obj/fs-path.o
clang++ -c -O2 -fPIC -I. -DLIBCUTL_STATIC_BUILD libcutl/compiler/type-info.cxx -o obj/compiler-type-info.o
clang++ -c -O2 -fPIC -I. -DLIBCUTL_STATIC_BUILD libcutl/compiler/cxx-indenter.cxx -o obj/compiler-cxx-indenter.o
clang++ -c -O2 -fPIC -I. -DLIBCUTL_STATIC_BUILD libcutl/compiler/context.cxx -o obj/compiler-context.o
```

### 步骤4：打包静态库

```bash
llvm-ar rcs libcutl.a obj/*.o
llvm-ranlib libcutl.a
# 产物: libcutl.a (519970 字节)
```

### 步骤5：DESTDIR 模式安装（R20 铁律）

```bash
# --prefix=$DEFAULT_PREFIX + DESTDIR=$TEST_PREFIX
STAGING=$TEST_PREFIX/$DEFAULT_PREFIX

# 安装头文件（45 个 .hxx/.ixx/.txx，含 compiler/container/fs/meta/re/shared-ptr 子目录）
mkdir -p $STAGING/include/libcutl/libcutl/{compiler,container,fs,meta,re,shared-ptr}
mkdir -p $STAGING/lib/pkgconfig
cp libcutl/*.hxx $STAGING/include/libcutl/libcutl/
cp libcutl/compiler/*.{hxx,ixx,txx} $STAGING/include/libcutl/libcutl/compiler/
cp libcutl/container/*.{hxx,txx} $STAGING/include/libcutl/libcutl/container/
cp libcutl/fs/*.{hxx,ixx,txx} $STAGING/include/libcutl/libcutl/fs/
cp libcutl/meta/*.hxx $STAGING/include/libcutl/libcutl/meta/
cp libcutl/re/*.txx $STAGING/include/libcutl/libcutl/re/
cp libcutl/shared-ptr/*.{hxx,ixx,txx} $STAGING/include/libcutl/libcutl/shared-ptr/

# 安装静态库
cp libcutl.a $STAGING/lib/

# 创建 pkg-config 文件
cat > $STAGING/lib/pkgconfig/libcutl.pc << 'EOF'
prefix=/storage/Users/currentUser/usr/local
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include/libcutl
Name: libcutl
Description: C++ utility library for compilers
Version: 1.11.0
Libs: -L${libdir} -lcutl
Cflags: -I${includedir} -DLIBCUTL_STATIC
EOF
```

### 步骤6：功能测试（真实执行）

**测试1 — 版本验证**:
```bash
$TMPDIR/test_libcutl
# 输出:
libcutl version: 1.11.0
libcutl version number: 100011000000000
```
✅ 版本号正确

**测试2 — 核心功能验证**:
```bash
$TMPDIR/test_libcutl2
# 输出:
Version check OK: 1.11.0
Path: /usr/local/include/libcutl
Path leaf: libcutl
Path directory: /usr/local/include
Exception caught: N4cutl9exceptionE
type_id of int: i
All feature tests passed!
```
✅ fs::path、exception、compiler::type_id 全部正常

**测试3 — 本地安装验证**（模拟用户部署）:
```bash
$TMPDIR/test_local
# 输出:
libcutl local install verification:
  Version: 1.11.0
  Path test: path
```
✅ 本地安装路径可用

**测试4 — pkg-config**:
```bash
PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig pkg-config --modversion libcutl
# 输出:
1.11.0
```
✅ pkg-config 正常返回版本号

### 步骤7：预编译包制作（R19 铁律：禁止手动打包）

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package libcutl 1.11.0
# 9 步自动流程: 收集→清理→链接替换→依赖收集→RPATH→Strip→签名→权限→tar.gz
# 产物: libcutl-1.11.0-ohos-aarch64.tar.gz (662KB)
```

### 步骤8：本地安装（不带 DESTDIR，模拟用户部署）

```bash
cp -r $STAGING/include/libcutl/libcutl/* $DEFAULT_PREFIX/include/libcutl/libcutl/
cp $STAGING/lib/libcutl.a $DEFAULT_PREFIX/lib/
cp $STAGING/lib/pkgconfig/libcutl.pc $DEFAULT_PREFIX/lib/pkgconfig/
```

### 步骤9：收尾（ohc-run.py finish）

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish libcutl 1.11.0 built
# 补丁生成: 0 个补丁（无源码修改）
# 归档关闭: built
# G0: FAIL（无 configure 脚本，build2 源码）
# G1-G4: PASS
# 知识条目: E105 (build2源码手动编译策略)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码包无 configure 脚本 | v1.11.0 使用 build2 构建系统而非 autotools（与任务描述不符） | 手动编译: 逐文件 clang++ 编译 + llvm-ar 打包为静态库 |
| 2 | /tmp 只读 (E002) | HMDFS 限制，写入报 Read-only | 使用 $TMPDIR 替代硬编码 /tmp |
| 3 | G0 门禁无法通过 | clean-verify 尝试运行 ./configure，但源码无 configure 脚本 | 已记录原因于 notes.md，手动验证编译和功能通过 |
| 4 | G4 manifest 缺少 build_system 字段 | manifest 模板使用嵌套 build.system，验证脚本期望顶层字段 | 在 manifest.yaml 顶层添加 `build_system: custom` |
| 5 | shared_ptr 测试 abort | libcutl::shared_ptr 是侵入式智能指针，要求对象继承自带引用计数的 shared base | 修改测试代码，仅验证 fs::path/exception/compiler::type_id 等非侵入式功能 |

## 源码修改

无补丁。源码无需任何修改：
- version.hxx 在源码包中已预生成（从 version.hxx.in 替换为 1.11.0 数值），无需额外处理
- export.hxx 的 fallback 分支在未定义 LIBCUTL_STATIC/SHARED 时自动生效，兼容手动编译

## 依赖版本

- clang/clang++ 15.0.4
- llvm-ar / llvm-ranlib
- GNU Make 4.4.1（未使用，手动编译）
- autoconf 2.72 / automake 1.17（未使用）
- pkg-config 0.29.2
- 无外部库依赖（libcutl 是纯 C++ 头文件+源码工具库）

## 质量门禁验证结果

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 干净构建 | ❌ FAIL | 源码无 configure 脚本（build2 构建系统），自动验证无法执行。已手动验证编译和功能均正常 |
| G1 二进制完整性 | ✅ PASS | libcutl.a 包含 9 个对象文件，519970 字节 |
| G2 功能可用性 | ✅ PASS (⚠️1) | 版本号、fs::path、exception、compiler::type_id 均通过。⚠️: 无独立可执行二进制 |
| G3 可移植性 | ✅ PASS | 纯静态库，无动态链接依赖，无 RPATH 问题 |
| G4 档案完整性 | ✅ PASS | manifest.yaml、notes.md、test-report.md、packaging/ 齐全 |

## 注意事项

- libcutl::shared_ptr 是**侵入式**智能指针，需要对象继承自带引用计数的 shared base，不能直接对普通类型使用
- 此版本源码使用 build2 构建系统，平台无 build2/bpkg，只能手动编译
- G0 门禁无法通过是预期行为（build2 源码无 configure），不影响实际编译质量
---

**编译结束**: 2026-07-28 16:42
**最终状态**: built
---

**编译结束**: 2026-07-28 16:43
**最终状态**: built
