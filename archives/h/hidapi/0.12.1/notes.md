# hidapi 0.12.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-03
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. 下载上游源码 hidapi-0.12.0.tar.gz（GitHub 直连失败，经 ghproxy 镜像下载）
2. 使用 CMake 构建（hidapi 0.12.1 同时支持 autotools 与 CMake，CMake 更适配 OHOS 交叉编译）
3. 关键配置参数：
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DCMAKE_BUILD_TYPE=Release \
         -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
         -DHIDAPI_NO_ICONV=ON \
         -DHIDAPI_WITH_LIBUSB=OFF \
         -DHIDAPI_WITH_HIDRAW=ON \
         ..
   ```
4. conan create 构建 hidapi/0.12.1@ohpcd/stable，生成 test_package 并验证通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 版本兼容错误（cmake_minimum_required 3.1.3 与 CMake 4.1.2） | 系统 CMake 4.1.2 移除了对 CMake < 3.5 的支持 | 添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（作为 cache_variables 传入 conan 构建） |
| 2 | libusb-1.0 依赖缺失 | hidapi 的 libusb 后端需要 libusb-1.0，制品仓无此包 | 关闭 libusb 后端（-DHIDAPI_WITH_LIBUSB=OFF），仅构建 hidraw 后端 |
| 3 | libudev 依赖缺失 | hidraw 后端需要 libudev | 使用制品仓已发布的 libudev-zero/1.0.4 提供 libudev 兼容实现 |
| 4 | 源码 CMakeLists 在非 Linux 系统名强制开启 libusb 后端 | src/CMakeLists.txt 的 else 分支无条件 `set(HIDAPI_WITH_LIBUSB ON)`，覆盖命令行选项 | 打补丁：将 Linux 系统名匹配扩展为 Linux/HarmonyOS/OHOS，else 分支尊重外部变量 |
| 5 | Iconv 缺失 | 鸿蒙平台无 iconv | 添加 `-DHIDAPI_NO_ICONV=ON` 禁用 |
| 6 | GitHub 直连下载失败 | 网络限制 | 使用 gh-proxy 镜像源下载源码 |

## 源码修改

- `src/CMakeLists.txt`：系统名匹配 `Linux` → `Linux|HarmonyOS|OHOS`，else 分支不再强制开启 libusb 后端（补丁：0001-src-CMakeLists.txt.patch）

## 依赖版本

- libudev-zero/1.0.4（提供 libudev 兼容实现）

## 验证结果

```bash
conan create archives/h/hidapi/0.12.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 结果: PASS（G0-G4 + L2/L4/L5 全部通过）
# 产物: libhidapi-hidraw.a + hidapi.h
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 构建配方 |
| conandata.yml | 源码地址与 sha256 |
| patches/0001-src-CMakeLists.txt.patch | OHOS 平台适配补丁 |
| test_package/ | 消费者验证测试（test.c） |

## 注意事项

- hidapi 在鸿蒙平台仅构建 hidraw 后端（直接访问 /dev/hidraw* 设备节点），不依赖 libusb
- 静态库产物：libhidapi-hidraw.a
---

**编译结束**: 2026-08-11 11:56
**最终状态**: built
