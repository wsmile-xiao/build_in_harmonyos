# leaps

协作式网页结对编程编辑器（operational transform 同步服务）。

- 上游：https://github.com/Jeffail/leaps （MIT）
- 语言：纯 Go（73 个 .go，0 C/C++）
- 构建系统：Go modules（go 1.12）

## OHOS 适配要点

- 官方 Go 工具链自举（go1.25.12 linux-arm64）+ 工具链/产物全 ELF 签名（E549）
- Go linker 输出落在 el2 app-files（E331/E523，hmdfs 拒绝 PROT_EXEC mmap）
- CGO_ENABLED=0 静态构建，模块经 goproxy.cn 拉取

## 版本

- `0.9.1`：built（conan-verify 八门禁通过；上游 go test 53/53 通过）
