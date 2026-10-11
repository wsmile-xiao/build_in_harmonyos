# packaging/ — srs-state 1.9.5

本目录遵循 ARCHIVE-SPEC v3.0 收尾要求。

- v3.0 已废弃 tar.gz 归档上传：打包产物由 `conan create` + 制品仓（ohpcd）承载，
  此处不再放置 release/debug tar.gz（finalize 的 release/debug tar.gz 告警为全仓既有口径，非本包阻塞项）。
- 交付物清单（conan 包内容）：
  - `include/st.h` — 公共头
  - `lib/libst.a` — 静态库（默认 shared=False）
  - `lib/libst.so.1.9`（+ `libst.so.1` / `libst.so` 符号链接）— 动态库（shared=True），SONAME=libst.so.1
- 上游测试与消费者测试结果见 `reports/test-report.md`。
