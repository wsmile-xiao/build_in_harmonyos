# libevent

## 简介
libevent 是事件通知库，提供快速非阻塞 I/O 支持，广泛用于网络服务程序。

## OHOS 适配
- 推荐 CMake 构建，避免 autotools 临时目录权限问题
- config.guess 需更新以识别 HarmonyOS
- OpenSSL 支持可选，系统缺少开发文件时可用 `-DEVENT__DISABLE_OPENSSL=ON` 禁用
- 测试套件在 HarmonyOS 上部分失败（epoll/mmap 差异），核心事件循环功能正常

## 依赖
- openssl（可选，可禁用）

## 功能验证
```bash
ls -la $HOME/usr/local/lib/libevent*
```

## 参考
- 主页: https://libevent.org/
- 源码: https://github.com/libevent/libevent
