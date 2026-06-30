# Gauche

Gauche 是一个 Scheme 脚本语言实现，专为脚本编写和系统集成设计。

## 特性

- R7RS（small and large）兼容
- UTF-8 和 Unicode 支持
- 多线程支持
- 超过 200 个扩展库

## 编译状态

- **0.9.15**: built（部分成功）

## 验证命令

```bash
gosh -V
# 输出：Gauche scheme shell, version 0.9.15 [utf-8,pthreads], aarch64-unknown-linux-ohos
```

## 平台适配

- config.guess/config.sub 支持 OHOS 检测
- pthread_cancel 提供 stub 实现（HarmonyOS 不支持）

## 来源

- 官网：https://practical-scheme.net/gauche/
- 源码：https://github.com/shirok/Gauche