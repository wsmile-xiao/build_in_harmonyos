# adplay 1.9 适配笔记

## 编译环境
- 构建系统: autotools（configure/make）
- 编译日期: 2026-08-09
- 编译器: clang/clang++
- 平台: OHOS（OpenHarmony PC, aarch64）
- 状态: built

## 编译步骤

```bash
# 下载源码（GitHub API tarball）
wget https://api.github.com/repos/adplug/adplay-unix/tarball/v1.9

# autotools 构建（OHOS 交叉编译）
./configure --prefix=<prefix> --host=aarch64-unknown-linux-ohos --disable-shared --enable-static
make -j1
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 交叉编译 | Worker 网络受限，无 autoconf 缓存 | 直接运行自带 configure/make，--host=aarch64-unknown-linux-ohos |
| 2 | 并行构建不稳定 | OHOS 交叉环境 | make -j1（R9 要求） |
| 3 | 依赖 AdPlug 库 | adplay 是 AdPlug 前端，依赖 AdPlug >= 2.2 | 依赖系统预装（仓库无 adplug conan 包，R36） |

## 注意事项
- adplay 是 AdPlug 的 UNIX 控制台 OPL2 播放器前端（C++）
- 版本 tag v1.9（2025-12，配套 AdPlug 2.4）

---

**编译结束**: 2026-08-09
**最终状态**: built
