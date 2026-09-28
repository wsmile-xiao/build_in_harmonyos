# imx-code-signing-tool 4.0.1 HarmonyOS 适配笔记

## 版本映射

- 上游：NXP Code Signing Tool (CST) 4.0.1（Release_Notes.txt，2025 年 6 月）
- 官方来源：NXP IMX_CST_TOOL_NEW（需注册下载）；本配方使用 Debian 官方 orig 重打包 `imx-code-signing-tool_4.0.1+dfsg.orig.tar.xz`，其 `src/CMakeLists.txt` 声明 `project(CST VERSION 4.0.1)` 与 `Software_Content_Register_CST.txt` 一致
- Conan 配方：`imx-code-signing-tool/4.0.1`
- 源码 SHA-256：`fd92a1a9faa10fb81bbf752c7ee1e257f17e1ec4c2964f8a47adf8a3eaa7df41`

## 源 URL 合规（R02，PF7 官方托管例外显式跳过）

- 官方归档 `cst-4.0.1.tgz`（`Software_Content_Register_CST.txt` 记录 Package/Version=4.0.1）仅能经 NXP license 同意页 `https://www.nxp.com/webapp/sps/download/license.jsp?colCode=IMX_CST_TOOL_NEW` 取得；匿名直连该 URL 返回 HTTP 404（2026-09-24 探测），无公开匿名下载端点。
- 因此本源声明使用 Debian 官方 orig 重打包件，并已在 `conandata.yml` 与 `conanfile.py` 中写明官方托管例外说明（PF7 显式跳过依据）：
  - 官方包名与版本：cst-4.0.1.tgz / 4.0.1（`Software_Content_Register_CST.txt`）；
  - 官方发行包内 `Release_Notes.txt` 与 `Software_Content_Register_CST.txt` 原样保留；
  - `src/CMakeLists.txt` 的 `project(CST VERSION 4.0.1)` 与官方 Version 一致；
  - SHA-256 `fd92a1a9…` 与 r01 及分析端独立复算一致。
- 未引入 file://、http://、个人 fork、网盘或不明 CDN；未改写官方 URL。

## 构建策略

- 使用 Conan 2 的 `CMakeToolchain` 与 `CMakeDeps`；CMake 工程位于源码包的 `src/` 子目录（`build_script_folder="src"`）。
- 依赖：`openssl/3.5.6`（CST 要求 OpenSSL >= 3.0.0）、`json-c/0.18`（`tools/ahab_signed_message` 静态链接 `libjson-c.a`）。
- 关键适配点：
  1. `OSTYPE=linux64`：上游只在 CMAKE_SYSTEM_NAME==Linux 时推导 OSTYPE，OHOS 上必须显式指定。
  2. OpenSSL 组件重映射：上游用 `find_package(OpenSSL)` + `OpenSSL::Crypto/SSL`，需在 `generate()` 中先重映射 ohpcd openssl 配方组件，再调用 `CMakeDeps.generate()`。
  3. `json_c_DIR` 指向 json-c 包根目录，使 `find_cst_dependency_library()` 推导出 `<root>/include`。
  4. 禁用可选 PKCS#11 与 PQC 后端（依赖 libp11/liboqs，非基础工具集）；保留上游默认关闭的 hab_log_parser 等工具。
- 补丁 3 个：convlb.c 的 NULL 重定义（OHOS libc 冲突）、csf_cmd_ins_key.c 与 ahab_image_verifier.c 的 -Wpointer-sign 类型不匹配（-Werror 下编译失败）。

## 制品

- 可执行文件 13 个：cst、srktool、pki_tree（add_key/hab4_pki_tree/ahab_pki_tree）、convlb、mac_dump、hab_csf_parser、ahab_signed_message、ahab_split_container、image_verifier（hab4/ahab）、hab4_mac_dump。
- 均为静态链接 OpenSSL/json-c 的 arm64 PIE 可执行文件（见 conan-verify L4 报告）。

## test_package

消费者测试（test.sh，bash 执行）：

1. `cst --version` 断言输出含 `4.0.1`
2. `cst --help` 断言输出用法
3. `srktool`（无参数）断言打印 `Usage`

上游无自动测试框架（发行版仅 examples/ 手工示例），test_package 为消费者冒烟验证。
---

**编译结束**: 2026-09-24 11:19
**最终状态**: built
