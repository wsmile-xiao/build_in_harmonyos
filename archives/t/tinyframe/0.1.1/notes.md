# tinyframe 0.1.1 HarmonyOS PC 迁移说明

## 源码与构建

- 官方源码：DNS-OARC/tinyframe `v0.1.1`
- 源码 SHA-256：`356aba1fe52a48784a37189c683902ae7600dff2c865c9c2837abf757c44460d`
- 构建系统：Autotools
- 目标平台：HarmonyOS PC aarch64

GitHub tag 归档仅包含 `configure.ac`，配方使用 automake 与 libtool 执行
`autoreconf`。`PKG_INSTALLDIR` 来自 pkg-config 的 `pkg.m4`，配方根据
`pkg-config` 可执行文件位置探测宏目录，不绑定 SDK 的具体版本路径。

HarmonyOS PC 的 HMDFS 对 Autoconf 临时目录和 GNU make 并行 jobserver FIFO
有权限限制，因此配方提供一个仅令 `mktemp` 探测失败的构建期包装器，使
Autoconf 使用其可移植的 mkdir 回退路径，并使用 `make -j1`。源码补丁只在
`configure.ac` 中识别 HarmonyOS uname 三元组；未修改库逻辑或上游测试。

## 测试

上游 `make check` 注册 3 个脚本；按脚本中的实际程序调用计为 9 个场景：

- `test1.sh`：6 种分块大小读取 Frame Streams 文件；
- `test2.sh`：写入、读取 2 个场景；
- `test3.sh`：1 个 API 边界与错误处理场景。

消费者测试声明 10 项：9 项覆盖帧大小、字节序、控制帧、数据帧往返、
停止/结束状态、分段输入和非法字段；另有 1 项 HarmonyOS PC 专属测试，
验证运行内核、aarch64 数据模型和页面大小。
