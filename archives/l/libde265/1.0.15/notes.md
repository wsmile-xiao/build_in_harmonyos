# libde265 1.0.15 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-30
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: built

## 编译步骤

本次编译使用 **CMake 方案**，而非默认的 autotools 方案。

**原因**：autotools 方案在 HMDFS 文件系统上遇到权限问题（config.status 无法创建临时文件 ./confXXXXXX），导致 configure 失败。libde265 提供 CMakeLists.txt，可以使用 CMake 构建。

**具体步骤**：

1. 初始化环境变量
   ```bash
   export LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH
   export DEFAULT_PREFIX=~/usr/local
   export TEST_PREFIX=~/tmp/test-install-libde265-1.0.15
   ```

2. CMake 配置
   ```bash
   mkdir -p $TMPDIR/libde265-build
   cd $TMPDIR/libde265-build
   cmake /storage/Users/currentUser/tmp/builds/libde265-1.0.15.work \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_POLICY_VERSION_MINIMUM=3.5
   ```

3. 编译
   ```bash
   make -j2
   ```
   编译成功，有一些 unused variable 警告，但不影响功能。

4. Staging 安装（R20 DESTDIR 模式）
   ```bash
   mkdir -p $TEST_PREFIX
   make install DESTDIR=$TEST_PREFIX
   ```

5. 预编译包制作
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py package libde265 1.0.15
   ```
   打包成功，生成：
   - libde265-1.0.15-ohos-aarch64.tar.gz (4.2M)
   - libde265-1.0.15-ohos-aarch64-debug.tar.gz (617K)

6. 本地安装验证
   ```bash
   make install  # 不带 DESTDIR，安装到 $DEFAULT_PREFIX
   ```
   pkg-config --modversion libde265 显示版本 1.0.15

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure 失败：lld 链接器缺少 libxml2 | LD_LIBRARY_PATH 未包含 Ohos SDK 的 llvm/lib | 添加 `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib` 到 LD_LIBRARY_PATH |
| 2 | CMake 无法识别 HarmonyOS 系统 | CMake 版本较旧，不支持 HarmonyOS | 不阻塞，继续构建（只是警告） |
| 3 | G0 干净构建验证失败：找不到 configure | G0 默认使用 autotools，但本项目是 CMake | 创建 `hints/configure` 脚本包装 cmake |

## 源码修改

无源码修改（CMake 构建不需要修改 CMakeLists.txt）

补丁：0001-CMakeLists.txt.patch（之前的归档，本次未使用）

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- lld: 15.0.4（依赖 libxml2）
- libxml2: 2.14.0
- SDL2: 2.0（可选依赖，未启用）

## 验证结果

```bash
# pkg-config 验证
pkg-config --modversion libde265
# 输出: 1.0.15

# 文件验证
ls -lh $DEFAULT_PREFIX/bin/dec265
# -rwxrwx--- 1 ... 42K ... dec265

ls -lh $DEFAULT_PREFIX/lib/libde265.so
# -rwxrwx--- 1 ... 834K ... libde265.so
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libde265-1.0.15-ohos-aarch64.tar.gz | 4.2M | 预编译包（已签名、已 strip） |
| libde265-1.0.15-ohos-aarch64-debug.tar.gz | 617K | 调试符号包 |

包含内容：
- bin/dec265
- lib/libde265.so (动态库)
- lib/libde265.a (静态库)
- lib/external/libSDL2-2.0.so.0 (可选依赖)
- include/libde265/*.h (头文件)
- lib/cmake/libde265/*.cmake (CMake 配置)
- lib/pkgconfig/libde265.pc (pkg-config 文件)

## 注意事项

1. **构建系统选择**：libde265 支持 autotools 和 CMake 两种构建系统。在 HMDFS 文件系统上，推荐使用 CMake 构建，避免 autotools 的临时文件权限问题。

2. **环境变量**：必须设置 LD_LIBRARY_PATH 包含 Ohos SDK 的 llvm/lib，否则 lld 链接器无法找到 libxml2。

3. **G0 验证**：CMake 项目需要创建 `hints/configure` 脚本来包装 cmake，以支持 SKILL 的 G0 干净构建验证流程。

4. **无补丁**：本次编译未修改源码，CMakeLists.txt 默认配置即可正常编译。

## 编译结束

**编译时间**: 2026-05-30 09:30-09:33
**最终状态**: built
**编译方案**: CMake
---

**编译结束**: 2026-05-30 09:39
**最终状态**: built
