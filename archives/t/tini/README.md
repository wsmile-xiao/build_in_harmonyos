# tini

A tiny but valid `init` process for containers.

## 功能特性

- 作为容器的 PID 1 进程运行
- 正确处理僵尸进程回收
- 支持子进程 subreaper 功能
- 轻量级，静态编译版本仅约 20KB

## 已编译版本

| 版本 | 状态 | 编译日期 | 下载 |
|------|------|---------|------|
| 0.19.0 | published | 2026-05-27 | tini-0.19.0-ohos-aarch64.tar.gz |

## 使用方法

```bash
# 基本用法
tini -- <your-program> [args]

# 示例：运行 shell
tini -- /bin/sh

# 在 Docker 中使用
ENTRYPOINT ["/usr/local/bin/tini", "--"]
CMD ["your-program"]
```

## 编译说明

- 构建系统：CMake
- 编译器：Clang
- 依赖：无外部依赖，纯 C 项目
- 补丁：需要修复 CMake 版本兼容性和函数原型声明

## 来源信息

- 上游源码：https://github.com/krallin/tini
- 许可证：MIT