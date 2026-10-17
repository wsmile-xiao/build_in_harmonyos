# audioflux

audioFlux — 音频/音乐分析与特征提取库（MIT License）。

上游：https://github.com/libAudioFlux/audioFlux

## 版本索引

| 版本 | 状态 | 构建系统 | 说明 |
|------|------|----------|------|
| 0.1.9 | published | CMake + setuptools | C 核心 libaudioflux.so + Python ctypes 包装（OHOS aarch64） |

## 说明

- C 核心由 src/CMakeLists.txt 构建共享库 libaudioflux.so（OpenMP 加速，SDK libomp），
  Python 包装 python/audioflux/ 经 ctypes 加载。
- OHOS 适配：补丁新增 HarmonyOS CMake 分支（0002-src-CMakeLists.txt.patch）、
  fftlib.py 识别 harmonyos 平台（0001-python-audioflux-fftlib.py.patch）。
- 上游无独立测试套件（官方 tag 无 tests/），benchmark/ 为性能对比脚本。
