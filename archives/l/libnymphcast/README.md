# libnymphcast

libnymphcast 是 NymphCast 投屏系统的客户端库（C++），负责媒体文件搜索、
服务发现（NyanSD）、连接接收端并控制播放。

## OHOS 适配要点

- **依赖**：NymphRPC（`nymph/nymph.h` 头 + `-lnymphrpc`）+ POCO 1.5+（PocoNet/PocoUtil/PocoFoundation/PocoJSON）。均通过 Conan 管理。
- **C++17**：HarmonyOS SDK libc++ 需要 C++17，上游 Makefile 已写死 `-std=c++17`，天然匹配。
- **make -j1**：OHOS SELinux 禁 FIFO（make jobserver 不可用），统一单线程构建。
- **无上游测试**：v0.2.1 源码不含 `test/` 目录，`make test` 为悬空 target；验证走 test_package 消费层。

## 依赖关系

```
libnymphcast
  ├── NymphRPC v0.1.1（必需，nymph/nymph.h + libnymphrpc.a）
  └── POCO 1.15.3（必需）
      ├── PocoNet / PocoUtil / PocoFoundation / PocoJSON
      └── OpenSSL（可选，仅 C 绑定示例链 PocoNetSSL）
```

## 参考
- https://github.com/MayaPosch/libnymphcast
