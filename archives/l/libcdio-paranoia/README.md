# libcdio-paranoia

libcdio-paranoia 是用于 CD 音频读取、抖动校正和错误恢复的 C 库，同时提供 `cd-paranoia` 命令行工具。

## 功能

- 导出 `libcdio_cdda` 和 `libcdio_paranoia` 静态库
- 提供 CDDA、TOC 和音频提取接口
- 提供 `cd-paranoia` 音频抓取工具
- 支持确定性的 BIN/CUE 镜像测试

## HarmonyOS PC 适配

- 使用 clang/clang++ 构建 `aarch64-unknown-linux-ohos` 静态目标。
- 为旧版 Autotools 补充 OHOS triplet 识别，并修复 HMDFS configure 临时目录权限。
- 通过 `libcdio/2.3.0` 的私有静态依赖前缀规避历史 `.la` 文件中的构建机绝对路径。
- 无物理音频光盘时，上游物理设备测试按原逻辑跳过；BIN/CUE 离线回归测试仍执行。

## 依赖

构建依赖为 Conan 包 `libcdio/2.3.0`。运行库和 `cd-paranoia` 均采用静态链接，消费者通过 Conan 传递获得 libcdio 头文件和库。

## 参考资料

- 官网：https://www.gnu.org/software/libcdio/
- 源码仓库：https://github.com/libcdio/libcdio-paranoia
- 版本配方：[`10.2-2.0.2/`](10.2-2.0.2/)
