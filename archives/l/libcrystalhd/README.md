# libcrystalhd

Broadcom CrystalHD 硬件视频解码库（用户空间部分），支持 BCM970012/BCM970015 设备。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 20130708 | published | 2026-06-01 |

## 鸿蒙平台功能测试结果

| 测试项 | 状态 | 说明 |
|--------|------|------|
| 编译链接 | ✅ 可用 | 头文件和库文件完整，可正常编译链接 |
| 动态加载 | ✅ 可用 | dlopen加载成功，206个导出符号 |
| 非设备API | ✅ 可用 | DtsCrystalHDVersion等不依赖硬件的API可正常调用 |
| 设备交互API | ❌ 不可用 | DtsDeviceOpen等需/dev/crystalhd的API触发SIGSYS |
| SSE2替代 | ✅ 可用 | aarch64上使用C路径（gSSE2=false），stub正确编译 |

**结论**: 库本身无平台兼容性问题，可正常编译、链接和加载。硬件交互功能不可用是硬件依赖限制而非平台bug。

## 注意事项

- 依赖 Broadcom CrystalHD 硬件（BCM970012/BCM970015），无硬件设备时核心解码功能不可用
- SSE2 路径在 aarch64 上使用 stub 替代，运行时仅使用普通 C 路径
- 源码来自 Debian snapshot（0.0~git20110715.fdd2f19），因网络限制无法获取 GitHub 版本
- 未包含 firmware 文件（bcm70012fw.bin, bcm70015fw.bin）
- DtsGetDILVersion/DtsGetDriverVersion符号不存在（本版本有DtsGetVersion/DtsGetDriverStatus替代）
- 预编译包RUNPATH($ORIGIN)正确；本地安装RUNPATH已修复为$ORIGIN（原为错误文件路径）
- 预编译包debug sections已分离(.symtab保留为设计选择)