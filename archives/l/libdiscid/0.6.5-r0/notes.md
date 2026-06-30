# libdiscid 0.6.5-r0 适配笔记

## 编译环境
- 构建系统: cmake (CMakeLists.txt)
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4 / clang++ (未使用)
- 平台: HarmonyOS aarch64 (generic — 无 disc reading)
- 状态: published

## 编译步骤

### 模式 B 手动编译（模式 A auto build 在 make 步骤失败后切换）

1. **cmake configure**:
   ```bash
   mkdir -p build && cd build
   cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
         -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_C_FLAGS="-fPIC -O2" \
         ..
   ```
   - cmake 检测到 HarmonyOS 为 unknown OS → 使用 generic 实现 (disc_generic.c)
   - "System is unknown to cmake" 警告不影响构建，可忽略

2. **make**:
   ```bash
   cd build && make -j1
   ```
   - 编译产物: libdiscid.so, discid (示例程序), discisrc (示例程序)

3. **make install DESTDIR** (staging 隔离):
   ```bash
   cd build && make install DESTDIR=/storage/Users/currentUser/tmp/test-install-libdiscid-0.6.5-r0
   ```
   - 产物安装到: $TEST_PREFIX/$DEFAULT_PREFIX/lib/, lib/pkgconfig/, include/discid/

4. **make check** (手动执行):
   ```bash
   LD_LIBRARY_PATH=./:$LD_LIBRARY_PATH ./test_core   # 7/7 passed
   LD_LIBRARY_PATH=./:$LD_LIBRARY_PATH ./test_put    # 7/7 passed
   LD_LIBRARY_PATH=./:$LD_LIBRARY_PATH ./test_read   # SKIP (预期, 无 disc reading)
   LD_LIBRARY_PATH=./:$LD_LIBRARY_PATH ./test_read_full # SKIP (预期)
   ```
   - `make check` 命令行执行失败（缺少 LD_LIBRARY_PATH 设置）
   - 手动设置 LD_LIBRARY_PATH 后测试全部通过

5. **make install** (本地安装，模拟用户部署):
   ```bash
   cd build && make install
   ```
   - 安装到 ~/usr/local/lib/libdiscid.so, ~/usr/local/lib/pkgconfig/libdiscid.pc, ~/usr/local/include/discid/discid.h

6. **验证本地安装**:
   ```bash
   pkg-config --modversion libdiscid  # 0.6.5
   readelf -d libdiscid.so            # NEEDED: libc.so (仅依赖 libc)
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake configure 失败: `config-cmake.h.in does not exist` | 源码 .work 目录中缺少 config-cmake.h.in 文件（tarball 包含但提取丢失） | 手动创建 config-cmake.h.in，包含 cmake 模板变量 (${PACKAGE_STRING}, ${SIZEOF_LONG}, ${PACKAGE}, ${VERSION}, WORDS_BIGENDIAN) |
| 2 | make 失败: `PACKAGE_STRING undeclared` | 原始 config-cmake.h.in 只定义 PACKAGE_STRING（用 @...@ 语法）和 SIZEOF_LONG，缺少 PACKAGE 和 VERSION；且 @...@ 语法的 PACKAGE_STRING 也需改为 ${...} 语法 | 更新 config-cmake.h.in 使用 cmake ${...} 语法，增加 PACKAGE 和 VERSION 定义 |
| 3 | `make check` 命令行失败 | 运行时缺少 LD_LIBRARY_PATH，libdiscid.so 无法加载 | 手动设置 `LD_LIBRARY_PATH=build_dir:$LD_LIBRARY_PATH` 执行测试 |
| 4 | ohc-run.py build auto 模式 make 步骤失败 | build 脚本从错误的 build 目录运行 make (`libdiscid-0.6.5-r0-build` 不存在) | 切换到模式 B 手动编译 |
| 5 | G0 clean-verify 失败 | clean-verify 脚本仅支持 autotools configure，不支持 cmake | 手动执行 cmake clean-verify（从原始 tarball 解压 → 打补丁 → cmake → make → 成功） |
| 6 | verify-build G4 失败: `manifest 缺少 build_system` | manifest 使用 `build.system: cmake` 嵌套格式，verify-build 期望 `build_system: cmake` 顶级字段 | 在 manifest.yaml 顶级添加 `build_system: cmake` |

## 源码修改

- **0001-config-cmake.h.in.patch**: 重写 config-cmake.h.in
  - 原始文件使用 autotools @...@ 变量语法（`@PACKAGE_STRING@`、`@SIZEOF_LONG@`）
  - 修改后使用 cmake ${...} 变量语法（`${PACKAGE_STRING}`、`${SIZEOF_LONG}`）
  - 新增 PACKAGE 和 VERSION 定义（`${PACKAGE}`、`${VERSION}`）
  - 新增 CONFIG_H 头文件守卫
  - 变量补充: disc.c 通过 HAVE_CONFIG_H 宏使用 PACKAGE_STRING，需要 config.h 中完整定义

## 依赖版本

- 编译器: clang 15.0.4 (无额外依赖)
- libc: 系统 libc.so (仅此一个运行时依赖)
- cmake: cmake version 4.1.2
- make: GNU Make 4.4.1
- 无第三方库依赖

## 验证结果

```bash
# pkg-config 验证
$ export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
$ pkg-config --modversion libdiscid
0.6.5
$ pkg-config --libs libdiscid
-L/storage/Users/currentUser/usr/local/lib -ldiscid
$ pkg-config --cflags libdiscid
-I/storage/Users/currentUser/usr/local/include

# readelf 验证 (仅依赖 libc)
$ readelf -d ~/usr/local/lib/libdiscid.so | grep NEEDED
 0x0000000000000001 (NEEDED)   Shared library: [libc.so]

# 测试验证 (test_core + test_put)
$ LD_LIBRARY_PATH=./:$LD_LIBRARY_PATH ./test_core
Testing discid_get_version_string ... OK
Testing discid_get_feature_list ... OK
Testing discid_get_default_device ... OK
Testing discid_new ... OK
Testing giving invalid device ... OK
Testing discid_get_error_msg ... OK
Testing discid_free ... OK
7 tests, 7 passed, 0 failed

$ LD_LIBRARY_PATH=./:$LD_LIBRARY_PATH ./test_put
Testing discid_put_verification ... OK
Testing discid_put ... OK
Testing discid_get_id ... OK
Testing discid_get_freedb_id ... OK
Testing discid_get_toc_string ... OK
Testing discid_get_submission_url ... OK
Testing discid_get_error_msg ... OK
7 tests, 7 passed, 0 failed

# G0 手动 clean-verify
从原始 tarball → 应用 0001-config-cmake.h.in.patch → cmake configure → make → 成功
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libdiscid-0.6.5-r0-ohos-aarch64.tar.gz | 99KB | 预编译包 (lib, include, pkgconfig) |
| libdiscid-0.6.5-r0-ohos-aarch64-debug.tar.gz | 27KB | debug 符号包 |
| 0001-config-cmake.h.in.patch | — | cmake 配置头模板补丁 |

## 注意事项

- HarmonyOS 平台为 "generic" OS，**disc reading 功能不可用**（test_read/test_read_full 测试跳过是预期行为）
- cmake 不识别 HarmonyOS 系统名，输出 "System is unknown to cmake" 警告不影响构建
- 原始 tarball 包含 config-cmake.h.in 但使用 autotools @...@ 语法，需改为 cmake ${...} 语法
- ohc-run.py clean-verify (G0) 仅支持 autotools，cmake 项目需手动验证
- 本库仅依赖 libc，无其他运行时依赖

## 功能测试（2026-06-02 补充）

编写 C 语言功能测试程序覆盖 8 组 40 个测试项，全部通过：

| 测试组 | 项数 | 结果 | 关键发现 |
|--------|------|------|----------|
| 基础对象生命周期 | 5 | PASS | discid_new/free 正常，NULL 安全 |
| 版本与特性查询 | 7 | PASS | 版本 "libdiscid 0.6.5"，generic 无 disc reading |
| 默认设备查询 | 1 | PASS | 返回 /dev/null |
| discid_put DiscID 计算 | 16 | PASS | offsets[0]=lead-out, offsets[track]=偏移；Invalid offset 错误处理正确 |
| discid_read 磁盘读取 | 3 | PASS | 预期失败："not implemented on this platform" |
| pkg-config 集成 | 3 | PASS | 编译链接运行均成功 |
| 多对象并发 | 3 | PASS | 5 对象同时 put，相同 TOC→相同 ID（确定性） |
| 边界条件 | 2 | PASS | 10-track put 成功，空对象查询安全 |

详细报告: `reports/functional-test-report.md`

**上库结论**: 🟢 符合上库要求（published + G0-G4 PASS + 40/40 功能测试通过 + ELF 签名 + pkg-config 可用）

## 对话记录

### 2026-06-02 Session 1: 重做编译

- **Phase 1**: init-build → 清理旧归档 → 重新初始化
- **Phase 2**: cmake configure (耗时 ~3s) → cmake 参数: `-DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS="-fPIC -O2"`
- **Phase 3**: 手动 make → 创建 config-cmake.h.in 补丁 → make check (14 pass, 4 skip)
- **Phase 4**: package → verify-build G1-G4 PASS → finish → published
---

**编译结束**: 2026-06-02 11:08
**最终状态**: published
