# jshn 2025.11.14 适配笔记

## 编译环境
- 构建系统: cmake（继承自libubox）
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: built
- 所属项目: libubox
- Git commit: a75209f (2025-11-14)

## 版本定位

**重要说明**：jshn不是独立软件包，jshn 2025.11.14版本基于libubox项目在2025-11-14的Git提交。

**版本查找过程**：
```bash
git clone https://git.openwrt.org/project/libubox.git
cd libubox
git log --since="2025-11-14" --until="2025-11-15" --oneline
# 输出: a75209f blobmsg: refactor blobmsg_cast_u64/s64
git checkout a75209f
```

**版本确定**：使用commit a75209f（2025-11-14提交）作为"2025.11.14"版本基础

## 编译步骤

1. **安装依赖**：使用json-c预编译包（v0.16）
   ```bash
   curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- json-c 0.16
   ```

2. **克隆libubox源码并定位版本**：
   ```bash
   git clone https://git.openwrt.org/project/libubox.git ~/tmp/builds/libubox-2025.11.14.work
   cd ~/tmp/builds/libubox-2025.11.14.work
   git checkout a75209f
   ```

3. **应用补丁（关键步骤）**：
   ```bash
   cp archives/l/libubox/master/patches/0001-CMakeLists.txt.patch ./
   patch -p1 < 0001-CMakeLists.txt.patch
   # 补丁解决cmake硬编码库路径问题
   ```

4. **配置cmake**：
   ```bash
   export DEFAULT_PREFIX="/storage/Users/currentUser/usr/local"
   export PKG_CONFIG_PATH="$DEFAULT_PREFIX/lib/pkgconfig:$PKG_CONFIG_PATH"
   export CMAKE_LIBRARY_PATH="$DEFAULT_PREFIX/lib:$CMAKE_LIBRARY_PATH"

   cmake .. \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DBUILD_LUA=OFF \
     -DBUILD_EXAMPLES=OFF \
     -DCMAKE_INSTALL_RPATH='$ORIGIN/../lib:$ORIGIN/../lib/external' \
     -DCMAKE_BUILD_WITH_INSTALL_RPATH=TRUE
   ```

5. **编译**：
   ```bash
   make -j2
   # 编译成功
   ```

6. **验证NEEED字段（关键检查）**：
   ```bash
   readelf -d build/jshn | grep NEEDED
   # 输出: [libjson-c.so] ✅ 相对路径（补丁生效）
   ```

7. **设置RUNPATH（手动）**：
   ```bash
   patchelf --set-rpath '$ORIGIN/../lib:$ORIGIN/../lib/external' build/jshn
   ```

8. **安装到staging目录**：
   ```bash
   export TEST_PREFIX="$HOME/tmp/test-install-jshn-2025.11.14"
   make install DESTDIR=$TEST_PREFIX
   ```

9. **创建jshn独立预编译包**：
   ```bash
   mkdir -p ~/tmp/jshn-2025.11.14-pkg/{bin,lib/external,share/jshn}
   cp $TEST_PREFIX/$DEFAULT_PREFIX/bin/jshn ~/tmp/jshn-2025.11.14-pkg/bin/
   cp $TEST_PREFIX/$DEFAULT_PREFIX/lib/libblobmsg_json.so ~/tmp/jshn-2025.11.14-pkg/lib/
   cp $TEST_PREFIX/$DEFAULT_PREFIX/lib/libubox.so ~/tmp/jshn-2025.11.14-pkg/lib/
   cp ~/usr/local/lib/libjson-c.so ~/tmp/jshn-2025.11.14-pkg/lib/external/
   cp $TEST_PREFIX/$DEFAULT_PREFIX/share/libubox/jshn.sh ~/tmp/jshn-2025.11.14-pkg/share/jshn/

   cd ~/tmp/jshn-2025.11.14-pkg
   tar -czf jshn-2025.11.14-ohos-aarch64.tar.gz *
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake找不到json-c | PKG_CONFIG_PATH未设置 | export PKG_CONFIG_PATH |
| 2 | cmake find_library返回NOTFOUND | CMAKE_LIBRARY_PATH未设置 | export CMAKE_LIBRARY_PATH |
| 3 | NEEDED硬编码绝对路径（首次编译） | cmake使用find_library结果 | 应用补丁：使用JSONC_LIBRARIES变量 |
| 4 | RUNPATH未自动设置 | cmake RPATH设置未生效 | 手动使用patchelf设置 |
| 5 | lua构建失败 | BUILD_LUA默认为ON | cmake配置添加 -DBUILD_LUA=OFF |

## 补丁说明

**补丁文件**：`0001-CMakeLists.txt.patch`（继承自libubox master）

**补丁作用**：解决cmake硬编码库路径问题

**关键修改**：
```diff
-find_library(json NAMES json-c)  # 返回绝对路径
-IF(EXISTS ${json})
+IF(JSONC_FOUND)                  # 使用pkg-config
-TARGET_LINK_LIBRARIES(blobmsg_json ubox ${json})  # 硬编码
+TARGET_LINK_LIBRARIES(blobmsg_json ubox ${JSONC_LIBRARIES})  # 库名
+TARGET_LINK_DIRECTORIES(blobmsg_json PRIVATE ${JSONC_LIBRARY_DIRS})
```

**效果验证**：
- ✅ 首次编译：NEEDED显示`/storage/Users/currentUser/usr/local/lib/libjson-c.so`（硬编码）
- ✅ 应用补丁后：NEEDED显示`[libjson-c.so]`（相对路径）

## 依赖关系

jshn依赖以下库：
- libblobmsg_json.so（JSON blob处理）
- libjson-c.so（JSON C库，外部依赖）
- libubox.so（OpenWrt核心库）
- libc.so（系统库）

所有依赖已包含在预编译包中：
- libblobmsg_json.so、libubox.so位于lib/
- libjson-c.so位于lib/external/

## 验证结果

```bash
# 预编译包验证
cd ~/tmp/verify-jshn-2025.11.14
tar -xzf jshn-2025.11.14-ohos-aarch64.tar.gz

# 依赖检查
readelf -d bin/jshn | grep NEEDED
# 输出: [libblobmsg_json.so], [libjson-c.so], [libubox.so], [libc.so] ✅ 全部相对路径

# RUNPATH检查
readelf -d bin/jshn | grep RUNPATH
# 输出: [$ORIGIN/../lib:$ORIGIN/../lib/external] ✅ 正确

# 外部依赖检查
ls -lh lib/external/libjson-c.so
# 输出: 98K ✅ 存在

# 功能测试
export LD_LIBRARY_PATH="$PWD/lib:$PWD/lib/external:$LD_LIBRARY_PATH"
./bin/jshn
# 输出: Usage: ./bin/jshn [-n] [-i] -r <message>... ✅ 正确
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| jshn-2025.11.14-ohos-aarch64.tar.gz | 510KB | jshn独立预编译包 |

预编译包内容：
- bin/jshn (47KB)
- lib/libblobmsg_json.so (43KB)
- lib/libubox.so (230KB)
- lib/external/libjson-c.so (98KB)
- share/jshn/jshn.sh (5.8KB)

## 注意事项

1. **组件性质**: jshn是libubox的组件，推荐安装完整libubox包以获得更多功能
2. **依赖完整**: jshn预编译包已包含所有必要依赖，可独立运行
3. **Shell脚本**: 使用jshn.sh需source脚本：`source ~/usr/local/share/jshn/jshn.sh`
4. **RPATH设置**: 预编译包已设置RPATH，无需手动设置LD_LIBRARY_PATH
5. **版本标识**: 2025.11.14基于libubox commit a75209f（2025-11-14提交）

## 与libubox的关系

| 方面 | jshn 2025.11.14 | libubox 2025.11.14 |
|------|----------------|-------------------|
| 源码位置 | libubox.git | libubox.git |
| Git commit | a75209f | a75209f |
| 编译方式 | 随libubox编译 | 独立编译 |
| 包大小 | 510KB | 约900KB |
| 功能范围 | JSON shell工具 | 完整工具库 |
| 推荐安装 | 基础使用 | 高级功能 |

---
**编译结束**: 2026-05-29 15:55
**最终状态**: built
**源项目**: libubox commit a75209f (2025-11-14)