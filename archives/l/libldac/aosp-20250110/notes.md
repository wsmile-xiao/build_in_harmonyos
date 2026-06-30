# libldac aosp-20250110 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 从 AOSP 镜像克隆源码：`git clone --depth 1 https://mirrors.ustc.edu.cn/aosp/platform/external/libldac`
2. 创建源码包：`tar -czf libldac-aosp-20250110.tar.gz`
3. 初始化编译环境：`ohc-run.py init-build libldac aosp-20250110`
4. 创建 CMakeLists.txt 文件（原项目使用 Android.bp 构建系统）
5. 配置：`cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX`
6. 编译：`make -j2`
7. 安装：`make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码无法从 GitHub/android.googlesource.com 下载 | 网络访问受限 | 使用 AOSP 国内镜像（mirrors.ustc.edu.cn） |
| 2 | 原项目使用 Android.bp 构建系统，不支持标准构建工具 | Android 构建系统限制 | 创建 CMakeLists.txt 文件，将源码编译逻辑转换为 CMake |
| 3 | clean_verify.py 不支持 CMake 构建系统 | 脚本只硬编码了 autotools | 修改 clean_verify.py，添加构建系统检测逻辑（检测 CMakeLists.txt） |
| 4 | CMake 参数格式错误 | 脚本使用 --prefix= 格式 | 修改脚本，为 CMake 使用 -DCMAKE_INSTALL_PREFIX= 格式 |
| 5 | make 在错误的目录运行 | 脚本未考虑 CMake 的 build 目录 | 修改脚本，添加 make_dir 变量，根据构建系统选择正确的目录 |

## 源码修改

**新增文件：CMakeLists.txt**
- 将 Android.bp 构建逻辑转换为 CMake
- 构建两个库：libldacBT_enc.so 和 libldacBT_abr.so
- 安装头文件：ldacBT.h 和 ldacBT_abr.h

## 依赖版本

无外部依赖（纯 C 库）

## 验证结果

```bash
# G0 干净构建验证
ohc-run.py clean-verify libldac aosp-20250110
结果：✅ G0 干净构建验证通过

# 编译产物检查
ls -lh /storage/Users/currentUser/test-install-libldac-aosp-20250110/storage/Users/currentUser/usr/local/lib/
结果：
libldacBT_enc.so  (62K)
libldacBT_abr.so  (18K)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libldacBT_enc.so | 62K | LDAC 编码器库 |
| libldacBT_abr.so | 18K | 自适应比特率库 |
| ldacBT.h | 22K | LDAC 编码器头文件 |
| ldacBT_abr.h | 7K | 自适应比特率头文件 |

## 注意事项

1. libldac 是索尼的 LDAC 音频编解码器，源自 AOSP 项目
2. 原项目使用 Android.bp 构建系统，需要转换为 CMake
3. 源码结构：所有源文件通过 #include 包含在 ldaclib.c 中
4. clean_verify.py 脚本需要修改以支持 CMake 构建系统（已提交技能改进）
5. 由于是库文件而非可执行程序，verify-build 可能报告"无二进制文件"，但这是正常情况
---

**编译结束**: 2026-06-03 15:25
**最终状态**: built
---

**编译结束**: 2026-06-03 16:00
**最终状态**: built
