# libcoverart

C/C++ client library for the MusicBrainz Cover Art Archive
（为应用提供 Cover Art Archive 封面图查询能力的开发库）。

## OHOS 适配

- 构建系统：CMake（`cmake_minimum_required` 抬到 3.5，去 `-Werror`，无补丁）。
- 依赖：`neon/0.34.0`（HTTP 传输）+ `jansson/2.15.1`（JSON 解析）
  + `libxml2/2.15.3.1`（仅构建时代码生成器 `make-c-interface`）。
- 默认静态库：neon 仅提供非 PIC 静态包，动态链接会在 aarch64 上失败。
- 上游离线测试 `tests/ctest` 在 build() 内真实运行并做版本字符串门禁；
  6 个在线抓取场景（`tests/cctest`）需 Cover Art Archive 公网，未纳入门禁。

## 依赖

- neon 0.34.0
- jansson 2.15.1
- libxml2 2.15.3.1

## 功能验证

```bash
conan create archives/l/libcoverart/1.0.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 参考

- 上游：https://github.com/metabrainz/libcoverart
- 文档：https://musicbrainz.org/doc/libcoverart
