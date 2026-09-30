# reliable

Más Bandwidth 出品的可靠 UDP 协议库（作者 Glenn Fiedler，即 *Gaffer on Games*
"Networked Physics" 系列作者）。在 UDP 之上提供：

- 包级 ACK 与丢包重传（`ACK_BUFFER` / `SENT_PACKETS` 序列缓冲）
- 大包自动分片与重组（`fragment_above` / `fragment_size` / `max_fragments`）
- 陈旧包与重复包拒收（滑动窗口 `received_packets_buffer_size`）
- 链路质量统计：RTT（min/max/avg）、jitter、packet loss、收发带宽
- 可替换分配器与收发回调（`allocate_function` / `transmit_packet_function`），
  不绑定任何 socket 实现，纯逻辑层

- 上游：https://github.com/mas-bandwidth/reliable
- 构建：CMake（单目标 `reliable`，默认静态库）
- 依赖：**无**（只用 C 标准库 + libm）
- 许可证：BSD-3-Clause（上游文件名拼写为 `LICENCE`）
- 测试：上游 `reliable.c` 内嵌测试套件（编译时 `RELIABLE_ENABLE_TESTS=1`），
  由 `test.cpp` 驱动；`CMakeLists.txt` 在 `RELIABLE_BUILD_TESTS=ON` 时
  注册 `test` / `fuzz` / `soak` / `fuzz_target` 四条 ctest

## OHOS 适配

- **零补丁**：上游源码在 clang/musl 生态（含 OHOS）零改动即可构建。配方不含
  任何 `patches/`，`conandata.yml` 的 `patches:` 段为空。
- **libm**：`reliable.c` 用 `fabs`（5 处）与 `pow`（1 处）计算 RTT/jitter/
  带宽统计，静态库消费者需显式链接 libm，故 `package_info` 中按
  `os in ("Linux", "OHOS")` 声明 `system_libs = ["m"]`。
- **上游测试真实执行**：不关闭 `RELIABLE_BUILD_TESTS`，而是在 `build()` 内
  用 `cmake.test()` 跑全部 4 条 ctest，结果进入 CI 日志（对应 L1c）。
  上游测试**零修改**。
- **包内清理**：删除上游安装的 `lib/pkgconfig/reliable.pc`（其 prefix 是构建机
  绝对路径，且 CMakeDeps 消费者不使用 pkgconfig）。
- **无上游 CMake config 冲突**：上游没有 `install(EXPORT)`，包内不存在
  `lib/cmake/reliable/`，因此无需做"移除上游 config"这一步。

## References

- https://github.com/mas-bandwidth/reliable
- https://github.com/mas-bandwidth/yojimbo（上游作者在其上构建的完整游戏网络层）
