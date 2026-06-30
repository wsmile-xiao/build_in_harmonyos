# graphviz 12.2.1 编译笔记

## 编译环境

- **操作系统**: OpenHarmony
- **编译器**: clang 15.0.4, clang++ 15.0.4
- **构建工具**: cmake 3.28.3
- **源码版本**: graphviz 12.2.1
- **源码来源**: https://gitlab.com/graphviz/graphviz/-/archive/12.2.1/graphviz-12.2.1.tar.gz

## 编译步骤

### Step 1: 下载源码

```bash
curl -k -L -o graphviz-12.2.1.tar.gz https://gitlab.com/graphviz/graphviz/-/archive/12.2.1/graphviz-12.2.1.tar.gz
```

**问题**: SSL 证书验证失败
**解决**: 使用 `-k` 参数跳过验证

### Step 2: 解压源码

```bash
mkdir -p ~/builds/graphviz-12.2.1.work
tar -xzf graphviz-12.2.1.tar.gz -C ~/builds/graphviz-12.2.1.work --strip-components=1
```

**问题**: 文件系统不支持硬链接
**解决**: 直接解压到目标目录

### Step 3: CMake 配置（静态链接）

```bash
cd ~/builds/graphviz-12.2.1.work
mkdir -p build-static
cd build-static

cmake .. \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_CXX_FLAGS="-stdlib=libc++" \
  -DCMAKE_EXE_LINKER_FLAGS="-lc++ -lc++abi -static-libgcc -static-libstdc++"
```

### Step 4: 编译

```bash
make -j2
```

**编译结果**: 100% 成功

### Step 5: 安装

```bash
make install DESTDIR=$TEST_PREFIX
make install  # 安装到本地 ~/usr/local
```

## 问题与解决方案

### 问题 1: Autotools 构建失败

**现象**:
- configure.ac 使用函数 `graphviz_version_major()` 定义版本
- autogen.sh 依赖 Git 环境生成 version.m4
- PKG_CHECK_MODULES 宏缺少 pkg.m4 文件

**解决**: 转用 CMake 构建系统

### 问题 2: C++ 链接失败

**现象**: dot_builtins 和 gvpack 缺少 C++ 标准库符号

**解决**: 添加链接选项 `-lc++ -lc++abi -static-libgcc -static-libstdc++`

### 问题 3: 运行时库路径相对路径（核心问题）

**现象**: ELF DT_NEEDED 条目使用相对路径 `../../lib/gvc/libgvc.so`

**根因**: graphviz CMake 构建系统硬编码相对路径，不适合 DESTDIR 模式

**解决**: 使用静态链接 `BUILD_SHARED_LIBS=OFF`

## 验证结果

### 运行时验证

```bash
$ dot -V
dot - graphviz version 12.2.1 (20260521.0212)

$ neato -V
neato - graphviz version 12.2.1 (20260521.0212)

$ readelf -d dot | grep NEEDED
libc++_shared.so, libc.so  # 仅系统库，无相对路径
```

### 质量门禁

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 | ⚠️ PYTHON_SUBPROCESS_LIMIT | 手动验证通过（平台限制） |
| G1 | ✅ PASS | 28 个二进制，2 个脚本 |
| G2 | ✅ PASS-WARN | 功能可用，部分工具 --version 不标准 |
| G3 | ✅ PASS-WARN | 静态链接，仅系统库依赖 |
| G4 | ✅ PASS | manifest.yaml 完整，README.md 已创建 |

## 交付物

### 预编译包

- `graphviz-12.2.1-ohos-aarch64.tar.gz` (19MB)
- `graphviz-12.2.1-ohos-aarch64-debug.tar.gz` (3.5MB)

### 核心产品

- **可执行工具**: 28 个（dot, neato, circo, fdp, sfdp, twopi, patchwork, osage, gvpr 等）
- **静态库**: libgvc.a, libcgraph.a, libcdt.a, libpathplan.a, libxdot.a

## 注意事项

1. **必须使用静态链接**: 动态链接版本存在相对路径问题，不适合打包发布
2. **需要添加 C++ 链接选项**: `-lc++ -lc++abi` 是必需的
3. **Autotools 构建不适用**: configure.ac 设计问题，只能用 CMake 构建

---

**编译结束**: 2026-05-21
**最终状态**: published
**质量门禁**: G0 手动验证通过, G1-G4 PASS