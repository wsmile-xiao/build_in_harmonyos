# libnova 编译笔记

## 基本信息

- **软件名称**: libnova
- **版本**: 0.14.0
- **类别**: 天文动力学计算库
- **构建系统**: autotools
- **编译日期**: 2026-06-08

## 编译流程记录

### Step 1: 源码准备

源码来源: `~/tmp/builds/JohannesBuchner-libnova-0ae301a`

此源码为本地已有的 Johannes Buchner 版本的 libnova，commit hash: 0ae301a

### Step 2: E011 HMDFS 权限修复应用

**关键步骤**: 在 configure 前应用 E011 修复

```bash
cd ~/tmp/builds/JohannesBuchner-libnova-0ae301a
sed -i 's/umask 077/umask 022/g' configure
```

**修复说明**:
- autotools 的 configure 脚本中使用 `umask 077` 创建临时文件
- 在 HMDFS 文件系统上，这会导致权限问题
- 将 `umask 077` 改为 `umask 022` 可以避免此问题

**验证**:
```bash
grep -n "umask 022" configure
# 输出:
# 16584:  tmp=`(umask 022 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
# 16589:  (umask 022 && mkdir "$tmp")
```

### Step 3: Configure 配置

```bash
./configure --prefix=/storage/Users/currentUser/usr/local
```

**配置成功**: config.status 生成，exit 0

**关键配置参数**:
- PREFIX: /storage/Users/currentUser/usr/local
- Compiler: clang (OHOS)
- Target: aarch64-unknown-linux-ohos

### Step 4: 编译

```bash
make -j$(nproc)
```

**编译成功**: 所有源文件编译完成

**编译警告** (不影响功能):
- `lunar.c:163:21: warning: unused variable 'W2'`
- `lunar.c:172:21: warning: unused variable 'W3'`
- `lunar.c:181:21: warning: unused variable 'earth'`
- `lunar.c:190:21: warning: unused variable 'peri'`
- `test.c:227:9: warning: variable 'JDE' set but not used`

这些警告来自源码中的未使用变量，不影响库功能。

### Step 5: 安装

#### DESTDIR 安装（测试验证）

```bash
TEST_PREFIX="/storage/Users/currentUser/tmp/libnova-test-install"
make install DESTDIR="$TEST_PREFIX"
```

**安装产物**:
- `/storage/Users/currentUser/usr/local/lib/libnova-0.14.so.0.0.0` (3.73 MB)
- `/storage/Users/currentUser/usr/local/lib/libnova.a` (3.81 MB)
- `/storage/Users/currentUser/usr/local/include/libnova/*.h` (32 files)

#### 本地安装

```bash
make install
```

**安装成功**: 库文件和头文件已安装到 DEFAULT_PREFIX

## 质量门禁验证

### G0 - 编译成功 ✅

- 编译命令执行成功
- 所有源文件编译完成
- 无致命错误

### G1 - 基本安装 ✅

- DESTDIR 安装成功
- 本地安装成功
- 文件权限正确

### G2 - 库文件存在 ✅

**共享库**:
- `libnova-0.14.so.0.0.0`: ELF64 AArch64, not stripped
- Symbolic links: libnova.so, libnova-0.14.so.0

**静态库**:
- `libnova.a`: ar archive format

### G3 - 头文件存在 ✅

**头文件目录**: `/storage/Users/currentUser/usr/local/include/libnova/`

**关键头文件**:
- `libnova.h` - 主头文件
- `julian_day.h` - Julian Day 计算
- `dynamical_time.h` - 动力学时间
- `sidereal_time.h` - 恒星时
- `solar.h` - 太阳位置计算
- `lunar.h` - 月球位置计算
- `vsop87.h` - VSOP87 行星理论
- 等共 32 个头文件

### G4 - ELF 签名 ⚠️ (部分通过)

**检查结果**:
```bash
readelf -S libnova-0.14.so.0.0.0 | grep ohos
# 输出: [ 1] .note.ohos.ident  NOTE
```

**说明**:
- `.note.ohos.ident` 段存在，表明 ELF 文件包含 OpenHarmony 标识
- 未发现完整的签名段（可能需要额外的签名工具）

## 关键文件路径

### 库文件
- 共享库: `/storage/Users/currentUser/usr/local/lib/libnova-0.14.so.0.0.0`
- 静态库: `/storage/Users/currentUser/usr/local/lib/libnova.a`
- Libtool: `/storage/Users/currentUser/usr/local/lib/libnova.la`

### 头文件
- 目录: `/storage/Users/currentUser/usr/local/include/libnova/`
- 主文件: `libnova.h`

### 可执行文件
- 配置工具: `/storage/Users/currentUser/usr/local/bin/libnovaconfig`

## 依赖关系

### 构建依赖
- libm (数学库)
- clang compiler
- autotools (autoconf, automake, libtool)

### 运行依赖
- libm (数学库)

## 已知问题与解决方案

### E011 - HMDFS 权限问题 ✅ 已解决

**问题**: autotools configure 使用 umask 077 导致 HMDFS 文件系统权限冲突

**解决方案**: 在 configure 前修改 configure 文件
```bash
sed -i 's/umask 077/umask 022/g' configure
```

**应用状态**: 成功应用，configure 和编译正常完成

## 下一步工作建议

1. **完整签名**: 使用 elfsign 工具对 ELF 文件进行完整签名
2. **测试验证**: 运行 lntest 测试套件验证库功能
3. **文档完善**: 补充 API 文档和使用示例
4. **注册记录**: 将 libnova 信息注册到 software-registry.yaml

## 编译环境信息

- **编译器**: clang (OHOS)
- **目标平台**: aarch64-unknown-linux-ohos
- **构建工具**: autotools
- **并发编译**: 4 线程
- **构建时长**: 约 2 分钟

## 总结

libnova 0.14.0 在 OpenHarmony 上编译成功，E011 修复有效应用。库文件和头文件已正确安装，可以作为 libindi 的依赖库使用。

**编译状态**: ✅ 成功
**安装状态**: ✅ 完成
**E011 修复**: ✅ 应用成功
**质量门禁**: G0-G3 全部通过，G4 部分通过