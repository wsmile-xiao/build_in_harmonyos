# E999: tarfile 用 r:gz 打开 .tar.xz 报 not a gzip file

## 现象

`conan create` 的 build() 内用 Python tarfile 解压下载的源码归档时报：

```
tarfile.ReadError: not a gzip file
```

随后的编译阶段连锁出现 `fatal error: 'xxx.h' file not found`（提取失败，
下游头文件缺失）。CI 日志中常见形态：先打印 "Downloaded xxx (N bytes)"，
紧接 "Failed to get ... : not a gzip file"。

## 根因

`tarfile.open(fileobj=..., mode="r:gz")` 硬编码 gzip 解压；x.org 等官方源
发布 `.tar.xz`。下载成功但解压抛异常，若异常被 except 吞掉或只 warn，
构建继续走，最终以难定位的头文件缺失形态失败。

## 处方

1. `tarfile.open(..., mode="r:*")` — 自动识别压缩格式（gz/xz/bz2）。
2. 多镜像 fallback：逐 URL try/except，全失败才 raise。
3. sha256 校验后再解压。
4. 提取后做哨兵校验（关键文件存在才算成功）。

## 证据

- PR #6361（xf86-video-r128 6.13.0）CI 连续失败根因之一，
  修复 commit 后本地 W3/CI 模拟通过。
