# libvpx 1.14.1 适配笔记

## 编译环境
- 构建系统: custom（libvpx 使用自定义 configure 脚本）
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: built（编译成功，但 G0 验证未通过）

## 编译步骤

1. **初始化环境**：设置 CC=clang, CXX=clang++
2. **Configure**：`./configure --target=arm64-linux-gcc --prefix=$DEFAULT_PREFIX`
3. **手动生成 rtcd.h 文件**（关键步骤）：
   ```bash
   perl build/make/rtcd.pl --arch=arm64 --sym=vpx_scale_rtcd --config=libs-arm64-linux-gcc.mk vpx_scale/vpx_scale_rtcd.pl > vpx_scale_rtcd.h
   perl build/make/rtcd.pl --arch=arm64 --sym=vpx_dsp_rtcd --config=libs-arm64-linux-gcc.mk vpx_dsp/vpx_dsp_rtcd_defs.pl > vpx_dsp_rtcd.h
   perl build/make/rtcd.pl --arch=arm64 --sym=vp8_rtcd --config=libs-arm64-linux-gcc.mk vp8/common/rtcd_defs.pl > vp8_rtcd.h
   perl build/make/rtcd.pl --arch=arm64 --sym=vp9_rtcd --config=libs-arm64-linux-gcc.mk vp9/common/vp9_rtcd_defs.pl > vp9_rtcd.h
   ```
4. **编译**：`make -j4`
5. **安装**：`make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败：Unable to invoke compiler: gcc | libvpx 默认查找 gcc，但系统只有 clang | 设置环境变量 CC=clang CXX=clang++ |
| 2 | 编译失败：缺少 vp9_rtcd.h, vpx_dsp_rtcd.h, vpx_scale_rtcd.h, vp8_rtcd.h | configure 后这些文件未自动生成到源码根目录 | 使用 rtcd.pl 脚本手动生成，需配合 libs-arm64-linux-gcc.mk 配置文件 |
| 3 | G0 干净构建验证失败 | rtcd.h 文件是构建时生成的，不属于源码 | 需要创建补丁或hints来处理此问题（待解决） |

## 关键知识提取

**libvpx rtcd.h 生成机制**：
- libvpx 使用 rtcd.pl Perl 脚本生成运行时 CPU 检测头文件
- configure 会生成 `libs-arm64-linux-gcc.mk` 配置文件
- rtcd.h 文件需要在 configure 之后手动生成，使用配置文件中的参数
- 生成的文件位于源码根目录，包含特定架构的 SIMD 函数调用表

## 源码修改

无补丁。rtcd.h 文件是构建产物，不应作为补丁。

## 依赖版本

- Perl（用于 rtcd.pl 脚本）
- clang 15.0.4

## 验证结果

```bash
# 编译产物验证
ls -lh vpx_scale_rtcd.h vp8_rtcd.h vp9_rtcd.h vpx_dsp_rtcd.h
# 输出：
# vp8_rtcd.h     12K
# vp9_rtcd.h    5.8K
# vpx_dsp_rtcd.h 97K
# vpx_scale_rtcd.h 2.8K

# 安装产物验证
ls -la $TEST_PREFIX/$DEFAULT_PREFIX/bin/
# vpxdec, vpxenc 已安装
```

## 交付物

暂无预编译包（因 G0 验证未通过）

## 注意事项

⚠️ **关键发现**：libvpx 的 rtcd.h 头文件生成是一个特殊的构建流程，不同于常规 autotools 项目。需要：
1. 在 configure 之后额外执行 rtcd.pl 脚本
2. 使用正确的配置文件（libs-arm64-linux-gcc.mk）
3. 不能作为补丁，因为这些文件是动态生成的

## 下一步行动

1. 创建 hints 文件来处理 rtcd.h 生成问题
2. 重新执行 finish 命令
3. 通过 G0 验证后创建预编译包
---

**编译结束**: 2026-05-21 10:12
**最终状态**: built
