# intel-hdcp 21.2.0 适配笔记（r02）

## 上游信息
- 仓库: https://github.com/intel/hdcp
- 版本: 21.2.0（r02 按分析端确认重置为全小写 slug；上游 release 名 `intel-HDCP-21.2.0` 不改写）
- 上游 release commit: `cacc352159c5bdaf1c21846cecdd1eb7b031e1d3`（tag intel-HDCP-21.2.0 peeled）
- 源码 tarball SHA-256: `243e7548745f1dd9b3e092152a3a60bb3a903d8c08254cb307d6be3c2c0858b8`
- 语言: C++（13 cpp / 14 h），lang-preflight 判定 cpp
- 构建系统: CMake（cmake_minimum_required 2.8.12，强制 out-of-tree）

## 三子工程与构建归属
| 子工程 | 形态 | 依赖 | 交付归属 |
|--------|------|------|---------|
| common/ | 静态库 libcommon（clientsock/gensock/servsock/socketdata） | 配置期 find_package(OpenSSL REQUIRED)+Threads（代码未直接用 OpenSSL API） | SDK 内部 |
| sdk/ | 共享库 libhdcpsdk.so（hdcpapi/session/sessionmanager） | Threads + common | **交付核心**（install: libhdcpsdk.so*、hdcpapi.h、libhdcpsdk.pc） |
| daemon/ | 可执行 hdcpd（main/daemon/port/srm/portmanager/display_window_util_wl） | OpenSSL + Threads + libdrm(pkg-config) + dl + Wayland/EGL 头文件 + systemd | **OHOS 排除** |

## daemon 排除决策（补丁 0001-optional-daemon.patch）
- daemon 编译强依赖 `wayland-client.h`/`wayland-egl.h`（daemon/global_wayland.h）与 systemd 单元；
  OHOS sysroot（/data/service/hnp/ohos-sdk_26.0.0.18/.../sysroot/usr/include）无 wayland 头文件
  （EGL 头存在），且 hdcpd 面向 Intel IAS Wayland compositor（dlopen libwl_base.so）与 i915 DRM，
  OHOS 无对应图形栈。
- 补丁将 daemon 的 add_subdirectory、hdcpd install、systemdservice include 置于 `HDCP_BUILD_DAEMON`
  选项之后；配方 generate() 固定 `HDCP_BUILD_DAEMON=OFF`，交付 SDK 库形态（R38：库类型不需要 commands.json）。
- 补丁 sha256: `17aa11aa3fed0019a948f104ea6ab3ff0d5842bc2bbae54ecd22321b4e5b6d49`

## 依赖
- openssl/3.5.6 — common/daemon CMake 配置期 find_package(OpenSSL REQUIRED)；W0 探测 ohpcd 已发布
- libdrm/2.4.133 — 仅 daemon pkg_check_modules(LIBDRM REQUIRED) 使用，daemon 排除后不再需要（W0 已发布留档）

## 测试
- 上游：官方 release 无独立测试套件（无 tests/ 目录、无 ctest 注册）——按 R51 清点，台账见 notes 上游测试台账
- 适配后：test_package/example.c 真实调用 SDK API 参数校验路径
  （HDCPCreate(NULL,...) / HDCPGetStatus(...,NULL) → HDCP_STATUS_ERROR_INVALID_PARAMETER），
  无需 daemon 即可确定性验证符号链接与 ABI

## r02 变化（相对 r01）
- version/source_branch/归档目录重置为小写 slug：21.2.0 / feat/intel-hdcp-21.2.0 / archives/i/intel-hdcp/21.2.0/
- 补入软件级 archives/i/intel-hdcp/{commands.json,README.md,manifest.yaml} 白名单（commands.json 库类型不需要，不交付）
- r02 采用独立 worktree build_in_harmonyos-intel-hdcp-21.2.0（r01 大写分支 worktree 不复用）

## 已知限制
- hdcpd daemon 在 OHOS 不可构建/无运行环境（Wayland + systemd + IAS compositor），属平台能力缺失，非当前库缺陷
---

**编译结束**: 2026-09-22 20:14
**最终状态**: built
