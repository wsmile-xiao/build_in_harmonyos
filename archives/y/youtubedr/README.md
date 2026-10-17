# youtubedr

Youtube 视频下载器（Go 实现）。同时是一个 Go 库（`github.com/kkdai/youtube/v2`）与
命令行工具（`cmd/youtubedr`），用于从 YouTube 下载视频、获取视频/播放列表元数据、
按 itag / 清晰度过滤可下载流。

## 功能概述

- 下载单个视频（按清晰度 hd720/medium、itag 选择流）
- 获取视频与播放列表元数据（标题、作者、时长、缩略图、字幕轨）
- 多 Client 支持（Web / Android / iOS / Embedded / AndroidVR）用于规避 403
- 提供 `github.com/kkdai/youtube/v2` Go 库 API（GetVideo / GetStream / GetPlaylist）

## OHOS 适配要点

### 构建系统

纯 Go 项目，`go 1.26`，标准库 + 多个第三方 Go 模块（cobra、viper、goja、
simplejson、tablewriter、mpb 等）。

```bash
go build -trimpath -o youtubedr ./cmd/youtubedr
go test ./...
```

### 关键点

- `CGO_ENABLED=0` + `GOOS=linux` + `GOARCH=arm64` 交叉编译，产物在 OHOS/HarmonyOS
  aarch64 上直接运行
- GOPROXY 指向 `goproxy.cn`（代理 golang.org 模块下载）
- 模块依赖通过 `go mod download` 拉取（vendor 不在发行包内）
- OHOS 上的可执行文件需要 `binary-sign-tool` 签名后才能 exec；测试二进制用
  `go test -exec=<wrapper>` 先签名再运行

### 测试

官方 `make test-unit` 为 `go test -v -cover ./...`。核心库与 CLI 的单元测试中，
一部分是纯逻辑/解析测试（ID 提取、itag 表、chunk 分片、format 过滤、PEM/日期解析、
getVideoAudioFormats 等），另一部分直接访问 YouTube 网络端点（获取真实视频/播放列表/
字幕），在无外网或 YouTube 受限的沙盒里无法执行，属于环境性 gap（详见各版本
notes.md 与 test_package/MANIFEST.yml）。

## 依赖关系

### 编译依赖
- Go 1.26+ 工具链（自包含下载，不用系统 Go）

### 运行依赖
- 无（CGO_ENABLED=0 静态链接）

## 使用示例

```bash
youtubedr version
youtubedr -o "out.mp4" https://www.youtube.com/watch?v=XXXX
youtubedr -i 140 https://www.youtube.com/watch?v=XXXX
youtubedr info https://www.youtube.com/watch?v=XXXX
youtubedr list https://www.youtube.com/playlist?list=XXXX
```

## 参考资料

- 官方仓库：https://github.com/kkdai/youtube
- 官方文档：https://pkg.go.dev/github.com/kkdai/youtube/v2
- GitHub Releases：https://github.com/kkdai/youtube/releases
