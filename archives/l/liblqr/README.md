# liblqr

## 简介

liblqr (Liquid Rescale) 是实现 seam carving 内容感知图像缩放算法的 C/C++ 库。
输入普通数组图像, 输出多尺寸表示, 支持 8-64 bit/通道、灰度/RGB/CMY 及自定义
颜色模型, 提供易用且文档完备的 API。

## OHOS 适配

- 使用 autotools 构建系统（configure + make -j1）
- 单一运行时依赖 glib-2.0（configure.ac PKG_CHECK_MODULES）
- OHOS 下固定 --build/--host=aarch64-unknown-linux-gnu（ctpl/cdecl/castget 先例，绕过 2009 年版 config.guess 对 OHOS 的识别）
- 依赖图与已合入 ctpl/0.3.5 对齐：glib/2.88.0 + zlib/1.3.1.1（override）+ tool_requires pkgconf/3.0.5
- 上游 0.4.2 不含测试套件, 由 test_package 真实调用 API 验证
- 默认静态库（liblqr-1.a）, 头文件位于 include/lqr-1, pkg-config 名 lqr-1

## 依赖

- glib/2.88.0（transitive_headers）

## 功能验证

```bash
pkg-config --modversion lqr-1
# 输出: 0.4.2
```

## 参考

- 官网: http://liblqr.wikidot.com
- 上游仓库: https://github.com/carlobaldassi/liblqr
- 下载页: http://liblqr.wikidot.com/en:download-page
