# alloy — Grafana Alloy (OpenTelemetry Collector 分发版)

鸿蒙 PC (OHOS aarch64) 适配归档。

- 上游: https://github.com/grafana/alloy (Apache-2.0)
- 版本: 1.17.1
- 构建: 纯 Go 静态构建（GOOS=linux GOARCH=arm64 CGO_ENABLED=0），
  主程序为 otel builder 生成的 `collector/` 模块
- 详见 `1.17.1/notes.md`
