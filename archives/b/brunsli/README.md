# brunsli

> JPEG Brunsli compression codec based on Brotli

## 简介

brunsli 是 Google 开发的 JPEG 压缩编解码器，基于 Brotli 算法实现 JPEG 无损重压缩。提供 cbrunsli（编码器，JPEG→Brunsli）和 dbrunsli（解码器，Brunsli→JPEG）两个命令行工具，以及 C API 共享库和静态库。

## OHOS 适配要点

- cmake_minimum_required(VERSION 3.1) 不兼容 cmake 4.x，需添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5
- GitHub tarball 不含 git submodule 内容，需手动下载 brotli v1.0.7 到 third_party 目录
- brotli include_directories 不传播到父 CMake scope，需手动添加 include_directories
- 上游 install 配置仅安装共享库和头文件，需手动复制可执行文件和静态库

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| brotli | v1.0.7 | 压缩算法库（子模块依赖） |

## 功能验证

```bash
cbrunsli --help
dbrunsli --help
```

## 参考

- [源码仓库](https://github.com/google/brunsli)