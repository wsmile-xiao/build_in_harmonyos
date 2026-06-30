# libomemo

## 简介
libomemo 是 OMEMO 加密库，为 XMPP 通信提供端到端加密支持。

## OHOS 适配
- cmake 构建
- 0.8.1 版本编译成功（静态库）
- Mini-XML API 兼容性问题已通过兼容层解决

## 关键问题
- **Mini-XML v4 API 不兼容**: libomemo 使用 mxml v2/v3 API，但系统安装的是 mxml4 v4.0.4
  - 解决方案: 创建 mxml4_compat.h 兼容层，提供 wrapper 函数和宏定义
- **pkg-config 包名不匹配**: libomemo 查找 "mxml.pc"，但系统只有 "mxml4.pc"
  - 解决方案: 创建 mxml.pc 兼容层指向 mxml4

## 依赖
- glib-2.0 2.88.0
- libgcrypt 1.11.0
- mxml4 4.0.4（需要兼容层）
- sqlite3 3.49.1

## 功能验证
```bash
# 检查库
ls -la $HOME/usr/local/lib/libomemo.a
# 检查头文件
ls -la $HOME/usr/local/include/libomemo.h
```

## 补丁说明
- 0001-src-libomemo.c.patch: 源码修改适配 mxml4
- 0002-src-mxml4_compat.h.patch: Mini-XML v4 API 兼容层

## 参考
- 主页: https://github.com/gkdr/libomemo
- 知识图谱草稿: E100-draft-CD64（Mini-XML v4 API 破坏性变更）