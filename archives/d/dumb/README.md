# DUMB

DUMB (Dynamic Universal Music Bibliotheque) 是一个 tracker 音乐模块库（kode54/dumb，Zlib OR FreeType 双许可）。纯 C 实现模块文件的加载、解码与渲染：IT/XM/S3M/MOD 四大主流格式加 MTM/PTM/PSM/OKT/AMF/669/ASY/DSMF/RIFF 等十余种；内置高质量重采样器与 LPC（线性预测编码）助手；dumbfile 抽象层支持文件/内存/自定义 I/O。

## 功能概述
- 模块解析：IT/XM/S3M/MOD/MTM/PTM/PSM/OKT/AMF/669/ASY/DSMF/RIFF 全家桶
- 渲染：duh_start_sigrenderer + duh_render_int/float（任意采样率、8/16/24bit 整数或 32/64bit 浮点输出）
- 重采样器 + LPC + click removal（咔哒声消除）
- dumbfile I/O 抽象：文件/内存/注册自定义后端
- IT 效果全集兼容（速度/节拍/音量/声像/包络）
- 纯 C + libm，无其他依赖；无音频设备要求（渲染到内存）

## OHOS 适配
- 三开关关闭平台无关项：BUILD_EXAMPLES（需 argtable2+SDL2 音频）/ BUILD_ALLEGRO4 / USE_SSE（x86 专用）
- CMake 4.x 兼容：CMAKE_POLICY_VERSION_MINIMUM=3.5 环境变量 shim
- 上游无注册测试（N=0）：test_package 补 12 项断言（S3M/MOD 真解析器 + IT 渲染核心 headless 全链，ASan 复验）
- 产物 libdumb.so（动态库，Conan 管理依赖链）

## 依赖关系
- **编译依赖**: 无（libm 系统库）
- **运行依赖**: libm

## 参考资料
- 官网: https://github.com/kode54/dumb
- DUMBFILE_SYSTEM.md（自定义 I/O 后端指南，源码包内）
