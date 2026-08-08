# adobe-source-serif 4.005 适配笔记

## 上游与产物

- 使用 Adobe 官方 `4.005R` 的 Desktop 发布包。
- 包含 60 个静态 OTF、60 个静态 TTF 和 4 个 OTF/TTF 可变字体。
- 安装目录为 `share/fonts/adobe-source-serif/`，保留 OTF、TTF 与 variable 分类。

## OHOS 适配

字体是平台无关资源，无需补丁，也没有编译过程。配方仍在 `build()` 阶段核对
官方发布物的精确文件数量，避免上游下载内容或目录结构静默变化。

## 测试口径

上游 Desktop 发布包不包含 `test`/`tests` 目录、测试目标或自动化测试脚本，
所以不存在可以执行和计数的上游测试，不能写成“0/0 通过”。适配后的消费者测试
会逐个读取 124 个已打包字体，验证 SFNT/OpenType 头、表边界和必要表；另用截断
字体执行故障注入，必须被解析器拒绝。

## 状态

- Linux x86_64 Conan `conan create + test_package`：2/2 消费测试通过；其中正向
  测试解析 124 个字体并核对精确数量，负向测试确认损坏字体被拒绝。
- DevEco OHOS 工具链：同一消费者源码成功生成 ELF64 AArch64 产物。
- HarmonyOS PC 模拟器（HarmonyOS 6.1.0，x86_64）：代表 OTF 解析与损坏字体拒绝
  2/2 通过。
