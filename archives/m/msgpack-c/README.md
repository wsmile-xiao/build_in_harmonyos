# msgpack-c

## 简介

MessagePack是一个高效的二进制序列化格式，比JSON更小更快，适用于C/C++应用程序的数据交换。

## OHOS 适配

### 适配要点
- CMake构建系统，无需修改源码
- 网络下载问题：GitHub连接超时，使用git clone + 本地打包方式
- HMDFS文件系统限制：tar命令打包失败，使用Python tarfile模块

### 已知问题
- 示例程序编译警告（不影响库本身）
- 缺少cJSON依赖导致jsonconv示例无法编译（非必需功能）
- G4质量门禁报告"无二进制文件"（实际是库文件，预期行为）

## 排除与替代

- 示例程序编译警告可忽略，不影响库功能
- cJSON依赖缺失不影响核心序列化功能

## 依赖

### 编译依赖
- cmake >= 3.5

### 可选依赖
- cJSON: 用于jsonconv示例程序（非必需）

### 运行依赖
- 无运行依赖

## 功能验证

```bash
# 编译产物验证
ls ~/usr/local/lib/libmsgpack-c.so       # 共享库
ls ~/usr/local/lib/libmsgpack-c.a        # 静态库
ls ~/usr/local/include/msgpack*.h        # 头文件
pkg-config --modversion msgpack-c        # pkg-config验证

# 示例程序（可选）
cd ~/builds/msgpack-c-7.0.0.work/example
# 示例程序可能有编译警告，不影响库功能
```

## 参考

- 官网: https://msgpack.org/
- 源码: https://github.com/msgpack/msgpack-c
- API文档: https://msgpack.org/documentation/cpp.html