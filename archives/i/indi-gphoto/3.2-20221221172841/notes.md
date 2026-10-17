# indi-gphoto 3.2-20221221172841 适配笔记

## 编译环境
- 构建系统: cmake（indi-3rdparty monorepo 子目录 indi-gphoto/）
- 编译日期: 2026-10-11
- 编译器: clang 15（OHOS aarch64 交叉，Conan profile ohos-aarch64）
- 状态: published

## 编译步骤

conan create（conanfile.py + conandata.yml，源码来自
https://github.com/indilib/indi-3rdparty/archive/refs/tags/v2.0.2.tar.gz，
v2.0.2 release tag 对应上游 indi-gphoto 驱动版本 3.2）。
全部 find_package 走 monorepo 的 legacy Find*.cmake（变量式），
在 conanfile.generate() 中以 toolchain 变量喂入 Conan 依赖包路径（R49，
build-folder 私有注入，无共享系统前缀）。

## 上游测试清点（R51）

- 清单 `indi-gphoto/`：CMakeLists.txt、gphoto_ccd.cpp/h、gphoto_driver.cpp/h、
  gphoto_readimage.cpp/h、dsusbdriver.cpp/h、config.h.cmake、indi_gphoto.xml.cmake、
  85-disable-dslr-automout.rules、indi-gphoto.spec、README 等。
- CMakeLists.txt 无 enable_testing()/add_test()，indi-3rdparty 全仓（v2.0.2）无该驱动测试用例
  → **上游确无测试**（evidence：grep enable_testing/add_test 无命中）。
- 交付测试为 test_package 自带消费者校验（check_driver.py，4 项断言，见 test_package/MANIFEST.yml）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | defaultdevice.h `std::any` 报错（no type named 'any'） | monorepo 共享 cmake_modules/CMakeCommon.cmake 硬编码 `set(CMAKE_CXX_STANDARD 14)`，目录级 set 覆盖了 Conan toolchain 的 cache 默认 17 | 补丁 0001 增 hunk：CMakeCommon 14→17（libindi 2.2 头文件需要 C++17） |
| 2 | gphoto_ccd.cpp FocuserInterface 回调 8 处旧 API 报错（IDSetNumber/.s/受保护 operator&） | 补丁 0004 的 upstream backport 漏掉 UpdateFocusMotionCallback() | 补丁 0004 追加 hunk：`FocusMotionSP.findOnSwitchIndex()`、`FocusRelPosNP.setState()+apply()` |
| 3 | check_driver 报 DT_NEEDED 含绝对路径（libraw.so） | libraw 包的 .so 无 SONAME，绝对路径传给链接器时被整体写进 DT_NEEDED | conanfile 改为 `LibRaw_LIBRARIES="raw"` + `-L<libdir> -Wl,-rpath-link,<libdir>`，按裸名链接 |

## 源码修改

全部以 patches/ 交付（conandata.yml 声明）：
- 0001 cmake 构建脚本：cmake_minimum_required 3.16（CMake 4）、INDI 组件 driver+client、
  LibRaw/JPEG/zlib include 路径、CMakeCommon C++14→17
- 0002 FindINDI：INDI_VERSION 正则兼容带引号字符串宏（libindi ≥ 2.2）
- 0003 FindLibRaw：libraw_version.h 位于 libraw/ 子目录（Conan 布局）
- 0004 backport 上游 libindi 2.x 新属性 API（commits 913c233635 / fa35d7594a / ba7ca67400，
  含 FocuserInterface 回调迁移）

## 依赖版本

libindi/2.2.2.1, libgphoto2/2.5.31, cfitsio/4.6.4, libraw/0.22.1,
libjpeg-turbo/3.2.0, libusb/1.0.27, zlib/1.3.1.1（均已发布于 ohpcd 制品仓）

## 验证结果

```bash
conan create . -pr:h ohos-aarch64 -pr:b default --build=missing
# Package '1cf8b420...' created
conan test test_package indi-gphoto/3.2-20221221172841
# checks=4 fails=0 skips=1  RESULT: PASS
# skip 项：真机宿主加载器拒绝加载未签名 OHOS so（FUSE mmap 受限，平台限制，非打包缺陷）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/indi_gphoto_ccd | 195200 B | AArch64 ELF 驱动主程序 |
| bin/indi_sony_ccd 等 | symlink | 品牌别名（打包为独立副本/链接） |
| share/indi/indi_gphoto.xml | - | INDI 驱动描述文件 |

## 注意事项

- indi-gphoto CMakeLists 会 append `../cmake_modules`，因此源码整仓保留（strip_root=True）。
- 运行时依赖 libindi 的共享对象（static-first 发布），conanfile 在 runenv_info 里显式
  prepend libindi libdir 到 LD_LIBRARY_PATH。
- UDEVRULES_INSTALL_DIR / INDI_DATA_DIR 均改为相对路径，安装进本包而非系统目录。
---

**编译结束**: 2026-10-11 18:43
**最终状态**: built
