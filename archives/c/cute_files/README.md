# cute_files - Single-file directory traversal / file utilities header

## 简介
cute_files 是 Randy Gaul 的 cute_headers 单头文件库集合中的一员，
提供一个 C 头文件 `cute_files.h`，用于跨平台目录遍历与文件系统工具函数：
递归/手动遍历目录、读取文件信息（路径/名称/扩展名/大小/类型）、
扩展名匹配、文件存在性与修改时间比较等。

## 特性
- 单文件头库，零依赖，C/C++ 均可直接包含
- 无动态内存分配，内部安全字符串拷贝，路径/名称/扩展名长度可调
- 支持 Windows / macOS / POSIX（OHOS 属 UNIX 分支）
- 定义 `CUTE_FILES_IMPLEMENTATION` 后在一个编译单元中包含即可生成实现

## OHOS 适配状态
- bootstrap 阶段（版本 1.0.0）：官方仓库/版本锚定与源码校验值已核验，
  最小归档与配方骨架已建立；尚未进入 adapt 与编译验证。

## 来源
- 官方仓库: https://github.com/RandyGaul/cute_headers（集合主页；
  cute_files.h 于 2022-11-10 移入官方归档库
  https://github.com/RandyGaul/cute_headers_deprecated）
- 1.0.0 锚定: cute_headers_deprecated 提交 3d1931aa806f111ad5bc40821afc8d299c8c554e
  （该提交头文件内部版本标识 v1.0，Copyright 2017 Randy Gaul）