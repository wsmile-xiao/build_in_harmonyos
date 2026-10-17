# pxr-gf 26.08 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-23（修复重验）
- 初次适配: 2026-09-04（PR #8104，因补丁损坏/测试空壳/镜像 URL 被 AI 检视打回）
- 编译器: clang/clang++ (15), libc++, C++17
- 状态: built

## 源码
- Repository: https://github.com/PixarAnimationStudios/OpenUSD
- Version: v26.08（pxr-gf 取自 OpenUSD 单仓的 pxr/base/gf 模块，与制品仓已有的 pxr-vt/26.08 同源同 sha256）
- SHA256: 4bccbb95cddda1dbeef2f74a08b9456352f2aa91bfd4578c0c613009c7950149

## 构建方式
- CMake target "gf"，自动拉取依赖闭包 arch、tf（同 pxr-vt 构建 target "vt" 的模式）
- 静态库: libusd_gf.a + libusd_tf.a + libusd_arch.a
- 头文件: pxr/base/{gf,tf,arch}/*.h + 生成头 build/include/pxr/pxr.h

## 依赖
- tbb/2023.0.0 (ohpcd 制品仓，tf 模块依赖 TBB::tbb)

## 遇到的问题与解决方案（初版 PR #8104 检视意见的修复）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 4 个补丁 hunk 头为 `@@ -XX,XX +XX,XX @@` 占位符，无法应用 | 初版补丁非真实 diff 生成 | 重写为真实 hunk 头的单一补丁（复用 pxr-vt 已验证的同源补丁） |
| 2 | 补丁使用 `#ifdef __OHOS__` 违反 R8 | 平台宏硬编码 | 改为特性探测守卫：`#ifdef _SC_LEVEL1_DCACHE_LINESIZE`、`#ifndef DEFFILEMODE`、去掉 `_GNU_SOURCE` 分支、`environ` 直接替换 `__environ` |
| 3 | `_SC_LEVEL1_DCACHE_LINESIZE` 未定义 | OHOS musl 的 sysconf 不提供此常量 | 特性守卫 + 默认值 64（魔数 0x2012 一并移除） |
| 4 | `strerror_r` 返回类型不匹配 | OHOS musl 为 POSIX 版本(返回 int) | 删除 `_GNU_SOURCE` GNU 分支，POSIX 分支两平台通用 |
| 5 | `__environ` 未声明 | OHOS musl 不提供 glibc 的 `__environ` | 替换为 `environ` |
| 6 | `DEFFILEMODE` 未定义 | OHOS musl 的 sys/stat.h 不定义此宏 | `#if defined(ARCH_OS_WASM_VM) \|\| !defined(DEFFILEMODE)` 扩展守卫 + 0666 兜底 |
| 7 | conandata.yml 使用 ghfast.top 镜像前缀（违反 R39） | 初版为绕过网络问题手工加镜像 | 改为官方原始 URL，CI 自动镜像 fallback |
| 8 | conandata patches 为 dict 格式，Conan 2.x 无法应用 | 初版格式错误 | 改为版本键 + 列表格式（与 pxr-vt 一致） |
| 9 | test_package test() 缺 self.run（CI L0 stub_test_method 拦截） | 初版用 cmake.test() 但无注册测试 | 改为 can_run + self.run(bin_path, env="conanrun")，并覆盖 gf/arch/tf 接口 |
| 10 | conan create 从未通过（网络超时阻塞） | GitHub 直连慢 | 本地预下载校验 sha256 后走 conan-verify（自动镜像注入） |

## 验证结果

```bash
conan create archives/p/pxr-gf/26.08 --build=missing -pr:b ci/conan/profiles/ohos-aarch64 -pr:h ci/conan/profiles/ohos-aarch64
# 结果: 构建成功，测试通过
# pxr-gf smoke test: OK
```
---

**编译结束**: 2026-09-23 13:56
**最终状态**: built
