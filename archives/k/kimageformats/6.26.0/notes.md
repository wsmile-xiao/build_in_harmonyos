# kimageformats 6.26.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-05
- 编译器: clang/clang++
- 目标平台: OpenHarmony NEXT (aarch64, musl libc, clang 15.0.4)
- 状态: built

## 编译步骤

1. ECM 6.26.0 升级安装到 /storage/Users/currentUser/usr/local
2. cmake配置:
```bash
cd /storage/Users/currentUser/tmp/builds/kimageformats-6.26.0.work/build
cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
      -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_TESTING=OFF \
      -DKF_IGNORE_PLATFORM_CHECK=TRUE \
      -DKIMAGEFORMATS_HEIF=OFF \
      -DKIMAGEFORMATS_JXL=OFF \
      -DKIMAGEFORMATS_JP2=OFF \
      -DKIMAGEFORMATS_WITH_KNOWN_CRASHES_JXR=OFF \
      -DCMAKE_C_COMPILER=clang \
      -DCMAKE_CXX_COMPILER=clang++
```
3. make 编译成功
4. make install DESTDIR=/storage/Users/currentUser/tmp/test-install-kimageformats-6.26.0 (staging install)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ECM 版本不匹配 | 原 ECM 6.10.0 太旧 | 升级 ECM 到 6.26.0 |
| 2 | HEIF/JXL/JP2/JXR 编译失败 | 这些格式依赖库在 musl OHOS 上不可用 | 禁用: KIMAGEFORMATS_HEIF=OFF, JXL=OFF, JP2=OFF, JXR=OFF |
| 3 | 平台检查失败 | OHOS 不在 KDE 支持平台列表中 | KF_IGNORE_PLATFORM_CHECK=TRUE |

## 源码修改

无源码修改，所有适配通过 cmake 选项完成。

## 依赖版本

- Qt6: 6.11.1
- ECM: 6.26.0

## 验证结果

17 个图像格式插件已编译: kimg_ani.so, kimg_dds.so, kimg_hdr.so, kimg_iff.so, kimg_pcx.so, kimg_pic.so, kimg_pfm.so, kimg_psd.so, kimg_pxr.so, kimg_qoi.so, kimg_ras.so, kimg_rgb.so, kimg_sct.so, kimg_tga.so, kimg_tim.so, kimg_xcf.so, kimg_raw.so

## 交付物

| 文件 | 说明 |
|------|------|
| kimageformats-6.26.0-ohos-aarch64.tar.gz | 主包 (17 plugins + cmake configs) |
| kimageformats-6.26.0-ohos-aarch64-debug.tar.gz | 调试符号包 |

## 注意事项

- ECM 版本必须与 kimageformats 版本匹配
- musl libc 下某些图像格式依赖不可用
---

**编译结束**: 2026-06-05 14:40
**最终状态**: built
