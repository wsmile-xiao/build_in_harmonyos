# libmygpo

libmygpo-qt 是 gpodder.net 播客 API 的 Qt 客户端库，提供设备、播客、订阅及播放动作等数据接口。

OHOS 适配保留全部生产源文件和上游 QtTest，使用已发布 Qt 的原生 CMake 配置及 moc。安装配置导出可迁移 include 路径和 Qt Core/Network 依赖；测试日期 fixture 显式声明 UTC，并区分两种 Qt JSON 日期格式。

构建/运行依赖为 Qt Core、Network；测试额外使用 Qt Test，不依赖真实网络服务。制品状态以版本目录的实际验证记录和发布流水线为准。

上游：[gpodder/libmygpo-qt](https://github.com/gpodder/libmygpo-qt)。
