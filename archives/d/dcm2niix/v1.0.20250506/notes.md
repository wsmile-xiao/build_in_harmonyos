# dcm2niix v1.0.20250506 适配笔记

## 编译环境
- 构建系统: cmake（SuperBuild + ExternalProject_Add）
- 编译日期: 2026-05-28
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. 源码下载：从 GitHub 下载 v1.0.20250506 tag 的 tar.gz
2. cmake 配置：
   ```bash
   mkdir build && cd build
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DCMAKE_C_COMPILER=clang \
         -DCMAKE_CXX_COMPILER=clang++ \
         -DUSE_STATIC_RUNTIME=OFF \
         -DCMAKE_BUILD_TYPE=Release ..
   ```
3. make -j2 编译
4. make install DESTDIR=$TEST_PREFIX（staging 安装）
5. 项目未注册 ctest（未定义 enable_testing），但通过 Git submodule 引用 3 个独立数据驱动回归测试套件（dcm_qa、dcm_qa_nih、dcm_qa_uih），各含 batch.sh 对真实多厂商 DICOM 数据执行转换并与 Ref 参考输出比对
6. staging 验证通过
7. package 制作预编译包
8. make install（不带 DESTDIR，本地安装验证）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接错误：ld.lld: error: unknown argument '-dead_strip' | console/CMakeLists.txt 中 Clang 分支使用了 macOS 专用链接标志 `-Wl,-dead_strip`，在 Linux/HarmonyOS 的 ld.lld 上不支持 | 修改 CMakeLists.txt，将 Clang 分支的链接标志改为条件判断：Apple 使用 `-Wl,-dead_strip`，非 Apple 使用 `-Wl,--gc-sections` |

## 源码修改

- console/CMakeLists.txt: 将 Clang 编译器分支中无条件设置 `-Wl,-dead_strip` 改为条件判断
  - Apple: `-Wl,-dead_strip`（原行为，macOS dead code elimination）
  - 非 Apple（Linux/HarmonyOS）: `-Wl,--gc-sections`（ELF 平台等效功能）

## 依赖说明

无外部依赖。项目使用内置的 Miniz 作为 zlib 实现，无 TurboJPEG/Jasper/OpenJPEG/JPEGLS 依赖。

## 功能验证（真实执行）

使用 Python 生成 3 个标准 DICOM MR 切片文件（16×16像素），通过 dcm2niix 执行 DICOM→NIfTI 转换：

### 输入
- 3 个 DICOM 切片文件（test_mr_01.dcm ~ test_mr_03.dcm）
- 每切片 16×16 像素，16-bit，间距 5mm
- 模态：MR，厂商：OpenHarmony

### 转换命令
```bash
dcm2niix -v 2 -o ~/tmp/dcm2niix-test/nifti-output3 ~/tmp/dcm2niix-test/input3
```

### 转换输出
```
Chris Rorden's dcm2niiX version v1.0.20250505  Clang15.0.4 ARM (64-bit Linux)
Found 3 DICOM file(s)
Convert 3 DICOM as input3_000000_1 (16x16x3x1)
Conversion required 0.035051 seconds (0.032479 for core code).
```

### 输出文件验证
- `input3_000000_1.nii`：NIfTI 3D volume（16×16×3×1，像素尺寸 1×1×5mm）
- `input3_000000_1.json`：BIDS JSON 侧边文件（包含 Modality=MR、转换软件=dcm2niix v1.0.20250505）

### 验证结论
✅ dcm2niix 核心功能验证通过：
- DICOM 文件识别 ✅
- 多切片合并为 3D volume ✅
- NIfTI 格式输出 ✅
- BIDS JSON 侧边文件生成 ✅
- 图像维度和像素尺寸正确 ✅

## 版本验证

```bash
$ dcm2niix --version
Chris Rorden's dcm2niiX version v1.0.20250505  Clang15.0.4 ARM (64-bit Linux)
v1.0.20250505
```

注意：源码内嵌版本号为 v1.0.20250505，GitHub release tag 为 v1.0.20250506。这是项目本身的行为（release tag 在版本号更新后创建）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| dcm2niix-v1.0.20250506-ohos-aarch64.tar.gz | 497KB | 预编译包（含 stripped ELF 签名二进制） |
| dcm2niix-v1.0.20250506-ohos-aarch64-debug.tar.gz | 92KB | 调试符号包 |
| 0001-console-CMakeLists.txt.patch | 1.4KB | 平台适配补丁 |

## 注意事项

- dcm2niix 使用 SuperBuild CMake 结构（ExternalProject_Add），构建时先配置顶层再自动配置 console 子项目
- 源码版本号 v1.0.20250505 与 release tag v1.0.20250506 不一致，这是项目本身的行为
- 项目未注册 ctest，但通过 dcm_qa、dcm_qa_nih、dcm_qa_uih 三个 Git 子模块提供数据驱动回归测试
- USE_STATIC_RUNTIME=OFF 是因为 Clang 在 HarmonyOS 平台上静态链接 stdc++ 可能有问题
- G0 干净构建验证：脚本 clean_verify 不支持 cmake 构建系统，已手动从干净源码+补丁验证编译自包含性通过

---

**编译结束**: 2026-05-28 10:21
**最终状态**: built
---

**编译结束**: 2026-05-28 10:24
**最终状态**: built
