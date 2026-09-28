# lwext4 1.0.0 适配笔记

## 上游信息

- 仓库: https://github.com/gkostka/lwext4
- 正式标签: `v1.0.0` → commit `890484c72dbb321535127625c3686e51f1f424b9`（GitHub API 核验）
- 官方归档: https://github.com/gkostka/lwext4/archive/refs/tags/v1.0.0.tar.gz
- sha256: `0991d092e46adb4f11898f47776816a9ac65aeb4e5175f477ba73301e82eb14a`
- 许可证: LICENSE 声明 GPL-2.0（部分文件各自携带许可证声明）
- 构建系统: CMake（`cmake_minimum_required(VERSION 2.8)`，LIB_ONLY 分支只建库）
- 语言: 纯 C（lang-preflight 通过，milestone=lang_checked）

## 环境要点

- 本机无法直连 github.com（443 超时），源码经 gh-proxy.com 官方镜像下载
- init-build 默认判定 autotools（由 URL 推断），实际为 CMake；conan-init 生成了
  autotools 模板 → 已手改为 CMake 配方
- `~/tmp/builds` 不是 TMPDIR 实际位置（TMPDIR=/storage/Users/currentUser），
  init-build 的 build_dir 是 `$TMPDIR/builds`；归档需预置到该路径跳过下载

## 适配要点

1. **CMAKE_POLICY_VERSION_MINIMUM=3.5**：上游 cmake_minimum_required(2.8) 被
   cmake 4.1 拒绝（"Compatibility with CMake < 3.5 has been removed"），
   generate() 注入该变量解决。
2. **LIB_ONLY=TRUE**：只构建库目标 lwext4 + blockdev，跳过 fs_test 示例
   （fs_test/CMakeLists.txt 的 install 规则把工具装到 /usr/bin，库本身无 install）。
3. **package() 手动复制**：上游无库安装规则；复制 liblwext4.a 到 lib/，
   递归复制 build 期生成 include/ 下的公共头（含 generated/ext4_config.h——
   include/ext4_config.h 在 CONFIG_USE_DEFAULT_CFG 未定义时 `#include
   "generated/ext4_config.h"`，该文件由 output_configure() 写入
   ${PROJECT_BINARY_DIR}/include/generated/）。
4. **test_package**：R34 实质测试——EXT4_BLOCKDEV_STATIC_INSTANCE 内存 RAM
   块设备，走 mkfs → mount → fopen/fwrite/fread/fclose → umount 全流程，
   断言写读回读一致。

## 上游测试

- fs_test.mk 定义 t0-t26 共 27 个测试目标，client/server 架构（lwext4-client
  向 lwext4-server 发命令），依赖 ext_images.7z（7z 压缩的 100MB ext2/3/4 镜像）。
- 已登记 MANIFEST.yml（lwext4-client / lwext4-server / lwext4-mkfs /
  lwext4-generic）。

## 门禁结论（待 conan-verify/finish 更新）

- 手动编译验证: 通过（clang 15，cmake 4.1 + CMAKE_POLICY_VERSION_MINIMUM=3.5）
- 待办: conan-verify（G0-G4+L2/L4/L5）、finish、W2/W3
---

**编译结束**: 2026-09-26 21:23
**最终状态**: published
