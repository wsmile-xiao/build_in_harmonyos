# libtraceevent

## 简介

libtraceevent是Linux内核trace event的处理库，用于解析和处理内核跟踪事件数据，是Linux tracing系统的核心组件之一。

## OHOS 适配

**适配要点**：
- 纯Makefile项目，无configure脚本
- 需补丁解决BTF类型定义缺失和qsort_r兼容性问题
- 生成动态库+静态库+14个插件文件

**已知问题**：
- OHOS内核BTF缺少FLOAT/DECL_TAG/TYPE_TAG/ENUM64类型定义（需补丁）
- musl libc不提供qsort_r函数（需提供兼容实现）
- 测试需要CUnit框架（可跳过）

**补丁说明**：
- `0001-src-trace-btf.c.patch`：添加缺失的BTF类型定义和qsort_r兼容实现

## 依赖

**编译依赖**：无外部依赖（纯Makefile）

**可选依赖**：
- CUnit：用于测试套件（可跳过）

## 功能验证

```bash
# 库验证
pkg-config --modversion libtraceevent
# 应返回: 1.9.0

# 查看插件
ls /storage/Users/currentUser/usr/local/lib/libtraceevent/plugins/
# 应显示14个插件.so文件
```

## 产物

- **动态库**: libtraceevent.so.1.9.0 (402KB)
- **静态库**: libtraceevent.a (605KB)
- **插件**: 14个.so插件文件
- **头文件**: event-parse.h, event-utils.h, trace-seq.h, kbuffer.h
- **pkg-config**: libtraceevent.pc

## 参考

- 官方仓库: https://git.kernel.org/pub/scm/libs/libtrace/libtraceevent.git/
- Linux tracing文档: https://www.kernel.org/doc/html/latest/trace/