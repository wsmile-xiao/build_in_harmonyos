# minisign 0.12 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-13
- 编译器: clang/clang++（OHOS aarch64，HNP 工具链）
- 状态: built（待真机预检）

## 编译步骤

1. 上游源码：`https://github.com/jedisct1/minisign/archive/refs/tags/0.12.tar.gz`
   - sha256: `796dce1376f9bcb1a19ece729c075c47054364355fe0c0c1ebe5104d508c7db0`
   - 与 Buildroot 官方记录（package/minisign/minisign.hash）一致，本机下载复核一致。
   - 注意：GitHub release 资产 `minisign-0.12.tar.gz`（macOS 打包）含 `._*` 垃圾文件且哈希不同（677e3dd5…），故用 GitHub 自动归档（官方 archive URL）。
   - 真机无法直连 github.com（E017）：conandata.yml 的 url 已改为有序镜像列表（gh-proxy.com / mirror.ghproxy.com / ghproxy.com / gitclone.com / moeyy.cn / kkgithub.com 在前，官方 URL 最后回退），镜像提供与官方完全相同的归档，sha256 不变。
2. 依赖：libsodium/1.0.22 **系统预编译包**（cmd-pkgs 安装于 ~/usr/local，非 conan 依赖）。
   - 原因：libsodium/1.0.22 未发布到 ohpcd 制品仓（R36）；conancenter 配方硬编码 GitHub 源码 URL，真机下载失败（RemoteDisconnected，E017）。同 0.12-r1 / gdnsd / rsync / gadap 先例改用系统预编译包。
   - generate() 若发现 `~/usr/local` 下无 `include/sodium.h`，按 abook/acedb 先例用纯 Python urllib 从 cmd-pkgs 按需安装 `libsodium-1.0.22-ohos-aarch64.tar.gz`（幂等；真机预检环境不预装系统 libsodium，这是首轮预检失败的根因）。
   - generate() 显式传 `SODIUM_INCLUDE_DIR=~/usr/local/include`、`SODIUM_LIBRARY=~/usr/local/lib/libsodium.a`（优先静态，无则 .so；OHOS 动态库加载受限，README 建议静态链接）。
3. 构建命令（conan create，profile 见 ci/conan/profiles/ohos-aarch64）：
   ```bash
   conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
   ```
4. CMake 构建：上游用 `find_package(PkgConfig REQUIRED)` + `find_path`/`find_library` 定位 libsodium。
   - 补丁 0001 将 PkgConfig 放宽为可选（OHOS 可能无 pkg-config，E001/E075 类）。
   - generate() 显式传 `SODIUM_INCLUDE_DIR` / `SODIUM_LIBRARY` 指向系统 libsodium（旧 0.12-r1 笔记同样显式指定过）。
5. 上游无测试套件（详见 test_package/MANIFEST.yml 审计），test_package 对打包的 minisign 二进制做真实功能测试（版本/密钥生成/签名/验证/篡改检测，5 项断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(PkgConfig REQUIRED)` 在无 pkg-config 的 OHOS 上会硬失败 | 上游 CMake 依赖 pkg-config 探测 libsodium | 补丁 0001：改为 `find_package(PkgConfig)` + `if(PKG_CONFIG_FOUND)` 保护 pkg_check_modules |
| 2 | find_path/find_library 找不到 libsodium | libsodium 在非标准路径 ~/usr/local，不在 CMake 默认搜索路径 | generate() 显式传 `SODIUM_INCLUDE_DIR`/`SODIUM_LIBRARY` |
| 3 | 上游无任何测试 | minisign 0.12 源码树无测试目录/框架/ctest | test_package 做真实功能验证 + MANIFEST 显式审计 no_tests |
| 4 | release 资产哈希与官方记录不符 | macOS 打包的 release tarball 含 xattr 垃圾 | 改用 GitHub archive（refs/tags/0.12）官方归档，哈希与 Buildroot 一致 |
| 5 | libsodium/1.0.22 源码下载失败（RemoteDisconnected） | 真机无法直连 github.com（E017）；libsodium 未发布到 ohpcd（R36），conancenter 配方硬编码 GitHub URL | 改用 cmd-pkgs 系统预编译 libsodium（~/usr/local），配方不再声明 conan libsodium 依赖；minisign 自身源码 URL 镜像化。首轮真机预检发现预检环境未预装系统 libsodium，generate() 改为缺失时按需从 cmd-pkgs 安装（abook/acedb 先例，纯 Python urllib，不依赖 curl） |
| 6 | cmd-pkgs 下载报 SSL CERTIFICATE_VERIFY_FAILED（unable to get local issuer certificate） | OHOS 上 Python 标准库 urllib 默认 SSL 上下文没有系统 CA 证书（E034/E185 类），直连 gitcode.com https 校验失败；同日志中 Conan 的 get() 用 requests+certifi 下载 minisign 源码 HTTPS 成功 | `_install_cmd_pkg` 改用 `conan.tools.files.download`（与 source() 同一 HTTP 栈，真机已证实可行）；不采用禁用 TLS 校验的临时手段（chicken 5.4.0 先例已废弃、禁止复用） |
| 7 | `apply_conandata_patches` 报 "source/target file does not exist: --- b'' +++ b''"，补丁应用失败 | conan 2.30 用 patch_ng 应用补丁，patch_ng 解析 git 风格补丁时已内部剥离 `a/` 前缀（source=b'CMakeLists.txt'）；conandata 再配 `strip: 1` 会把 `CMakeLists.txt` 继续剥成空路径。本地 patch_ng 复现：strip=0 成功、strip=1 失败；acedb 先例无 strip 字段（默认 0） | conandata.yml 补丁 strip 从 1 改为 0（与 acedb 先例一致）；补丁内容本身经 git apply --check 与 patch_ng strip=0 双重验证可正确应用 |
| 8 | test_package 4 项功能测试全 FAIL（版本/密钥生成/签名/验证），仅篡改检测“通过”（因验证已失败反向成功） | E077：OHOS 内核要求可执行 ELF 含有效 `.codesign` 签名段；上游 CMakeLists 的 POST_BUILD strip（`${CMAKE_STRIP}`）在链接后改写 ELF，使链接期自签失效 → 内核拒绝加载（Operation not permitted，chmod 无法恢复）。0.12-r1 笔记同证（未 ELF 签名→执行权限被拒）。构建与打包本身成功，二进制不可执行 | `package()` 中 `cmake.install()` 后按 acme/acme-client/ad2vcf/acsccid 先例对 `bin/` 下 ELF 重签：`llvm-objcopy --remove-section .codesign`（容错）→ `binary-sign-tool sign -inFile ... -outFile ... -selfSign 1` → `os.replace` → `chmod 755`（E077 四步流程） |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`：PkgConfig 可选（portability）。

## 依赖版本

- libsodium/1.0.22

## 验证结果

```bash
# 待 HMBS 真机预检（HarmonyOS aarch64 真机 conan create + test_package）
# test_package 断言：5 项（版本/密钥生成/签名/验证/篡改检测）
```

## 注意事项

- minisign 是命令行工具（application 包），`package_info` 只设置 `cpp_info.bindirs = ["bin"]`。
- minisign 无 `--version`，用 `-v` 输出版本（旧 0.12-r1 笔记验证：`minisign -v` → `minisign 0.12`）。
- 上游 README 已推荐迁移到 minizign（zig 实现），但 0.12 CMake 路径仍需 libsodium。
