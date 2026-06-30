# moe 1.16 适配笔记

## 编译环境
- 构建系统: autotools（自定义 configure 脚本，非 autoconf 生成）
- 编译日期: 2026-06-29
- 编译器: clang/clang++ 15.0.4
- 平台: OpenHarmony aarch64 (native 编译)
- 状态: published

## 编译步骤

### 1. 下载源码
moe 源码以 .tar.lz 格式分发，Python urllib 因 SSL 证书问题无法下载，使用 curl -kL 手动下载。
鸿蒙环境无 lzip，需从源码编译安装 lzip 1.25（使用 clang++ 编译）。

```bash
# 下载 lzip 源码并编译
curl -kL -o lzip-1.25.tar.gz "https://download.savannah.gnu.org/releases/lzip/lzip-1.25.tar.gz"
tar xzf lzip-1.25.tar.gz && cd lzip-1.25
./configure --prefix=$HOME/.local CXX=clang++
make -j1 && make install
cp $HOME/.local/bin/lzip /storage/Users/currentUser/usr/local/bin/

# 下载 moe 源码
curl -kL -o moe-1.16.tar.lz "https://ftpmirror.gnu.org/gnu/moe/moe-1.16.tar.lz"
lzip -d -k moe-1.16.tar.lz
tar xf moe-1.16.tar
```

### 2. configure
moe 的 configure 是手写脚本（非 autoconf），不使用 config.guess/config.sub。
默认 CXX=g++，回退 CXX=c++，两者在鸿蒙平台均不存在，必须显式传 CXX=clang++（E053）。

```bash
./configure --prefix=$DEFAULT_PREFIX \
  CXX=clang++ \
  CXXFLAGS="-O2 -fPIC -I/storage/Users/currentUser/usr/local/include" \
  LDFLAGS="-static -L/storage/Users/currentUser/usr/local/lib"
```

### 3. make
```bash
make -j1 CXX=clang++ \
  CXXFLAGS="-O2 -fPIC -I/storage/Users/currentUser/usr/local/include" \
  LDFLAGS="-static -L/storage/Users/currentUser/usr/local/lib"
```

### 4. make install DESTDIR（Staging 隔离）
```bash
make install DESTDIR=$TEST_PREFIX
```

### 5. make check
```bash
make check  # 输出: No tests yet defined for moe-1.16
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | 鸿蒙环境缺少 CA 证书 | 使用 curl -kL 手动下载 |
| 2 | .tar.lz 无法解压 | Python tarfile 不支持 lzip | 编译安装 lzip 1.25，手动解压 |
| 3 | ncurses.h 未找到 | 编译器搜索路径不含 /usr/local/include | CXXFLAGS 添加 -I 路径 |
| 4 | libncurses 未找到 | 链接器搜索路径不含 /usr/local/lib | LDFLAGS 添加 -L 路径 |
| 5 | CXX=c++ 不存在 (E053) | configure 默认 g++/c++，鸿蒙只有 clang++ | configure 参数 CXX=clang++ |
| 6 | test_package API 错误 | 模板用 Conan 1.x deps_cpp_info | 改用 Conan 2.x self.dependencies |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| ncurses | 系统预装 | 静态库 libncurses.a，位于 /storage/Users/currentUser/usr/local/lib/ |
| lzip | 1.25 | 解压工具，从源码编译安装 |
| clang++ | 15.0.4 | 鸿蒙 LLVM 工具链 |

## 验证结果

### Staging 验证
```bash
$ find $TEST_PREFIX -type f
bin/moe           (3,758,080 bytes, ELF static)
etc/moe.conf      (2,441 bytes)
share/info/moe.info  (47,837 bytes)
share/man/man1/moe.1 (4,154 bytes)

$ file bin/moe
ELF executable, 64-bit LSB arm64, static, not stripped

$ readelf -d bin/moe
There is no dynamic section in this file.  # 完全静态链接

$ ./moe --version
GNU moe 1.16
```

### Conan 验证 (conan-verify)
- G0: ✅ PASS (预构建风险评估)
- G1: ✅ PASS (配方完整性)
- G2: ✅ PASS (conan create 成功)
- G3: ✅ PASS (静态链接 R26)
- G4: ✅ PASS (产物完整性)
- L2: ✅ PASS (smoke test: GNU moe 1.16)
- L4: ✅ PASS (NX=enabled, RELRO=partial)
- L5: ✅ PASS (产物基线一致)

## 源码修改

无源码修改。所有适配通过 configure 参数和 conanfile.py 配置实现，未修改任何源文件（R6）。

## 注意事项

1. moe 源码以 .tar.lz 格式分发，CI 环境需预装 lzip 工具
2. moe 的 configure 是手写脚本，不接受标准 autotools 参数（--build/--host/--target 等）
3. 鸿蒙平台必须显式指定 CXX=clang++（E053）
4. ncurses 头文件和库在 /storage/Users/currentUser/usr/local/，需显式指定路径
5. 使用 -static 实现完全静态链接，产物无动态依赖（R26）

---

**编译结束**: 2026-06-29
**最终状态**: published
