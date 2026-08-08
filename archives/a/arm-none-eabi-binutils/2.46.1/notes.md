# arm-none-eabi-binutils 2.46.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-17
- 编译器: clang 15
- 状态: published

## 编译步骤
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 编译结束
---

**编译结束**: 2026-07-22 19:15
**最终状态**: built
