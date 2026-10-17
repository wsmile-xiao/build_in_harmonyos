# OHOS 上 Go 产物的签名时机与 `-toolexec` 路径约束

> **状态**: 草稿（未审核、未合入正式知识库）
> **来源事件**: incus-user 7.0.1 适配（github.com/lxc/incus tag v7.0.1，cmd/incus-user）
> **KV**: [DRAFT-incus-user-7.0.1-go-daemon-ohos-sign-link.kv](DRAFT-incus-user-7.0.1-go-daemon-ohos-sign-link.kv)

## 问题面

在 OHOS 上用 Go 工具链构建（并需要执行 `go test`）时，除 E523（链接器 fallocate EACCES）
与 E318（测试 ELF 未签名）之外，还有两个容易踩的坑：

### 坑 1：签名时机 —— go 在链接后会改写产物

- 现象：按 E523 做 `-toolexec` 包装器时，若在包装器内对链接输出**立即** `binary-sign-tool` 签名，
  得到的测试二进制**带 `.codesign` 段却无法执行**：

```text
fork/exec /…/go-build…/b001/api.test: operation not permitted   # EPERM
```

- 根因：`go` 在链接完成后仍会改写/拷贝产物（buildid 重写、`$WORK/…/a.out` → `-o` 落地）。
  包装器里的签名随即失效（`.codesign` 存在但校验不过 → 内核 EPERM）。

- 正确做法：**签名发生在 go 的最终拷贝之后**。
  - 主产物：`go build -o <exe> …` 结束后再对 `<exe>` 签名；
  - 测试：`go test -c -o <tb> ./pkg/` → 签名 `<tb>` → `cd <包目录> && ./<tb> -test.v`，
    与 `go test` 等价，且签名有效。

### 坑 2：`-toolexec` 的值不能含空格

- 现象：

```text
go: error obtaining buildID for go tool compile:
    fork/exec /storage/Users/currentUser/Desktop/lan: no such file or directory
```

- 根因：Go 把 `-toolexec` 的值**按空格切分**为命令前缀；当工作区/包装器路径含空格
  （示例中目录名 “lan work”）时，go 取首个空格前的片段去 `fork/exec`，路径被截断。

- 正确做法：包装器放在**无空格路径**（`/dev/shm/<pkg>-toolexec.sh`、`$HOME/<pkg>-toolexec.sh`）。
  配方中可对候选目录做“路径不含空格”判定后再写入。

## 方案（incus-user 7.0.1 实测）

```bash
# 1) 包装器（E523）：把 link 的 -o 输出重定向到支持 fallocate 的 /dev/shm
WRAP=/dev/shm/incus-user-toolexec.sh          # 无空格
INCUS_USER_LINK_REDIR=/dev/shm
# 2) 构建
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local GOFLAGS=-mod=mod \
GOPROXY=https://goproxy.cn,direct GOSUMDB=off \
  go build -toolexec "$WRAP" -trimpath -ldflags "-s -w" -o bin/incus-user ./cmd/incus-user
# 3) 签名（在最终拷贝之后）
binary-sign-tool sign -selfSign 1 -inFile bin/incus-user \
  -outFile bin/incus-user.signed -signAlg SHA256withECDSA && mv bin/incus-user.signed bin/incus-user
# 4) 测试：编译 → 签名 → 执行
go test -c -toolexec "$WRAP" -o pkg.test ./shared/api/
binary-sign-tool sign -selfSign 1 -inFile pkg.test -outFile pkg.test.s -signAlg SHA256withECDSA
mv pkg.test.s pkg.test && (cd shared/api && ../pkg.test -test.v)
```

## 附：无 vendor/ 的官方 git archive 源

GitHub `archive/refs/tags/vX.tar.gz` 是 git archive，**不含 `vendor/`**
（上游 linuxcontainers.org 的发布 tarball 才含）。用这种源时 `-mod=vendor` 不可用，
须 `go mod download` + `-mod=mod` + `GOPROXY`（见 KV 的 fallback）。

## 验证证据

- incus-user 7.0.1：包装器内即时签名 → `operation not permitted`；
  改为 `go test -c` + 签名 + 执行 → 151/151 PASS。
- `-toolexec` 指向含空格路径 → `fork/exec …/lan: no such file or directory`；
  移到 `/dev/shm/…` → 构建通过（产物 15,007,906 B，`--version` → 7.0.1）。

## 适用边界

- 任何在 OHOS 上以 Go 构建、且产物需 execve 的库/工具（CLI、守护进程、含 `go test` 的包）。
- 反例：纯库（不产出可执行文件、不跑测试）无需签名，但仍受 `-toolexec` 路径空格约束。

## 查重关系

- similar_to: E523（链接器 fallocate EACCES → toolexec /dev/shm）、
  E318（go test 测试 ELF 未签名）、E250（Go 工具链缺失 → 下载）、
  DRAFT-kubeadm-go-toolchain-sign（工具链自身 ELF 批量自签）
- 差异轴：本稿讲“**何时**签名才对”（go 改写产物后签名失效）与“**-toolexec 值的空格**约束”，
  前三条均未覆盖。
