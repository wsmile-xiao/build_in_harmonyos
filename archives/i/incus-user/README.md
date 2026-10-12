# incus-user

Incus 的**用户项目守护进程**（user project daemon）。受限用户通过
`/run/incus/unix.socket.user` 代理访问系统 incusd 中的个人项目。

- 上游：https://github.com/lxc/incus
- 许可证：Apache-2.0
- 语言/构建：Go（`go build ./cmd/incus-user`）

## 已编译版本

- 7.0.1 (2026-10-10) — status: built

## 依赖

- Go 工具链 1.26.5（配方内自举，非 conan 依赖）
- 无第三方 C/C++ 库依赖（N=0）

## OHOS 适配要点

1. `CGO_ENABLED=0 GOOS=linux GOARCH=arm64` 静态交叉编译；源为 GitHub 官方归档（无 `vendor/`），build 内 `go mod download` + `-mod=mod`。
2. 自举的 Go SDK 内全部 ELF 需 `binary-sign-tool` 自签后才能执行。
3. **E523**：`-toolexec` 包装器把链接器 `-o` 输出重定向到 `/dev/shm`，规避 HMDFS `fallocate()=EACCES`。
4. **E318**：`go test` 测试二进制需签名（在 go 最终拷贝之后）。

## 产物

```bash
incus-user --version   # -> 7.0.1
```

## 说明

- 上游服务端组件（incusd / incus-agent / incus-migrate 等）需要 CGO 与
  liblxc/cowsql/libudev，OHOS 上不可构建，不在本库范围。
- 同源先例：`archives/i/incus/7.1.0`。
