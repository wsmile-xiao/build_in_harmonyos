# monero 0.18.4.4-r0 编译笔记

## 基本信息
- 软件: monero
- 版本: 0.18.4.4-r0
- 构建系统: CMake
- 源码: https://github.com/monero-project/monero/archive/refs/tags/v0.18.4.4.tar.gz

## 依赖项
- Boost (system, thread, chrono, date_time, filesystem, program_options, regex, serialization)
- OpenSSL (libssl, libcrypto)
- libunbound (DNS 解析)
- libsodium (加密)
- hidapi (硬件钱包支持)

## 编译日志

---

## 编译失败报告 (2026-05-20)

### 失败原因

1. **网络访问严重受限**：
   - GitHub submodule clone 失败 (supercop, trezor-common 返回 403)
   - curl 下载 submodule tarball 失败 (超时/空响应)
   - cmd-pkgs API 被拦截 (418 WAF)

2. **缺少关键依赖**：
   - **Boost >= 1.66**：必需，未安装，Boost 是大型库编译需数小时
   - **libunbound**：必需 DNS 解析库，未安装
   - **libsodium**：必需加密库，未安装
   - **libzmq >= 4.2.0**：必需 ZeroMQ 库，未安装
   - **miniupnpc**：git submodule，网络无法获取

3. **源码完整性问题**：
   - GitHub tarball 不包含 submodule
   - git clone --recursive 因网络限制失败
   - 5个 submodule 全部为空目录

4. **OpenSSL 已安装但需要路径配置**：
   - OpenSSL 3.5.6 已安装在 ~/usr/local
   - 需要 PKG_CONFIG_PATH 和 OPENSSL_ROOT_DIR 配置

### 编译环境检查

- **编译器**：clang++ 15.0.4 (aarch64-unknown-linux-ohos) ✅
- **CMake**：4.1.2 ✅
- **make**：4.4.1 ✅
- **pkg-config**：0.29.2 ✅
- **OpenSSL**：3.5.6 ✅ (需配置路径)
- **Boost**：❌ 未安装
- **libunbound**：❌ 未安装
- **libsodium**：❌ 未安装
- **libzmq**：❌ 未安装
- **git submodule**：❌ 无法下载

### 建议

1. 在有完整网络访问的环境中编译
2. 先安装预编译依赖包（Boost, libunbound, libsodium, libzmq）
3. 使用 `git clone --recursive` 下载完整源码
4. 或使用官方预编译的 monero 二进制

### CMake 配置错误日志

```
CMake Error at external/CMakeLists.txt:43 (add_subdirectory):
  add_subdirectory given source "miniupnp/miniupnpc" which is not an existing directory.

CMake Error at CMakeLists.txt:113 (message):
  Could not find libunbound
```

**最终状态**: failed

---

## 第二次编译尝试报告 (2026-05-20)

### R18 原则执行情况

按照 R18 原则（依赖先查预编译 → 无预编译包 → 手动编译），本次任务执行了以下步骤：

#### 1. 预编译包查询（cmd-pkgs）

**尝试访问 cmd-pkgs README 获取预编译包列表：**

```bash
# 尝试 1: GitCode API
curl "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/blob/main/README.md"
→ 返回 HTML 页面（需 JavaScript 渲染）

# 尝试 2: GitCode raw 格式
curl "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/raw/main/README.md"
→ 返回 HTML 页面（被 WAF 拦截）
```

**结果**: ❌ cmd-pkgs 预编译包仓库访问失败，无法获取 libsodium、libunbound、libzmq、Boost 的预编译包列表。

#### 2. 手动编译依赖尝试（libsodium）

**libsodium** 是最小型加密库，优先尝试编译。

**下载源码尝试（共 6 次）：**

| 尝试 # | 来源 | URL | 结果 | 错误信息 |
|--------|------|-----|------|---------|
| 1 | GitHub releases | https://github.com/jedisct1/libsodium/releases/download/1.0.18-RELEASE/libsodium-1.0.18.tar.gz | ❌ 失败 | wget: response header too large |
| 2 | 官方站点 | https://download.libsodium.org/libsodium/releases/libsodium-1.0.18.tar.gz | ❌ 失败 | wget: response 404 |
| 3 | GitHub releases (1.0.19) | https://github.com/jedisct1/libsodium/releases/download/1.0.19-RELEASE/libsodium-1.0.19.tar.gz | ❌ 失败 | wget: response header too large |
| 4 | curl 官方站点 | https://download.libsodium.org/libsodium/releases/libsodium-1.0.18.tar.gz | ❌ 失败 | 404 Not Found (nginx) |
| 5 | archive.org | https://web.archive.org/web/2020/https://download.libsodium.org/libsodium/releases/libsodium-1.0.18.tar.gz | ❌ 失败 | curl: (28) Failed to connect after 65090 ms |
| 6 | osdn.net | https://osdn.net/projects/libsodium/downloads/68669/libsodium-1.0.18.tar.gz/ | ❌ 失败 | curl: (6) Could not resolve host: osdn.net |

**结果**: ❌ 所有下载源均失败，无法获取 libsodium 源码。

#### 3. 其他依赖源码获取尝试

由于 libsodium 下载失败，未继续尝试下载 libunbound、libzmq、Boost 源码。

**原因**:
- libunbound 源码同样需要从网络下载
- libzmq 源码同样需要从网络下载
- Boost 是大型库（编译需数小时），即使下载成功也难以在当前任务时限内完成

#### 4. 本地资源检查

**检查系统已安装的依赖：**

```
✅ OpenSSL 3.5.6 - 已安装（~/usr/local/lib/libssl.so.3, libcrypto.so.3）
   - pkg-config: openssl 3.5.6（需设置 PKG_CONFIG_PATH）

❌ libsodium - 未安装
   - pkg-config: Package 'libsodium' not found

❌ libunbound - 未安装
   - pkg-config: Package 'libunbound' not found

❌ libzmq - 未安装
   - pkg-config: Package 'libzmq' not found

❌ Boost - 未安装
   - ~/usr/local/include/boost: No such file or directory
```

### 环境限制总结

**网络访问限制（无法绕过）**:
1. GitHub releases: response header too large / 超时
2. download.libsodium.org: 404 Not Found
3. archive.org: Connection timeout
4. osdn.net: DNS resolution failed
5. GitCode cmd-pkgs: WAF 拦截（返回 HTML 页面）

**本地环境状态**:
- OpenSSL 已安装（可用于 monero 编译）
- 其他 4 个关键依赖（libsodium, libunbound, libzmq, Boost）均未安装
- 无本地缓存的依赖源码

### R18 原则执行结论

**已完全执行 R18 原则流程**:
1. ✅ 查询预编译包（cmd-pkgs）→ 失败（WAF 拦截）
2. ✅ 尝试手动编译依赖（libsodium）→ 失败（无法下载源码）
3. ✅ 检查本地资源 → OpenSSL 已安装，其他依赖未安装

**符合 R18 原则要求**: 在预编译包不可用的情况下，已尝试手动编译依赖，但因环境限制无法继续。

### 最终状态

**状态**: failed

**原因**:
1. 网络访问受限：无法下载 libsodium、libunbound、libzmq、Boost 源码
2. cmd-pkgs 预编译包仓库访问被拦截
3. 缺少 4 个关键依赖（除 OpenSSL 外）
4. 已按 R18 原则完整尝试预编译包查询 + 手动编译依赖，但环境限制导致无法继续

**建议**:
- 在有完整网络访问的环境中编译
- 或使用已准备好的预编译依赖包（需要网络获取）
- 或使用官方预编译的 monero 二进制
---

**编译结束**: 2026-05-20 15:16
**最终状态**: failed
