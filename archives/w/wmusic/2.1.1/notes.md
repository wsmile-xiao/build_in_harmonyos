# wmusic 2.1.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-29
- 编译器: clang 15 / clang++ 15
- 状态: built

## 编译步骤

1. 下载并解压 `wmusic-2.1.1.tar.gz`（来自 dockapps.net）
2. 使用 conan 安装依赖（libdockapp/0.7.3, playerctl/2.4.1, libx11/6.4.0, libxpm/3.5.17, libxext/6.4.0, xorgproto/2025.1, glib/2.84.0.1 等）
3. 通过 CMake 的 `PkgConfigDeps + AutotoolsDeps + AutotoolsToolchain` 生成器传递依赖信息
4. 配置时用 `/system/bin/sh` 执行 configure，并设置 `--host=aarch64-linux-ohos` 避免运行 conftest 二进制
5. 修复 `umask 077` → `umask 022`（FUSE/HMDFS 忽略 chmod，mkdtemp 创建 0700 目录会使子进程 getcwd EACCES）
6. 编译并打包

### 关键修复

- **`playerctl/playerctl.h` 找不到**：playerctl conan recipe 的 `cpp_info.includedirs` 未正确设置，CMakeDeps 生成的 find_package 无法找到头文件。解决方案：在 test_package 中改用 `PkgConfigDeps` + CMake `pkg_check_modules` 读取 `.pc` 文件
- **`playerctl_player_manager_new` API 签名错误**：文档示例与实际头文件不符（2.4.1 版本只接受 `GError **` 单参数）。修正为 `playerctl_player_manager_new(&error)`
- **`playerctl_player_manager_get_players` 不存在**：实际 API 通过 GObject property `"player-names"` 获取玩家列表，使用 `g_object_get` 读取
- **OHOS sandbox 无 D-Bus**：`playerctl_player_manager_new` 在 sandbox 中因缺少 `/var/lib/dbus/machine-id` 而失败。消费者代码处理此情况为正常（headers 编译链接已验证）

## 源码修改

无补丁（路径 A：纯基础适配）

## 依赖版本

- libdockapp/0.7.3
- playerctl/2.4.1
- libxpm/3.5.17
- libx11/6.4.0
- libxext/6.4.0
- xorgproto/2025.1
- xtrans/1.6.0
- libxcb/1.16
- libxau/1.0.11
- libxdmcp/1.1.5
- glib/2.84.0.1
- pcre2/10.45
- libffi/3.4.4
- zlib/1.3.1.1

## 验证结果

### conan create
```
✅ G2: PASS (conan create 干净构建)
✅ G3: PASS (系统同名库隔离验证)
✅ G4: PASS (产物完整性检查)
✅ L2: PASS (平台功能矩阵/smoke test)
✅ L4: PASS (静态安全扫描)
✅ L5: PASS (产物基线对比)
```

### test_package
- ARTIFACT layer: AArch64 ELF ✅, .codesign ×1 ✅, bare sonames ✅, no host prefix leak ✅
- HarmonyOS consumer: 编译 ✅, 链接 ✅, 执行 ✅（headers OK, D-Bus 不可达为预期）
- Loader-process smoke: 二进制存在 ✅, AArch64 ELF ✅, version banner ✅

### 产物
- Package folder: `/data/storage/el2/base/cache/conan-home/p/b/wmusi*/p/bin/wmusic`
- AArch64 ELF, 41 个 DT_NEEDED 条目（全部 bare sonames，无绝对路径泄漏）

## 交付物

| 文件 | 说明 |
|------|------|
| conandata.yml | 源码 URL + SHA256 |
| conanfile.py | OHOS 交叉编译配方 |
| manifest.yaml | 构建元数据 |
| test_package/ | 三层测试套件 |
| commands.json | CLI 工具声明 |

## 注意事项

- wmusic 是 X11 GUI dockapp，需要在 X server 环境下运行
- test_package 消费者在 OHOS sandbox 中因无 D-Bus 无法初始化 playerctl manager，但已验证编译链接正确
- 上游无自动化测试（no tests/ directory, no check_PROGRAMS, no TESTS in Makefile.am）

### 对话 #1 [2026-09-29]

- 问题：wmusic 2.1.1 需在 OHOS PC 上完成 autotools 交叉编译适配，依赖链较深（libdockapp、playerctl → glib/X11 全家桶）
- 操作：
  - worktree `~/.scratch/wt-wmusic` 从 origin/main 建分支 feat/wmusic-2.1.1
  - R36 核验 9 个直接/传递依赖均可从 ohpcd 消费
  - 编写 conanfile.py：PkgConfigDeps + AutotoolsDeps + AutotoolsToolchain；`--host=aarch64-linux-ohos`；umask 077→022
  - test_package 三层：artifact 检查 / HarmonyOS 消费者（真实调用 playerctl API，非断言）/ loader-process smoke
  - conan create → conan-verify（G0-G4 + L2/L4/L5）→ finish → W2/W3
- 结果：
  - conan create 全绿，包产物 AArch64 ELF（41 个 bare sonames，无 host prefix 泄漏）
  - conan-verify PASS；W3 本地 CI 100%（JC 增量模式）；W2 仅 10+ 配方文件无框架混入
  - 关键坑：playerctl 配方 cpp_info.includedirs 为空导致 CMakeDeps 找不到头文件 → test_package 改用 pkg_check_modules；playerctl 2.4.1 API 实际签名与文档不符（manager_new 只收 GError**；players 列表走 GObject property "player-names"）
---

**编译结束**: 2026-09-29 10:39
**最终状态**: built
