# libhttpserver 2.0.0→0.19.0 — C++20 pmr 工具链边界 + autotools 交叉接线（draft）

**Category**: platform | toolchain | cpp-standards · **Severity**: 3 · **Tool**: clang++/configure/conan

## 症状

1. `fatal error: 'memory_resource' file not found`（2.0.0 C++20 编译，std::pmr 贯穿核心 36 处）。
2. `ld.lld: error: unable to find library -lstdc++`（0.19.0 configure.ac 硬编码 AM_LDFLAGS）。
3. release tarball 无 `configure`，直接 configure 报 No such file。
4. 交叉 configure 卡在 `checking for libmicrohttpd... `（AC_CHECK_LIB 试图执行宿主测试程序）。
5. `config.status: could not setup config files machinery`（E011 umask 077）。
6. 上游 SSL 测试 `[FAILURE] Unable to connect daemon to port: 8080`。

## 根因

- OHOS 工具链 libc++ 15004（clang 15）**不带标准 `<memory_resource>`**（仅 experimental/），
  CI 与本地同款（profile cppstd 17）——C++20 pmr 包是平台能力边界（env_unsupported）。
- 上游 configure.ac 只为 darwin/freebsd 做了 OS 分支，OHOS 的 libc++ 无 libstdc++ 可链。
- 无 configure 的 tarball 必须 autoreconf；automake/libtool 不在基础镜像，须 tool_requires。
- AC_CHECK_* 交叉下不可执行，须 ac_cv_* 预置 + CPPFLAGS/LDFLAGS 指 conan 包。
- 依赖 libmicrohttpd 制品包构建时未启 HTTPS → MHD HTTPS daemon 起不来 → 上游 ssl_* 用例失败。

## 处置（可复用）

1. **指定 tag 遇 C++20 pmr**：先实证工具链边界（一行 clang++ 探针），再选上一代 C++17
   release 适配，notes.md 留 env_unsupported 证据链（指定 tag 结论），不硬改 pmr。
2. **-lstdc++ 硬编码**：configure.ac 的 case $host_os 加 `linux-ohos*` 分支置空
   AM_LDFLAGS（同 freebsd 先例，纯构建系统分支，patch 在 autoreconf 之前打）。
3. **无 configure tarball**：tool_requires automake/1.18 + libtool/2.5.4，build() 先
   autoreconf -fi（conanbuild env，-pr:h/-pr:b 双 profile）。
4. **交叉 AC_CHECK**：os.environ 预置 ac_cv_header_microhttpd_h=yes、
   ac_cv_lib_microhttpd_MHD_start_daemon=yes；AutotoolsToolchain configure_args 带
   CPPFLAGS/LDFLAGS 指依赖包。
5. **E011**：autoreconf 后 sed configure 的 umask 077→022（CI 幂等无害）。
6. **SSL 用例豁免**：依赖包能力边界逐用例申报（原文+根因），不连坐整包。

## 降级方案（fallback）

上一代 release 也不可用时（pmr 已成强制依赖 / API 断裂不可接受）：
- 仅当库不依赖 pmr 覆盖语义时，可用 `experimental/memory_resource` + feature 宏兜底过渡；
- **禁止**硬改 pmr 出核心设计（重写上游数据结构=违反最小 patch）——正确通道是版本异常
  反馈：释放指定版本任务 + 重导正确版本任务（本次实证：#13777 释放 2.0.0 + #13910
  重导 0.19.0 对齐 taskBranch）；
- 跟踪 SDK 工具链升级，待 libc++ 提供 `<memory_resource>` 后跟进 2.x。

## 验证

ohos-aarch64 conan create 全绿：libhttpserver.so 打包；test_package 6/6（真实 HTTP
起停+GET 往返）；上游 12 程序本地执行 152 tests / 811 checks：808 过 + 3 SSL 豁免
（libmicrohttpd 无 HTTPS），149/152 = 98.0%。
