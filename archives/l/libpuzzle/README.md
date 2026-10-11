# libpuzzle

## 简介

libpuzzle 是感知图像哈希库，用于快速找出视觉相似的图片（GIF/PNG/JPG），
即使图片被缩放、重压缩、改色或轻微修改过也能识别。核心是 C 库，
另带 puzzle-diff 命令行工具和 man 手册。

## OHOS 适配

- 构建系统：Autotools（configure 无 AC_CANONICAL_HOST，无需 config.guess/config.sub 补丁）
- 依赖：gd/2.3.3.1（带 JPEG 支持的注册仓变体；gd/2.3.3 无 JPEG，会使上游回归测试空转）
- 上游 `make check` 运行 3 个 regress 测试，配方在 build() 中真实执行
- 上游 regress 在夹具缺失时 exit(0) 误报通过：配方先校验夹具尺寸再信任 PASS

## 功能验证

```bash
# C 库：见 archives/l/libpuzzle/0.11/test_package/test_libpuzzle.c（6 用例）
# CLI：相似图片对比较应退出 10
puzzle-diff -e pic-a-0.jpg pic-a-1.jpg
echo $?
```

## 参考

- 上游仓库：https://github.com/jedisct1/libpuzzle
- 源码包：https://download.pureftpd.org/pub/libpuzzle/releases/libpuzzle-0.11.tar.gz
