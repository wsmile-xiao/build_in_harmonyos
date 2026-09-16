# GNU ccRTP

GNU ccRTP 是一个基于 GNU uCommon/Common C++ 框架的 C++ RTP（实时传输协议）库，提供 RTP/RTCP 会话管理、分组收发与 SRTP 加密能力。

## 基本信息

- **名称**: ccrtp
- **许可证**: GPL-2.0-or-later
- **官方网站**: https://www.gnu.org/software/ccrtp/
- **源码仓库**: https://ftp.gnu.org/gnu/ccrtp/

## HarmonyOS 编译状态

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.0.2 | ✅ built | 2026-09-02 | autotools 构建，基于 commoncpp2 1.8.1（依赖 zlib/openssl） |
| 2.1.2 | ✅ built | 2026-09-06 | autotools 构建，基于 conan ucommon/7.0.1（--disable-srtp） |

## 构建配置

- **构建系统**: autotools
- **编译器**: clang 15 (cppstd=17)
- **配置选项**: `--disable-srtp`（SRTP 为可选加密层，上游在缺少 libgcrypt/OpenSSL 时硬失败）
- **依赖**:
  - 1.0.2: commoncpp2/1.8.1（需 zlib/1.3.1、openssl/1.1.1w，已在 OHOS 发布）
  - 2.1.2: ucommon/7.0.1（制品仓已发布；提供 commoncpp 兼容层，commoncpp.pc Version 7.0.1 >= 6.2.2 满足 configure 要求）

## 安装

```bash
# 使用 conan 引用
conan install --requires=ccrtp/2.1.2 -pr:h=ohos-aarch64
```

## 编译笔记

详见 [2.1.2/notes.md](2.1.2/notes.md)。

## 补丁

本版本使用的补丁（详见 [2.1.2/patches](2.1.2/patches)）：
- `0001-autoconf-config.guess.patch` — config.guess 识别 HarmonyOS → `aarch64-unknown-linux-ohos`（E007）
- `0002-autoconf-config.sub.patch` — config.sub 接受 `-linux-ohos*` 三元组
- `0003-configure.patch` — 无条件定义 SRTP_OPENSSL/SRTP_GCRYPT automake 条件（支持 `--disable-srtp`）+ config.status 临时目录 umask 022（E129 HMDFS setgid）
- `0004-src-CryptoContextCtrl.cpp.patch` — 显式 include `ccrtp/CryptoContext.h`（SRTP 关闭时 SrtpEncryptionNull/SrtpAuthenticationNull 在守卫外被引用）

## 知识沉淀

1. **E007**: 2013 版 GNU config.guess 不识别 HarmonyOS，configure 第一阶段即失败 → 需打补丁识别 `aarch64-unknown-linux-ohos`
2. **E129**: HMDFS setgid 目录下 config.status 创建临时文件失败 → 编译前 umask 022
3. **SRTP 可选层**: 缺少 libgcrypt/OpenSSL 时上游 configure 硬失败，`--disable-srtp` 关闭即可（核心 RTP 功能不依赖加密后端）
4. **cpp_info.requires 传递**: ccrtp 公共头 include `<ucommon/*>`/`<commoncpp/*>`，需在 `package_info()` 声明 `self.cpp_info.requires = ["ucommon::ucommon"]`，使下游仅 `require ccrtp` 时 ucommon 的 include/link 也能通过 CMakeDeps 传递

## 注意事项

1. 必须使用 conan ucommon/7.0.1（已发布，含 commoncpp.pc 兼容层）
2. 必须 `--disable-srtp`（本环境无 libgcrypt/OpenSSL）
3. C++ 标准：profile 为 cppstd=17，ccrtp WARN_FLAGS 传 `-ansi`（C++03）会触发 ucommon 的 nullptr shim → CXXFLAGS 追加 `-std=c++17` 覆盖
