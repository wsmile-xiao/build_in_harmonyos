# utimer

utimer 是基于 GLib 的命令行计时、倒计时和秒表工具。

鸿蒙 PC 配方保留上游计时、键盘交互、参数解析和 gettext 调用，使用 CMake 编译完整生产源文件以及未修改的 GLib GTest 测试。针对 Clang 修正头文件声明与全局变量定义，初始化计时器 source ID，并用文件描述符读取避免开放 stdin 时退出阻塞。EOF 只结束输入监听，不提前终止计时。

编译及运行依赖为 Conan 管理的 GLib 和 proxy-libintl。CLI 功能验证不要求交互式终端；暂停/恢复按键的人工交互未包含在自动消费者结论中。

上游：https://launchpad.net/utimer 。来源及每版具体验证见版本目录。当前配方完成原生构建与回归，但尚未提交 PR 或发布制品。
