# marcli

marcli —— MARC (Machine Readable Cataloging) 文件的命令行解析与过滤工具（上游
`hectorcorrea/marcli`，纯 Go 实现，MIT）。支持 mrk / mrc / xml / json / solr / yaz /
count-only 多种输出格式，可按字段/子字段/内容/正则/hasFields 过滤记录，读取 10 条或百万条
MARC 记录。

## 软件级信息

| 项 | 值 |
|---|---|
| 上游 | https://github.com/hectorcorrea/marcli |
| 许可证 | MIT |
| 类型 | tool（命令行工具，R38 已声明 `commands.json`） |
| 语言/构建 | Go（`github.com/hectorcorrea/marcli`，入口 `cmd/marcli`，`CGO_ENABLED=0` 静态链接） |
| 归档版本 | `1.3.1` |

## HarmonyOS PC 适配要点

- 零 conan 第三方依赖：唯一外部 Go 模块 `github.com/google/go-cmp v0.5.9` 仅测试期使用，
  经 GOPROXY 消费，非 conan 包。
- Go 工具链（go1.25.0）由配方自举下载，**签名后必须 `chmod 755`**，否则
  `fork/exec .../pkg/tool/linux_arm64/compile: permission denied`。
- OHOS 上链接产物必须落在 ext2 类可写工作区（HMDFS 下 Go linker mmap 输出会
  `mapping output file failed: permission denied`），构建后拷回 build folder。
- 成品与测试二进制需 `binary-sign-tool` 自签名（`.codesign`），并恢复执行位。
- 上游测试以「逐包 `go test -c` → 自签名 → 从各包目录直接运行」等价复刻（OHOS 禁止自签名进程
  `execve` 另一 ELF，`go test`/`go test -exec` 均不可用）。

## 版本索引

| 版本 | 说明 |
|---|---|
| 1.3.1 | 首次适配（HarmonyOS PC / OpenHarmony aarch64）；上游用例 55/55 通过 |
