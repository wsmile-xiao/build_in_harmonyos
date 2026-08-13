# proj 9.3.1 适配笔记

## 本地 CI 预审与测试闭环（2026-07-31）

- 在 Ubuntu WSL2（x86_64、GCC 15.2.0、CMake/CTest 4.2.3、Conan 2.29.0）完成
  `conan create archives/p/proj/9.3.1 --build=missing`。构建使用本地 Conan
  缓存的 `sqlite3/3.49.1` 作为 host library 和 build tool。该本地预审曾启用
  PROJ 上游 GoogleTest 1.11.0；当前 CI 配方关闭 `BUILD_TESTING`，因为 PROJ 会在
  configure 阶段从 GitHub 下载 GoogleTest，CI 网络不可用时会导致生产库无法配置。
- 本地预审中 `ctest -N` 注册 56 个上游测试；`ctest --output-on-failure --parallel 2`
  实际执行 **56/56 通过（100%）**。该记录仅作为 Linux 预审证据，当前 OHOS CI
  不执行上游测试树，改由下述消费者测试覆盖已安装包的关键 API。
- `conan create` 已完成打包和本仓库 `test_package/CMakeLists.txt` 对安装树的
  `PROJ::proj` 独立消费者验证：`ctest --output-on-failure` 实际执行
  **1/1 通过（100%，0.07 秒）**；`test_proj.cpp` 内 6 个 API/地理计算断言均通过。
  安装后的 `projinfo EPSG:4326` 也成功输出 WGS 84。
- GCC 15 暴露上游两个 CLI 源文件缺少 `<cstdint>` 的问题；
  `patches/0001-add-cstdint-to-cli-sources.patch` 只补充这两个 include，
  补丁后的全量构建和全部 CTest 均通过。
- 上述是本地 Linux x86_64 结果，不等同于 OpenHarmony 目标运行结果。PR 仍须由
  远端 CI 在目标配置中重新构建和执行，不能将此记录表述为 OHOS 通过。

## Conan 固化记录（2026-07-20）

- 新增 `conanfile.py`、`conandata.yml` 和 `test_package/`，使用官方 OSGeo
  源码包 `https://download.osgeo.org/proj/proj-9.3.1.tar.gz`。
- 源码 SHA256：
  `b0f919cb9e1f42f803a3e616c2b63a78e4d81ecfaed80978d570d3a5e29d10bc`。
- PROJ 构建期必须运行 sqlite3 生成 `proj.db`，recipe 同时声明
  `self.requires("sqlite3/3.49.1")` 和 `self.tool_requires("sqlite3/3.49.1")`。
- 首版 Conan 包关闭 `ENABLE_TIFF`、`ENABLE_CURL` 和 `BUILD_PROJSYNC`，避免在
  MapServer 依赖前置阶段引入未固化的 CURL/TIFF 全链；保留核心库和
  `proj`、`cs2cs`、`cct`、`geod`、`gie`、`projinfo` 等常用命令。
- `test_package/test_proj.cpp` 覆盖版本查询、context 生命周期、pipeline 坐标变换、
  非法 projection 拒绝和 geodesic inverse 计算。
- 早期 Windows 原生验证仅覆盖 configure/build/install 和消费者检查；完整的
  上游 CTest 统计以本文件 2026-07-31 的 WSL 预审记录为准。
- 本机未安装 OpenHarmony Conan，因此 `conan create proj/9.3.1` 需等待远端 OHOS CI。

## 归档：2026-05 历史原生尝试（非当前 Conan 证据）

以下记录仅保留旧的 OpenHarmony 原生构建排障背景；不表示当前 Conan recipe
已在 OHOS 目标上验证，也不覆盖上文 2026-07-31 的本地测试结果。

### 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: built

### 编译步骤

```bash
cd /storage/Users/currentUser/tmp/builds/proj-9.3.1.work
mkdir -p build && cd build

cmake .. \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_TESTING=ON \
  -DCMAKE_C_FLAGS="-fPIC -O2 -fuse-ld=bfd" \
  -DCMAKE_CXX_FLAGS="-fPIC -O2 -fuse-ld=bfd" \
  -DCMAKE_EXE_LINKER_FLAGS="-fuse-ld=bfd" \
  -DCMAKE_SHARED_LINKER_FLAGS="-fuse-ld=bfd" \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5

make -j2
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-proj-9.3.1
make install
```

### 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 可执行文件运行时找不到 libproj.so | proj 使用 $ORIGIN/../lib 相对路径 RPATH，OpenHarmony 不支持 | 使用静态链接 BUILD_SHARED_LIBS=OFF |
| 2 | CMake configure 失败：lld 链接器缺少 libxml2.so.16 | OpenHarmony SDK 的 lld 依赖 libxml2，但库路径不正确 | 添加 -fuse-ld=bfd 标志使用 GNU ld 链接器 |
| 3 | CMake 策略版本警告 | proj cmake/Ccache.cmake 使用 cmake_minimum_required(VERSION 3.5) | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |

### 源码修改

该历史尝试未记录补丁。当前 Conan recipe 使用
`patches/0001-add-cstdint-to-cli-sources.patch`，详见上文当前验证记录。

### 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| sqlite3 | 3.49.1 | 动态库依赖 |
| tiff | 4.7.1 | 动态库依赖 |
| curl | 8.19.0 | 动态库依赖 |

### 验证结果

```bash
# 验证静态链接（无 libproj.so NEEDED）
readelf -d /storage/Users/currentUser/usr/local/bin/proj | grep NEEDED
# 输出：libsqlite3.so.0, libtiff.so.6, libcurl.so.4, libc++_shared.so, libc.so
# 注意：无 libproj.so，说明静态链接成功

# 预编译包
ls -la archives/p/proj/9.3.1/packaging/
# proj-9.3.1-ohos-aarch64.tar.gz: 65.7 MB
# proj-9.3.1-ohos-aarch64-debug.tar.gz: 11.1 MB
```

### 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| proj-9.3.1-ohos-aarch64.tar.gz | 65.7 MB | 预编译包 |
| proj-9.3.1-ohos-aarch64-debug.tar.gz | 11.1 MB | 调试符号包 |

### 注意事项

1. **静态链接是关键**：BUILD_SHARED_LIBS=OFF 确保可执行文件不依赖 libproj.so，解决 RPATH 问题
2. **链接器选择**：使用 -fuse-ld=bfd 避免 lld 的 libxml2 依赖问题
3. **外部依赖仍为动态库**：sqlite3, tiff, curl 等仍为动态链接，需确保这些库在目标系统可用

---

**编译结束**: 2026-05-29 19:44
**最终状态**: built

---

### 依赖修复记录（2026-05-29）

### 问题描述
1. 缺少 libsqlite3.so.0、libtiff.so.6、liblzma.so.5 依赖库
2. libtiff.so.6 的 RUNPATH 设置错误（指向具体文件而非目录）
3. 缺少 libc++_shared.so

### 修复措施
1. 添加缺失的依赖库到 lib/external 目录：
   - libsqlite3.so.0 (从 /storage/Users/currentUser/usr/local/lib/external)
   - libtiff.so.6.2.0 (从 /storage/Users/currentUser/usr/local/lib)
   - liblzma.so.5.6.2 (从 /storage/Users/currentUser/usr/local/lib)
   - libcurl.so.4 (从 /storage/Users/currentUser/usr/local/lib)
   - libssl.so.3 (从 /storage/Users/currentUser/usr/local/lib/external)
   - libcrypto.so.3 (从 /storage/Users/currentUser/usr/local/lib/external)
   - libc++_shared.so (从 /system/lib64)

2. 修复 RUNPATH 设置：
   - 可执行文件: $ORIGIN/../lib/external（相对路径正确指向依赖库目录）
   - 库文件: $ORIGIN（库文件相互依赖时能找到同目录下的其他库）
   
3. 使用文件复制而非软链接：
   - libtiff.so.6 从 libtiff.so.6.2.0 复制（而非软链接）
   - liblzma.so.5 从 liblzma.so.5.6.2 复制（而非软链接）
   - 原因：避免 HMDFS 文件系统的软链接加载问题

4. ELF 签名：
   - 使用 ohc-run.py sign-elf 对所有 ELF 文件重新签名
   - 确保在 OpenHarmony 系统上可执行

### 验证结果
- proj --version: ✓ 成功运行 (Rel. 9.3.1)
- cs2cs: ✓ 成功运行
- geod: ✓ 成功运行
- projinfo: ✓ 成功运行
- RUNPATH 检查: ✓ 正确设置

### 最终打包依赖库
- libc++_shared.so (1.4M)
- libcrypto.so.3 (4.1M)
- libcurl.so.4 (830K)
- liblzma.so.5 (230K)
- liblzma.so.5.6.2 (230K)
- libsqlite3.so.0 (1.4M)
- libssl.so.3 (762K)
- libtiff.so.6 (539K)
- libtiff.so.6.2.0 (539K)

---

**修复结束**: 2026-05-29 21:26
**最终状态**: published
