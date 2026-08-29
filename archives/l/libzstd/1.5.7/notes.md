# libzstd 1.5.7 适配笔记

## 编译环境
- 构建系统: cmake (build/cmake 子目录，cmake 4.1.2，Ninja 生成器)
- 操作系统: HarmonyOS HongMeng Kernel 1.12.0 aarch64 (Toybox)
- 编译器: clang 15.0.4 (/srv/workspace/llvm-release/2026_0313_llvm15_release/toolchain/llvm-project/clang 0e01a01d567b9acfce8edfdadb66a7b69f088fb0)
- TMPDIR: /storage/Users/currentUser/tmp
- 编译日期: 2026-08-28
- 状态: built (conan create rc=0, test_package PASS)

## 源码来源
- 官方仓库: https://github.com/facebook/zstd
- 标签: v1.5.7 (tag object sha ac66b19e6bd6b83238bf008eecc1298105298532)
- 标签指向 commit: f8745da6ff1ad1e7bab384bd1f9d742439278e99
- 源码下载 URL (codeload git-archive): https://codeload.github.com/facebook/zstd/tar.gz/refs/tags/v1.5.7
- 源码校验值 (SHA-256): 37d7284556b20954e56e1ca85b80226768902e2edabd3b649e9e72c0c9012ee3
- 备注: 官方 release tarball (https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-1.5.7.tar.gz) 记录 SHA-256 eb33e51f...（自既有 zstd/1.5.7.1 归档交叉引用）；本机环境 github.com 主域不可达，codeload 通道下载的 git-archive 与 bootstrap 阶段实测 hash 一致。

## 编译步骤
1. `conan source .` — 从 codeload 下载 v1.5.7 git-archive，strip_root 解压
2. `conan build .` — 自动发现 OHOS NDK ohos.toolchain.cmake
   - cmake -G Ninja -B build-ohos -S build/cmake \
     -DCMAKE_TOOLCHAIN_FILE=ohos.toolchain.cmake \
     -DCMAKE_AR=llvm-ar -DCMAKE_RANLIB=ranlib-shim \
     -DOHOS_ARCH=arm64-v8a -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_INSTALL_LIBDIR=lib \
     -DZSTD_BUILD_SHARED=ON -DZSTD_BUILD_STATIC=ON \
     -DZSTD_BUILD_PROGRAMS=ON -DZSTD_BUILD_TESTS=OFF
   - cmake --build build-ohos -- -j$(nproc)
3. `conan package .` — cmake --install → self-sign .so (llvm-objcopy --remove-section .codesign + binary-sign-tool -selfSign 1)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码 sha256 不匹配 | conandata.yml 沿用了既有 zstd/1.5.7.1 归档的 release tarball hash (eb33e51f...)，本机环境实际下载的 codeload git-archive 字节计算为 37d72845... | 记录为本地实测 hash，与任务 Known Bootstrap Evidence 一致 |
| 2 | codeload URL 无 .tar.gz 扩展名导致 conan 按 zip 解压报 BadZipFile | URL 以 v1.5.7 结尾，conan 无法识别 tar.gz 格式 | conandata.yml 增加 filename: "zstd-1.5.7.tar.gz" |
| 3 | OHOS musl 无 GNU qsort_r | cover.c 的 `_GNU_SOURCE` 分支尝试调用 glibc qsort_r（OHOS musl 无该符号） | r24 合规修复：移除对 GNU qsort_r 的 `_GNU_SOURCE` 依赖，统一走 ISO C90 `qsort()` + 全局上下文（能力/标准基方案，无 `__OHOS__` 平台身份宏，R8 合规）；经 conandata.yml patches + apply_conandata_patches() 应用 |
| 4 | llvm-ranlib 不存在 | OHOS SDK 不含 llvm-ranlib | 创建 shim 脚本 `exec llvm-ar s "$@"` |
| 5 | 签名验证 | binary-sign-tool verify 不可用 | 仅检查 .codesign section 存在 |
| 6 | github.com 主域不可达 | 本机环境网络限制 | 通过 codeload.github.com 下载（官方 git-archive 通道） |

## 源码修改

合规补丁（经 conandata.yml patches 声明 + apply_conandata_patches() 应用）：
- `patches/0001-lib-dictBuilder-cover.c-c90-qsort.patch`：移除 cover.c 对 GNU qsort_r 的 `_GNU_SOURCE` 依赖，统一走 ISO C90 `qsort()` + 全局上下文（能力/标准基方案，不依赖 `__OHOS__` 平台身份宏，R8 合规）。

## 依赖版本

无外部依赖（zstd 核心零外部依赖，requirements: pass）

## 验证结果

```bash
# conan create 完整编译 (rc=0)
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 制品验证
# libzstd.so -> libzstd.so.1 -> libzstd.so.1.5.7 (ELF 64-bit LSB arm64, BuildID=...)
# libzstd.a (static)
# bin/zstd + unzstd/zstdcat/zstdmt (symlinks) + zstdgrep/zstdless

# 上游测试: ZSTD_BUILD_TESTS=OFF 跳过（无 /bin/sh，fuzzer 需 OSS-Fuzz 运行时）

# 鸿蒙特有测试: dlopen libzstd.so + dlsym ZSTD_versionNumber → version=10507 PASS
# test_package: ./test_probe → "zstd: version=10507, dlopen ... ok"
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | cmake 配方，OHOS 平台适配完整 |
| conandata.yml | 源码 URL + SHA-256 |
| manifest.yaml | 版本级 manifest |
| test_package/ | dlopen 实测 libzstd API 的鸿蒙测试 |

## 注意事项

- 本配方基于 zstd/1.5.7.1 既有配方（同源 v1.5.7 源码）修改为 libzstd 名称与版本
- 源码 SHA-256 使用本机环境实测的 codeload git-archive 校验值（37d72845...）
- 正式环境中 CI 会对 github release 下载添加镜像 fallback
- SELinux: 本机环境无 SELinux 工具（getenforce 不存在），无限制
- 签名: .codesign section 已存在（PROGBITS），binary-sign-tool 用于签名；verify 子命令不可用
- libzstd 无外部依赖，W0 预检通过
---

**编译结束**: 2026-08-28 16:00
**最终状态**: built
