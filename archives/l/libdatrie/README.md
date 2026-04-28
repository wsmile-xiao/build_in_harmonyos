# libdatrie 0.2.14 — OpenHarmony 编译记录

## 基本信息
- **软件**: libdatrie (Double-Array Trie Library)
- **版本**: 0.2.14
- **构建系统**: autotools
- **目标平台**: ohos-aarch64
- **编译状态**: ✅ 成功 (partial)
- **源码来源**: https://github.com/tlwg/libdatrie (Debian mirror)

## 编译指导

### 环境要求
- clang 15.0.4
- make 4.4.1
- autoconf 2.72
- pkg-config 0.29.2

### 编译步骤
```bash
# 1. 解压源码
tar -xf libdatrie-0.2.14.tar.xz
cd libdatrie-0.2.14

# 2. 应用补丁（E007 - HarmonyOS 平台识别）
patch -p1 < patches/0001-build-aux-config.guess.patch
patch -p1 < patches/0002-build-aux-config.sub.patch

# 3. 配置（注意 HMDFS 临时目录问题）
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR/libdatrie_tmp_fixed
./configure --prefix=$HOME/usr/local

# 4. 编译
make -j$(nproc)

# 5. 测试
make check  # 10/10 PASS

# 6. 安装
make install DESTDIR=$HOME/test-install-libdatrie-0.2.14
```

## 补丁清单

| 补丁文件 | 类型 | 说明 |
|---------|------|------|
| 0001-build-aux-config.guess.patch | 平台识别 | 添加 __OHOS__ LIBC 检测和 HarmonyOS 系统识别 |
| 0002-build-aux-config.sub.patch | 平台识别 | 添加 ohos-linux 三元组支持 |

## 已知限制

### F001: HMDFS config.status 临时目录限制
config.status 脚本在 HMDFS 上无法在当前目录创建临时文件。
**解决方案**: 预创建 `$TMPDIR/libdatrie_tmp_fixed` 目录并修改 config.status。

### F002: GitHub 下载超时
GitHub releases URL 可能连接超时。
**解决方案**: 使用 Debian 镜像 `https://deb.debian.org/debian/pool/main/libd/libdatrie/`

## 功能验证

```bash
# 验证工具
$ trietool --version
0.2.14

# 验证库
$ pkg-config --modversion datrie-0.2
0.2.14

# 测试结果
$ make check
============================================================================
Testsuite summary for libdatrie 0.2.14
============================================================================
# TOTAL: 10
# PASS:  10
# SKIP:  0
# XFAIL: 0
# FAIL:  0
============================================================================
```

## 编译产物

- `lib/libdatrie.so.1.4.1` - 共享库 (48KB)
- `lib/libdatrie.a` - 静态库 (48KB)
- `bin/trietool` - 命令行工具 (31KB)
- `include/datrie/*.h` - 头文件 (4 个)
- `lib/pkgconfig/datrie-0.2.pc` - pkg-config 文件

## 质量门禁

| 门禁 | 状态 |
|------|------|
| G1 二进制完整性 | ✅ PASS |
| G2 功能可用性 | ✅ PASS |
| G3 可移植性 | ✅ PASS |
| G4 档案完整性 | ✅ PASS |
| G0 干净构建 | ⚠️ SKIP (HMDFS) |

---

**归档日期**: 2026-04-22
**归档路径**: archives/l/libdatrie/0.2.14/
