# imx-code-signing-tool (NXP Code Signing Tool / CST)

NXP 官方代码签名工具，用于为 i.MX 系列 SoC 生成 HABv4（High Assurance Boot）与 AHAB（Advanced High Assurance Boot）安全启动所需的签名镜像与证书链。

## 功能概述

- **cst**：将 CSF（Command Sequence File，HABv4/AHAB 命令序列文件）文本转换为二进制签名文件，并可选对接 OpenSSL 后端完成签名。
- **srktool**：从 SRK 证书生成 SRK Table 与 SRK Table hash（HABv4/AHAB 密钥根表）、efuse 建议值。
- **pki_tree**（add_key / hab4_pki_tree / ahab_pki_tree）：生成 HAB/AHAB PKI 证书树与密钥。
- **convlb**：将 Windows 行尾文件转换为 Unix 行尾格式。
- **mac_dump / hab_csf_parser**：解析与调试 CSF 生成产物。
- **ahab_signed_message / ahab_split_container / image_verifier**：AHAB 签名消息构造、容器拆分与镜像校验辅助。

## OHOS 适配要点

- 构建系统为 CMake（工程位于源码包 `src/` 子目录），顶层 `CMakeLists.txt` 仅在 `CMAKE_SYSTEM_NAME` 为 Linux/Windows 时推导 `OSTYPE`；OHOS 上需显式 `-DOSTYPE=linux64`。
- 依赖 OpenSSL（`find_package(OpenSSL)` + `OpenSSL::Crypto/SSL`）与 json-c（`ahab_signed_message` 静态链接 `libjson-c.a`），Conan 配方中通过 CMakeDeps 组件重映射与 `json_c_DIR` 注入路径。
- OHOS libc 头文件与 clang `-Werror` 下需 3 个源码补丁（`#define NULL` 重定义、两处 `-Wpointer-sign` 类型不匹配）。
- 可选 PKCS#11 与 PQC（liboqs）后端默认关闭（依赖非基础工具集，需额外适配）。
- 与 Linux 的差异：可执行文件为 arm64 PIE；未发现影响签名核心功能的平台差异。产物为命令行工具集，无系统级后台服务。

## 编译与运行依赖

- 宿主工具：clang 15 / bison / flex / CMake / Conan 2（ohos-aarch64 profile）。
- Conan 依赖：openssl/3.5.6、json-c/0.18。

## 参考资料

- 上游官方：https://www.nxp.com/webapp/sps/download/license.jsp?colCode=IMX_CST_TOOL_NEW（`cst-4.0.1.tgz`，BSD-3-Clause）
- Release_Notes.txt / Software_Content_Register_CST.txt（发行包内）
- 构建说明：src/BUILD.md