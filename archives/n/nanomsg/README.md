# nanomsg

## 简介

nanomsg是一个高性能、轻量级的消息队列库，实现了多种分布式通信模式（PAIR、REQ/REP、PUB/SUB等）。

## OHOS 适配

### 适配要点
- **CMake版本兼容性**: 系统CMake 4.1.2要求最小版本3.5，需修改`cmake_minimum_required`
- **HarmonyOS平台识别**: CMake无法识别HarmonyOS系统，需添加平台分支设置`UNIX TRUE`
- **make jobserver fifo**: SELinux限制导致并行编译失败，使用单线程编译

### 已知问题
- G0干净构建验证失败（Python subprocess平台限制）
- G4档案完整性报告错误（build_system字段）

### 补丁列表
1. `0001-CMakeLists.txt.patch`: 更新cmake版本到3.5 + 添加HarmonyOS平台识别

## 排除与替代

- 无不推荐安装的组件

## 依赖

### 编译依赖
- cmake >= 3.5

### 运行依赖
- 无运行依赖

## 功能验证

```bash
# 编译产物验证
ls ~/usr/local/lib/libnanomsg.so          # 共享库
ls ~/usr/local/bin/nanocat                # 命令行工具
pkg-config --modversion nanomsg           # pkg-config验证

# 测试套件
make check                                # 部分测试可能失败（平台差异）
```

## 参考

- 官网: https://nanomsg.org/
- 源码: https://github.com/nanomsg/nanomsg
- 协议文档: https://nanomsg.org/documentation/