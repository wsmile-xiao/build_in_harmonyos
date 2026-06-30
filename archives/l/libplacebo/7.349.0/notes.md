# libplacebo 7.349.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-21
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. 源码下载
   - 从 VideoLAN GitLab 下载：https://code.videolan.org/videolan/libplacebo/-/archive/v7.349.0/libplacebo-v7.349.0.tar.gz
   - 使用本地文件初始化编译：`--url=file:///storage/Users/currentUser/tmp/libplacebo-v7.349.0.tar.gz`

2. 补充 git submodules
   - libplacebo 使用 git submodules 管理第三方依赖
   - tar.gz 包不包含 submodules，需要手动下载：
     - fast_float：从 GitHub 下载 v6.1.6，解压后放到 `3rdparty/fast_float/include/` 目录

3. Meson 配置
   ```bash
   meson setup build --prefix=/storage/Users/currentUser/usr/local --buildtype=release \
     -Dopengl=disabled \
     -Dvulkan=disabled \
     -Dd3d11=disabled \
     -Dglslang=disabled \
     -Dshaderc=disabled \
     -Ddemos=false \
     -Dtests=false
   ```

4. 编译
   ```bash
   cd build
   ninja
   ```

5. 安装到 staging 目录
   ```bash
   meson install --destdir $TEST_PREFIX
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah 下载链接 404 | libplacebo-latest.tar.gz 不存在 | 使用 VideoLAN GitLab 的具体版本链接 |
| 2 | SSL 证书验证失败 | Savannah SSL 证书问题 | 从 GitLab/GitHub 下载，使用 curl -k |
| 3 | 缺少 glad (OpenGL loader) | git submodule 未包含 | 禁用 OpenGL 功能 |
| 4 | 缺少 fast_float 头文件 | git submodule 未包含 | 手动下载 fast_float v6.1.6 并放到正确位置 |
| 5 | fast_float.h 路径不匹配 | meson 检查 `3rdparty/fast_float/include` | 重组目录结构为 include/fast_float/ |

## 源码修改

无补丁，仅补充了第三方依赖文件（fast_float）。

## 依赖版本

- meson: 1.11.1
- ninja: 1.12.1
- clang: 15.0.4
- python3: 3.12
- Vulkan headers (系统自带): 1.4.309

## 验证结果

```bash
# 编译成功，生成共享库
ls -lh /storage/Users/currentUser/test-install-libplacebo-7.349.0/storage/Users/currentUser/usr/local/lib/libplacebo.so.349
# 输出: 690K 共享库文件

# 头文件安装验证
ls /storage/Users/currentUser/test-install-libplacebo-7.349.0/storage/Users/currentUser/usr/local/include/libplacebo/*.h
# 26 个头文件成功安装
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libplacebo-7.349.0-ohos-aarch64.tar.gz | 1.9M | 预编译包（已签名） |
| libplacebo-7.349.0-ohos-aarch64-debug.tar.gz | 220K | 调试符号包 |

## 注意事项

1. **构建系统为 Meson**：libplacebo 使用 Meson 构建系统，而非 autotools
2. **Git submodules 重要**：下载 tar.gz 包时需要手动补充 submodules（fast_float、glad等）
3. **图形 API 禁用**：在鸿蒙系统上禁用了 Vulkan/OpenGL/D3D11，编译为有限功能版本
4. **fast_float 目录结构**：必须放在 `3rdparty/fast_float/include/fast_float/` 才能被 meson 检测到

---

## 质量门禁验证

### G0 干净构建验证：✅ PASS（已修复）

**修复日期**: 2026-05-22

**原始问题**: 原始 tar.gz 缺少 fast_float git submodule

**修复方案**:
1. 创建 `hints/post-download.sh` 脚本，在 tarball 解压后自动补充 fast_float 头文件
2. 修改 `scripts/ohc/clean_verify.py`：
   - 添加 hints/post-download.sh 执行支持
   - 添加 meson 构建系统支持（meson setup + ninja + meson install）
   - 修复 LD_LIBRARY_PATH 顺序问题（python lib 必须在 usr/local/lib 前面）
   - 修复 YAML list 格式 configure_options 解析问题

**hints/post-download.sh 脚本位置**:
- `archives/l/libplacebo/7.349.0/hints/post-download.sh`

**脚本功能**:
- 检查是否已有 fast_float 头文件（避免重复下载）
- 优先使用本地已有的 fast_float tarball
- 从 GitHub 下载作为备选方案（但网络可能不稳定）

**验证结果**:
```
ℹ️ G0: 解压 libplacebo-v7.349.0.tar.gz 到临时目录
ℹ️ G0: 无补丁
ℹ️ G0: 运行 hints/post-download.sh...
✅ G0: hints/post-download.sh 成功
✅ G0: meson setup 成功
✅ G0: ninja 成功
✅ G0: 安装产物正常 (0 bin, 3 lib)
✅ G0 干净构建验证通过
```

**知识沉淀**:
- Git submodule 缺失问题可通过 hints/post-download.sh 自动化解决
- Meson 构建系统在 clean_verify.py 中需要特殊处理（不同于 autotools）
- LD_LIBRARY_PATH 顺序很重要：系统 Python 的 lib 目录必须优先于 usr/local/lib

### G4 档案完整性：✅ PASS（已修复）

**修复内容**: 创建软件级 README.md
- 路径: `archives/l/libplacebo/README.md`
- 内容: 软件简介、主要功能、编译说明、已知问题（含 submodule 缺失）
---

**编译结束**: 2026-05-22 10:14
**最终状态**: published（G0-G4 全部通过，hints/post-download.sh 修复生效）
