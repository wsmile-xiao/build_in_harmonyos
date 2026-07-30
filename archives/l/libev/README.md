# libev

## 简介
libev 是高性能事件循环库，支持 epoll、kqueue、select 等多种后端。

## OHOS 适配
- 旧归档记录的 autotools `config.status` 在 HMDFS 上创建临时文件失败，因此配方生成等价 CMake 构建。
- SDK 11 未提供系统 `libev.so`，Conan 包默认构建共享库并保留 `libev.so.4` SONAME。
- OHOS 显式禁用未实现的 io_uring 后端，保留 CMake 探测到的 epoll、poll 和 select 后端。
- 共享库使用 `$ORIGIN` RUNPATH，避免 Windows 交叉安装阶段写入主机路径。

## 依赖
- 无第三方 Conan 依赖；仅使用目标系统 C/POSIX API。

## 功能验证
- `test_package` 校验 4.33 版本、默认事件循环和一次定时器回调。
- Windows 交叉构建只确认 AArch64 编译/链接；目标执行由原生 HarmonyOS CI 完成。

## 参考
- 主页: https://software.schmorp.de/pkg/libev.html
