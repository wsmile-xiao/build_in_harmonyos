# libfduserdata

将用户自定义数据与文件描述符关联的线程安全哈希表小库（VirtualSquare 团队，LGPL-2.1-or-later）。

核心 API：`fduserdata_create` / `fduserdata_destroy` / `fduserdata_destroy_cb` / `fduserdata_new` / `fduserdata_get` / `fduserdata_put` / `fduserdata_del`，头文件为 `fduserdata.h`，库名为 `fduserdata`。

## OHOS 适配

- **构建系统**：CMake，与上游官方构建方式一致（`cmake .. && make && make install`）。
- **线程库**：HarmonyOS libc 内含 pthread API，无独立 libpthread；在 HarmonyOS 上跳过 `-lpthread` 链接，Linux 上保留。
- **文档页**：`man/` 需要 pandoc，在 HarmonyOS 上跳过，不影响库本体。
- **静动态库**：上游硬编码 SHARED，补丁使其跟随 `BUILD_SHARED_LIBS`（默认静态）。
- **测试**：上游无任何测试；test_package 提供 12 项 TAP 消费者测试覆盖创建/新增/查询/归还/删除/回调销毁全链路。
- **依赖关系**：无编译依赖，无运行依赖；纯 C 库，只依赖系统 libc（含 pthread）。

## 参考

- 上游仓库：https://github.com/rd235/libfduserdata
- 上游版本：0.1.2（官方 tag）
- API 文档：源码内 `fduserdata.h` 头注释与 `README.md`
