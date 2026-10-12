# incus-feature-agent

Incus 的**虚拟机 agent（VM guest agent）**。在 Incus 管理的虚拟机内运行，
负责 guest 内的实例配置、设备插入、exec、文件传输、事件、metrics 等。

- 上游：https://github.com/lxc/incus
- 许可证：Apache-2.0
- 语言/构建：Go（`CGO_ENABLED=0 go install -tags agent,netgo ./cmd/incus-agent`）

## 已编译版本

- 7.2.0 (2026-10-10) — status: built

## 依赖

- Go 工具链 1.25.10（配方内自举，非 conan 依赖）
- 无第三方 C/C++ 库依赖（N=0，纯 Go）
- Go modules 由 `go mod` + GOPROXY 拉取（非 conan 依赖）

## OHOS 适配要点

1. `CGO_ENABLED=0 GOOS=linux GOARCH=arm64 -tags agent,netgo` 静态交叉编译；
   agent 组件零 cgo，不链接任何原生库。
2. 自举的 Go SDK 内全部 ELF 需 `binary-sign-tool` 自签后才能执行。
3. **E523**：`-toolexec` 包装器把链接器 `-o` 输出重定向到 `/dev/shm`，规避 HMDFS `fallocate()=EACCES`。
4. **E318**：`go test` 测试二进制需签名（在 go 最终拷贝之后）。

## 产物

```bash
incus-agent --version   # -> 7.2
```

## 说明

- 上游服务端组件（incusd/incus-user 等）需要 CGO 与 liblxc/cowsql/libudev，
  OHOS 上不可构建，不在本库范围。
- 同源先例：`archives/i/incus/7.1.0`（客户端工具集）、`archives/i/incus-user/7.0.1`。
