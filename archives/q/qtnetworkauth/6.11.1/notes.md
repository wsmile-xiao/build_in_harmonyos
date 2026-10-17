# qtnetworkauth 6.11.1 适配笔记

## 基本信息
- 软件: qtnetworkauth（Qt NetworkAuth 模块，OAuth1 / OAuth2）
- 版本: 6.11.1（上游 tag `v6.11.1`，commit `a804d2581006e827c8966b7514f98e0bfc599b02`）
- 语言: C++17，构建系统: CMake + Ninja
- 许可证: BSD-3-Clause / LGPL-3.0 / GPL-3.0
- 状态: built（真机 shadow CI conan create 通过，未 upload）

## 配方要点
- `QT_QMAKE_TARGET_MKSPEC=harmonyos-clang`，依赖 `qtbase/6.11.1`（Qt::Core + Qt::Network）。
- qtbase 为 `cmake_find_mode "none"`：generate() 显式设 `CMAKE_PREFIX_PATH` 指向 qtbase
  package_folder，`CMAKE_MODULE_PATH` 指向 qtbase 安装的 `lib/cmake/Qt6/platforms`。
- OHOS 上追加 `-DQT_NO_ARM_AES_INTRINSICS`（OAuth 签名用 QCryptographicHash/HMAC）。
- **HMDFS symlink 处理**：`_materialize_cmake_symlink_library_rules()` 把 CMake 的
  `cmake_symlink_library` 替换为文件复制；`_ensure_soname_link_copies()` 在 install 后
  生成 `.so` / `.so.6` 实体副本（HMDFS 不支持符号链接，否则链接时 Permission denied）。
- OHOS ELF 签名（`_sign_installed_elfs`）：test_package 运行必需。
- 上游测试子集选 `tst_oauth1signature` / `tst_abstractoauth2`（无条件构建，纯本地无网络）。
  `tst_abstractoauth` 被 `QT_FEATURE_private_tests`（默认关闭）门控，不构建。

## 依赖版本
- qtbase 6.11.1（无外部依赖，离线源码编译；与 qtsvg 等 Qt 6.11 模块一致）

## 验证结果（真机 shadow CI）
- 本机（Windows）无 conan / OHOS SDK，仅静态验证通过。
- 真机 shadow CI（job `qtnetworkauth-6.11.1-shadow-20260921-200037`）：
  - qtbase/6.11.1 离线 `conan create` 成功（含 symlink 修复 + 跳过 tst_qdom 德语文件名环境问题）
  - qtnetworkauth/6.11.1 `conan create` 成功：
    - 上游测试 **2/2 通过**（tst_abstractoauth2 0.28s + tst_oauth1signature 0.10s）
    - test_package **通过**（`test_qtnetworkauth: PLAINTEXT + HMAC-SHA1 OK`）
  - 产物完整：`lib/libQt6NetworkAuth.so.6.11.1`（含 .so.6 / .so 副本）、头文件、CMake 配置

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（qtbase/6.11.1 依赖、harmonyos-clang、symlink 复制、ELF 签名） |
| conandata.yml | 官方 Qt 镜像源（清华/中科大/腾讯/阿里/download.qt.io）+ SHA256 |
| test_package/ | 消费者测试（QOAuth1Signature plaintext + HMAC-SHA1 校验）+ MANIFEST.yml |

## 备注
- 本库是 musescore/4.7.4 的缺失依赖（W0 拆单适配）。依赖链：qtbase → qtnetworkauth → musescore。
- 制品仓发布（conan upload）待正式 CI 流程执行，本轮 shadow CI 只做本机前置验证。
