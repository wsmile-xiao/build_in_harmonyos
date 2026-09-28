# libioth

Internet of Threads 统一套接字 API（VirtualSquare 团队，LGPL-2.1-or-later）。

核心库：`ioth`（运行时可加载栈插件之上的套接字复用）+ `iothaddr`（基于哈希的 IPv6/MAC 辅助函数），头文件为 `ioth.h` / `iothaddr.h`，库名为 `ioth` / `iothaddr`。

## OHOS 适配

- **构建系统**：CMake，与上游官方构建方式一致（`cmake .. && make && make install`）。
- **依赖**：`libfduserdata/0.1.2` 与 `mhash/0.9.9.9`（本仓库已适配配方）；`nlinline 0.2.2`（被 `ioth.h` 包含的 header-only 库）暂无 OHOS 配方，在 `source()` 内获取官方 tag 源码并随包安装头文件。
- **插件**：`vdestack` 是唯一需要 `libvdeplug` 的模块（尚无 OHOS 配方），缺失时仅跳过该插件，核心库不受影响。
- **线程库**：HarmonyOS libc 内含 pthread API，无独立 libpthread；在 HarmonyOS 上跳过 `-lpthread` 链接，Linux 上保留。
- **文档页**：`man/` 需要 pandoc + make，在 HarmonyOS 上跳过，不影响库本体。
- **静动态库**：上游硬编码 SHARED，补丁使其跟随 `BUILD_SHARED_LIBS`（默认静态），并补齐 ARCHIVE/RUNTIME 安装目标。
- **musl 兼容**：`dlmopen`/`LM_ID_*` 回退为 `dlopen`；`sockaddr_storage` 内核 tag 隐藏；去掉 `ioth_getifaddrs.c` 中无用的 `linux/if_arp.h`。
- **测试**：上游无任何自动化测试；test_package 提供 13 项 TAP 消费者测试覆盖 native 栈生命周期与 iothaddr 确定性向量。

## 参考

- 上游仓库：https://github.com/virtualsquare/libioth
- 上游版本：0.1.2（官方 tag）
- API 文档：源码内 `ioth.h` / `iothaddr.h` 头注释与 `README.md`
