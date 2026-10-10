# 非 Windows 音频 GUID 的有符号字段导致 C++ narrowing

状态：草稿；来源：sndobj 2.6.7 鸿蒙 PC 可移植核心适配（2026-10-04）。

## 现象与根因

源码 `src/SndPVOCEX.h` 以 `0x8312b9c2` 初始化 `KSDATAFORMAT_SUBTYPE_PVOC`。非 Windows 路径的 `src/SndWaveX.h` 却把 `GUID::Data1` 声明为 `int`，`Data2/Data3` 为 `short`。本地 GCC 16 在编译 `PVRead.cpp` 时报告从 `unsigned int` 到 `int` 的 narrowing，构建中断。Windows 路径使用系统 `Windows.h`，不受该兼容结构影响。

标准 GUID 的前三个字段是无符号 32/16/16 位。对非 Windows 兼容结构作最小字段类型修正，比加入 `-Wno-narrowing` 或强制转换更能保持原始二进制值的语义。

## 处理方式

在 `#ifndef WIN` 下将 `Data1` 改为 `unsigned int`，`Data2/Data3` 改为 `unsigned short`，保留 `Data4[8]`。补丁位于 `archives/s/sndobj/2.6.7/patches/0001-src-SndWaveX.h.patch`。同类库应先核对目标平台位宽、结构布局和文件格式契约；位宽不确定时使用定宽类型和静态断言。

## 验证与边界

- 修正后，本地 Windows GCC 完整编译可移植核心及捆绑的 FFTW 2 源码成功。
- 鸿蒙 arm64 目标机上 `conan create` 生成 `libsndobj.so`，安装后的消费者调用 `HarmTable`/`Oscili` 并完成 3/3 条件验证；真机事务 `sndobj-w3-20261003T174232Z` 12/12 回执通过。
- 源包的 `SConstruct` 不提供非交互式自动测试目标；`src/examples/test.cpp` 与 `python/test.py` 都依赖实时音频设备。当前配方选择 `NO_RTIO` 可移植核心，未声称实时音频后端已验证。
- 与已有 SCons 环境自举、Autotools 转 CMake overlay 草稿不同，本条只处理 GUID 字段 signedness 引起的 C++ 源码编译错误。
