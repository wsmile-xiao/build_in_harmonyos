# lib3mf

## 简介
lib3mf 是 3MF（3D Manufacturing Format）文件标准的 C++ 参考实现，由 3MF Consortium 维护。提供 3MF 文件的读取、创建与写出能力，覆盖网格、材料、纹理、梁格子、切片等 3D 制造数据模型。

## OHOS 适配
- 构建系统: cmake（上游 3.0.2 需现代化 patch 至 3.5）
- 依赖: libzip/1.11.4、zlib/1.3.1.1（上游内置副本经 patch 替换为 conan 外部依赖）
- UUID: 上游 util-linux API，OHOS 下改为内置 /dev/urandom RFC 4122 v4 生成（ossp-uuid 1.6.2 运行时有堆破坏缺陷）
- zip 回调: patch 兼容 libzip >= 1.9 的 source callback 协议
- 产物: lib3MF.so（动态库，SONAME lib3MF.so.1）

## 适配版本
- 1.8.1（2026-09-14，published）
