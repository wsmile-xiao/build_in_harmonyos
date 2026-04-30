# APR (Apache Portable Runtime)

Apache Portable Runtime (APR) 是 Apache HTTP Server 的基础库，提供了一组跨平台的 API。

## 版本信息
- 当前版本: 1.7.6
- 发布日期: 2025-01-01
- 官网: https://apr.apache.org/

## 描述
APR 的目的是创建和维护一个软件库，为底层平台特定的实现提供可预测且一致的接口。

主要功能：
- 内存管理
- 文件系统操作
- 网络通信
- 线程和进程管理
- 时间和日期处理
- 共享内存
- 锁定机制

## 编译状态
- 鸿蒙难度: 🟡 (中等)
- 构建系统: autotools
- 编译器: clang

## 依赖
- 无外部依赖

## 已知问题
- E007: config.guess 需要补丁支持 HarmonyOS
- E011: configure umask 需要修改
- E072: config.sub 需要支持 ohos-linux triplet

## 使用方式
```bash
# 链接 APR
gcc myapp.c -I/path/to/apr/include/apr-1 -L/path/to/apr/lib -lapr-1

# 使用 pkg-config
gcc myapp.c $(pkg-config --cflags --libs apr-1)
```
