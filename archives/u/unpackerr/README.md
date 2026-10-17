# unpackerr

unpackerr 是一个 Go 语言编写的下载目录自动解压守护进程：监控 Radarr、Sonarr、Lidarr、Readarr、Whisparr 等 Starr 应用与本地文件夹，自动解压（rar/zip/7z/tar 等）完成下载的内容，方便媒体库直接导入。

- 上游仓库：https://github.com/Unpackerr/unpackerr
- 许可证：MIT
- 语言：Go（CGO_ENABLED=0，纯静态）
- 适配路径：路径 A（基础适配）

## 版本

| 版本 | 状态 | 构建日期 |
|------|------|----------|
| 0.15.2 | built | 2026-08-12 |

## 用法

```bash
unpackerr --version                 # 打印版本并退出
unpackerr --help                    # 打印用法
unpackerr -c /path/to/unpackerr.conf # 以 TOML 配置文件启动守护进程
```

配置文件参考 `examples/unpackerr.conf.example`，支持环境变量前缀（默认 `UN_`）覆盖配置项。

## OHOS 适配要点

- 纯 Go 应用，无 C/C++ 目标库（任务页 C++ 标签不准确），GOPROXY 拉取模块
- Go 工具链与最终产物均需 binary-sign-tool 自签（OHOS Seccomp 拦截未签名 ELF）
- Go 缓存/链接输出/测试工作目录放在非 hmfs 工作区（E051/E166 经验）
- 上游 `go test ./...` 共 15 个用例在 OHOS 上全部通过（-exec 自签 wrapper）
