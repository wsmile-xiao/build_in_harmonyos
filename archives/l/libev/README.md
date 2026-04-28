# libev

## 简介
libev 是高性能事件循环库，支持 epoll、kqueue、select 等多种后端。

## OHOS 适配
- autotools 构建因 HMDFS 文件系统限制导致 config.status 失败
- 采用手动编译方式：`clang -c -fPIC -O2 ev.c event.c`
- 需要更新 config.guess/config.sub 支持 HarmonyOS
- tar.gz 在 HMDFS 上创建失败(ustar header 限制)，预编译包使用 zip 格式

## 排除与替代
- autotools 不可用 → 手动编译替代
- tar.gz 不可用 → zip 格式替代

## 依赖
- 无编译依赖

## 功能验证
```bash
ls -la $HOME/usr/local/lib/libev*
# 测试程序验证 libev version: 4.33
```

## 参考
- 主页: http://software.schmorp.de/pkg/libev.html
