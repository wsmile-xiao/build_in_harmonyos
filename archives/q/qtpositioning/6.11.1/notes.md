# qtpositioning 6.11.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-08
- 编译器: clang/clang++
- 平台: OHOS（OpenHarmony PC, aarch64）
- 状态: built

## 编译步骤

```bash
# 下载源码（中科大镜像已验证可用）
wget https://mirrors.ustc.edu.cn/qtproject/official_releases/qt/6.11/6.11.1/submodules/qtpositioning-everywhere-src-6.11.1.tar.xz

# Conan 构建
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Qt6 子模块源码下载 | 官方 download.qt.io 慢/不稳定 | conandata.yml 配置清华/中科大/腾讯/阿里镜像 fallback |
| 2 | OHOS 平台识别 | Qt CMake 默认不认识 HarmonyOS | QT_QMAKE_TARGET_MKSPEC=harmonyos-clang（参照 qtbase/6.11.1） |
| 3 | 依赖链 | qtpositioning 依赖 Qt Core/Network | requirements() 声明 qtbase/6.11.1（仓库已发布该版本） |

## 注意事项
- qtpositioning 是依赖类包，必须先构建 qtbase/6.11.1
- 参照 qtbase/6.11.1 的 mkspec 与 feature 开关写法保持风格一致

---

**编译结束**: 2026-08-08
**最终状态**: built
