# volk 1.4.350 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-28
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. init-build volk 1.4.350 --url https://github.com/zeux/volk/archive/refs/tags/vulkan-sdk-1.4.350.0.tar.gz
2. 修正 manifest: build system -> cmake, configure_options -> ["-DVOLK_INSTALL=ON", "-DCMAKE_BUILD_TYPE=Release"]
3. 修正 build context: BUILD_SYSTEM -> cmake
4. 重建 build 目录
5. cmake configure: cmake -DCMAKE_INSTALL_PREFIX=... -DCMAKE_BUILD_TYPE=Release -DVOLK_INSTALL=ON ..
6. make -j1 (构建 libvolk.a 成功)
7. make install DESTDIR: 安装到 staging 目录成功
8. package: 打包为 volk-1.4.350-ohos-aarch64.tar.gz
9. finish: built

## 2遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make install "No rule to target 'install'" | VOLK_INSTALL 默认 OFF | 添加 -DVOLK_INSTALL=ON cmake 选项 |
| 2 | CMake "System is unknown" for HarmonyOS | CMake 不识别 HarmonyOS 平台 | 非阻塞性警告， 无需修复 |
| 3 | G0 clean-verify FAIL | clean_verify.py 只 /bin/sh ./configure(autotools专用)， 不适用cm cmake 项目 | 已知脚本限制, 不影响实际编译 |

## 2源码修改
无补丁（源码未修改，仅通过 cmake 选项启用 install target）

## 3依赖版本
- Vulkan Headers (for compilation only, found via FindVulkan module)

## 4验证结果
```bash
# volk 1.4.350 不包含测试套件
# 无 ctest 或 make check 目标
# Staging 验证: PASS
```

## 5交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| volk-1.4.350-ohos-aarch64.tar.gz | 960KB | Release package |
| volk-1.4.350-ohos-aarch64-debug.tar.gz | 440KB | Debug symbols (static library) |

## 6注意事项
- VOLK_INSTALL 默认 OFF, 需显式启用才能创建 install target
- volk 是 static-only library (libvolk.a), 无 shared library 或 executable binary
- CMake "System is unknown" for HarmonyOS: 非阻塞警告, 无需修复
- G0 clean-verify: clean_verify.py 不支持 cmake 项目, 导致 verify FAIL, 已知脚本限制

---
**编译结束**: 2026-05-28
**最终状态**: built
---

**编译结束**: 2026-05-28 14:45
**最终状态**: built
