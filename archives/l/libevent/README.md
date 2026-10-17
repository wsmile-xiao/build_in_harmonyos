# libevent

## 简介
libevent 是事件通知库，提供快速非阻塞 I/O 支持，广泛用于网络服务程序。

## OHOS 适配
- 2.1.13 使用上游 CMake 构建，保留官方 regress 与外围测试。
- HarmonyOS 共享库输出为真实无版本 `.so`，避免依赖 HMDFS 软链接。
- OpenSSL 是可选功能；当前配方显式禁用，不引入未声明依赖。
- `event_rpcgen.py` 随包安装到 `bin/`，可由 Conan 运行环境发现。

## 依赖
- zlib/1.3.1.1（仅用于构建阶段官方 regress 测试）
- OpenSSL（可选，当前禁用）

## 功能验证
```bash
conan create archives/l/libevent/2.1.13
```

## 参考
- 主页: https://libevent.org/
- 源码: https://github.com/libevent/libevent
