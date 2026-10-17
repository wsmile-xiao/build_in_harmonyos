# thc 3.8 (THC IPv6 Attack Toolkit)

OpenHarmony / OHOS PC (aarch64) Conan 2.29 适配配方。

- 上游：`vanhauser-thc/thc-ipv6` v3.8
- 构建系统：手写 Makefile（68 个工具 + 5 个 EXTRA）
- 依赖：libpcap/1.10.6、openssl/3.5.6、libnetfilter_queue/1.0.5

## 适配摘要
- 编译器取自 conan conf（R33），非裸 shell 变量。
- patch `0001-makefile-ohos.patch`：移除 `-march=native`/`-flto`（OHOS clang 不支持）与
  `-lresolv`/`-lrt`（musl 已并入 libc）；构建传 `MANPAGES=` 避免运行二进制生成 man 页。
- 依赖 include/lib 经 CPPFLAGS/LDFLAGS 注入。
- 无 `__OHOS__` 平台宏（R8 合规）；无 sockaddr_storage 冲突，无需特性检测补丁。

## 测试
- R51：上游无自动化测试套件（仅 `6to4test.sh` 运维脚本）。
- 消费者冒烟测试：见 `test_package/test.sh`（address6 离线解析，3 条断言）。
