# libplayerone 3.1.0 适配笔记

## 编译环境
- 构建系统: install-imported（上游无可编译源码，纯安装型预编译包）
- 编译日期: 2026-09-17
- 目标架构: aarch64 (armv8, OHOS 6.0)
- 状态: built

## 包内容

libplayerone 是 Player One Astronomy (POA) 天文相机的官方 C SDK。上游按架构
分发厂商闭源预编译二进制（`.bin`）+ 自包含头文件 + udev 规则，上游
CMakeLists 仅 `add_library(PlayerOneCamera SHARED IMPORTED)` +
`install_imported`，**无任何构建目标**——本包是纯安装型交付：

- `lib/libPlayerOneCamera.so.3` — 厂商 aarch64 共享库（`armv8/libPlayerOneCamera.bin`
  重命名为其自身 SONAME 名，`llvm-readelf -d` 确认 SONAME 为
  `libPlayerOneCamera.so.3`）
- `lib/libPlayerOneCamera.so` — 符号链接（使 `-lPlayerOneCamera` 可链接解析，
  与上游 install_imported 的 NAMELINK 行为一致）
- `include/libplayerone/PlayerOneCamera.h` — 公共头文件（上游 CMake 安装位置）
- `lib/udev/rules.d/99-player_one_astronomy.rules` — USB 设备 udev 规则
- `licenses/license.txt` — MIT 许可证（上游 `license.txt`，spec 文件
  `License: MIT`）

## 源码选择

- 主源: Debian salsa 官方上游快照 tag
  `upstream/3.1.0+20221218103507` 的 tarball（含全部厂商二进制 + 头文件 +
  udev 规则 + 许可证；sha256 已验证，2026-09-17 下载成功）
- 备选 1（未采用）: cica 镜像的 Debian `.orig` 包
  `libplayerone_3.1.0+20221218103507.orig.tar.gz` —— 当前持续下载损坏
  （gzip inflate EOF，两次重试均失败）
- 备选 2（未采用）: GitHub `indilib/indi-3rdparty` 的 `libplayerone/` 子目录
  —— 无 tag 可直取，且 `.bin` 是 git-lfs 指针文件（需 lfs 拉取）
- 版本语义: Debian 源版本 `3.1.0+20221218103507` 的基版本即 3.1.0
  （`+20221218103507` 是厂商 SDK 的构建时间戳）

## 遇到的问题与解决方案

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| conan create 报 package_type 警告 | `package_type='shared-library'` 与 `shared` option 并存时 conan 提示 option 被忽略 | 保留 warning（shared-library 语义正确），配方在 validate() 拒绝 shared=False |
| 厂商 .bin 文件后缀是 .bin | 厂商按 `lib<Name>.bin` 命名，实际是 ELF 共享库（SONAME `libPlayerOneCamera.so.3`） | package() 复制后重命名为 SONAME 名并建 .so 符号链接 |
| CI 沙箱 dlopen 厂商 .so 报 Permission denied | 容器禁止对外部加载的 .so 做 mmap PROT_EXEC（改名 .so + chmod 755 后仍拒）；且厂商库需物理 POA 相机经 USB 连接 | test_package 不用运行时测试：头文件编译 + ELF 静态校验（llvm-readelf/llvm-nm）+ OHOS clang 真实下游链接（R34） |
| salsa 下载偶发 429 | salsa.debian.org 对 tarball 端点限流（瞬态） | conan create 重试即可（429 → 200，sha256 一致）；conan 内置下载器用 urllib 不受本容器 subprocess PATH 失效影响 |
| 3.1.0 头文件 API 与文档常见示例不符 | 3.1.0 无 `POAGetCameraName`/`POCOpenCamera`（早期/其它 SDK 的命名），实际是 `POAOpenCamera`/`POAGetCameraProperties` | 探针与断言全部以 3.1.0 头文件实际声明为准 |

## 验证结果

- `conan create` (ohos-aarch64): PASS — 包 ID `92d86a7399272b268f4bdf51b580cb28cefd75cc`，
  打包 5 个文件（.so.3 / .so 链接 / .h / .rules / license.txt）
- `conan test` (test_package): PASS — 21/21 断言通过
- `ci/conan/build_and_test.sh` (CI_PACKAGES 定向, prdiff 模式):
  - G0 / G0e: PASS（知识图谱完整性 + 根目录白名单）
  - JC: PASS（杂项文件拦截，含 JC6 单软件原子性）
  - L0: PASS（质量门禁，含 L0d self.run 真实执行检查、L0i 注册表依赖检查
    `libusb/1.0.27`、L0m 目录结构）
  - L1: PASS（test_package 经 conan create 真实执行）
  - L2: SKIP（无 bin/ 目录，库包）
  - L4: PASS（无补丁，无补丁安全扫描）
  - L5: PASS（lib/ 有内容）
  - Build Summary: Success 1/1, Pass rate 100.0%
