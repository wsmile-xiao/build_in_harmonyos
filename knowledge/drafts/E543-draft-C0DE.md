# E543-draft-C0DE: cek 0.2.0 的 OHOS Go 工作区、签名测试与测试分层

> 状态：Path B 知识库扩展候选，尚未提升为正式 E 条目。
> 结构化数据：与本文件同 stem 的 `E543-draft-C0DE.kv`。
> 来源：`cek` 0.2.0 适配 PR #9322，Shadow CI 任务 #43472。

## 结论先行

这不是把“Go 缺工具链”“Go linker 权限错误”“ELF 签名”和“网络超时”
分别抄成四条已有规则。`cek` 的新增价值是一个已经在 OHOS 真机上跑通的
纯 Go CLI 交付流程：

1. 在 linker 启动前规划可执行工作区，统一迁移 Go 的临时目录、缓存和链接输出；
2. 对 Go SDK 内部工具、`go test` 生成的测试 ELF 和最终 CLI 执行前签名；
3. 用 `/bin/sh` 调起签名 wrapper，保留包级测试的原始执行语义；
4. 将 hermetic smoke 与 registry-backed full 测试分层，真实记录网络限制；
5. 用 Conan `test_package` 直接消费安装包，验证交付面而不是源码目录。

因此，本草稿足以作为 B 类候选材料提交评审，但“最终是否认定为 B 类”
仍由知识库维护者根据查重、可复用性和证据质量决定。本文件不直接修改
`knowledge/graph/`、`knowledge/doc/` 或 `index.tsv`。

## 适用范围

本模式适用于以下组合条件：

- 构建目标是 HarmonyOS PC arm64，构建系统通过 Conan 驱动；
- 上游项目是需要 `go build`、`go list` 或 `go test` 的纯 Go 工具；
- 构建或测试会在目标机上执行 Go 生成的 ELF；
- 构建目录、Go cache 或临时输出可能位于 HMDFS；
- 上游测试既有不依赖网络的确定性用例，也有 OCI registry 或 daemon 用例。

它不要求普通 C/C++ 包采用 Go 的环境变量，也不把外部网络失败当成
通用源码缺陷。只有满足上述组合条件时，才应复用整套流程。

## 与既有知识的关系

本草稿明确复用并扩展以下正式条目：

| 条目 | 已覆盖内容 | `cek` 的新增组合 |
| --- | --- | --- |
| E250 | OHOS 原生环境缺失 Go 时引导固定版本 SDK | 将 SDK 下载、版本校验和 SDK ELF 签名纳入同一 Conan 配方 |
| E124 / E134 | Go linker 在 HMDFS 上的 `mapping output file failed` | 不只迁移最终输出，同时迁移 Go cache、module cache、GOTMPDIR、wrapper 和 link-out |
| E077 | OHOS ELF 的签名约束 | 把签名放到 SDK 工具、测试 ELF 和最终 CLI 的首次执行边界 |
| E318 | `go test` 生成临时测试 ELF 需要签名 | 用 `/bin/sh <wrapper>` 通过 `-exec` 启动，并按 package、`-p 1`、`-vet=off` 保留测试判定 |

因此，这条草稿不是声称 E124、E134、E077、E250 或 E318 失效，也不应
在人工提升时机械复制成五条重复条目。建议维护者将它作为“纯 Go CLI 在
OHOS 上的 Conan 交付编排和测试证据协议”进行评审。

## 问题模型

### 1. linker 输出位置必须在构建前确定

`cek` 初次在 OHOS 上构建时出现：

```text
link: mapping output file failed: permission denied
```

失败点不是最终安装目录的权限，而是 Go linker 对输出文件的 mmap 行为与
HMDFS 的文件系统策略不兼容。只设置普通的 `TMPDIR` 不能保证 Go 的
`GOTMPDIR`、`GOCACHE`、`GOMODCACHE` 和最终链接输出离开 HMDFS。

配方因此显式创建两个工作区：

- `OHOS_GO_WORKDIR`：Go SDK、module cache、build cache 等可复用内容；
- `OHOS_GO_EXEC_WORKDIR`：临时目录、测试 wrapper、签名临时文件和 `link-out`。

`GOOS=linux` 与 `GOARCH=arm64` 是 OHOS Go 工具链当前目标映射；这不是把
项目伪装成 Linux 主机，也不应通过 `--host` 或 `--build` 绕过平台检测。

### 2. 生成的测试 ELF 必须在首次加载前签名

即使 linker 已经在外部工作区成功，`go test` 仍会生成包级测试 ELF 并
立即执行。OHOS 会在进入测试代码前检查 ELF 签名；直接把 `go test -exec`
指向未签名脚本或测试程序会得到 `Permission denied`、`Operation not
permitted` 或 `Exec format error`。

`cek` 的 wrapper 在每次执行前检查签名；对未签名测试 ELF 复制到签名临时
目录，必要时移除旧签名段，再调用：

```text
binary-sign-tool sign -selfSign 1 -inFile <tmp> -outFile <tmp>.signed -signAlg SHA256withECDSA
```

替换回测试 ELF 后恢复执行位，并由系统 `/bin/sh` 调起 wrapper。这个顺序
保留了 Go 测试的 package 初始化、相对路径和测试退出码语义；仅给脚本
`chmod +x` 并不能代替对实际 ELF 签名。

### 3. 上游测试的网络依赖必须单独计量

`cek` 上游测试同时覆盖命令/view 的确定性行为和 OCI image 读取。后者会
访问 `index.docker.io`、`gcr.io` 或依赖 daemon。把默认测试改成只跑本地
用例可以降低真机阻塞，但不能把这部分覆盖宣称为通过。

配方提供两个明确模式：

- `CEK_UPSTREAM_TEST_MODE=smoke`：默认运行不访问外部 OCI registry 的确定性测试，
  作为构建门禁；
- `CEK_UPSTREAM_TEST_MODE=full`：先 `go list ./...`，再逐包运行完整上游测试，
  在网络可达时补齐 registry 覆盖。

两种模式都把 `discovered`、`executed`、`passed`、`failed`、`skipped` 和
原因写入 `upstream_test_result.json`，并随安装包进入 `res/`。这使 CI 可以
区分源码失败、平台限制和外部服务不可达。

## 推荐实施顺序

1. 从上游 `go.mod`/`go.sum` 确定 Go 最低版本。本次为 Go 1.25.7；
   缺失时下载官方 Linux arm64 SDK 并校验 SHA256。
2. 写入 Conan `Environment`，至少固定 `CGO_ENABLED=0`、`GOOS=linux`、
   `GOARCH=arm64`、`GOTOOLCHAIN=local`，并把 Go 相关工作目录指向可执行
   OHOS 路径。
3. 在 `go mod download`、`go list`、`go test` 和 `go build` 前建立目录；
   不能等到 `package()` 才搬运输出。
4. 在 OHOS 上签名 SDK 的 `go`、`gofmt` 和 `pkg/tool` ELF；构建最终 CLI
   后立即签名，再复制到 package 的 `bin/`。
5. `go test` 使用 `-p 1` 降低共享存储临时文件峰值，使用 `-vet=off` 避免
   未验证的 vet 临时产物干扰，使用 `/bin/sh <signed-wrapper>` 作为 `-exec`。
6. 先执行 smoke 并写入结果，再按网络条件显式执行 full；不得删除或重命名
   registry 测试来制造绿色结果。
7. `test_package` 运行安装后的 `bin/cek`，至少验证版本、帮助、路径参数、
   非法参数退出码和安装路径；不要只检查源码目录的 `go run`。

## 本次实证

| 验证层 | 结果 | 证据 |
| --- | --- | --- |
| Go SDK / 编译 | 通过 | 官方 Go 1.25.7 下载、SHA256 校验，OHOS ELF 签名，版本注入构建成功 |
| 默认 smoke | `26/26` 通过 | `CEK_UPSTREAM_TEST_MODE=smoke`，`failed=0`、`skipped=0` |
| 完整上游测试 | 源码清点 `N=62`；本次实际执行 `N′=31`，`17` 通过、`14` 失败 | `index.docker.io` / `gcr.io` HTTPS 请求超时，未发现编译或打包失败；未在本次输出中出现的 31 个源码测试函数作为覆盖缺口保留 |
| Conan consumer | `6/6` 通过 | 安装后执行 `test_package/test.sh`，直接调用 `bin/cek` |
| Shadow CI | 通过 | 任务 `#43472`，L0/L1/L2/L4/L5 均通过；package revision `30abbebe2dd9d56651d4fd6c8275695b` |

完整测试的 14 个失败没有被标记为 skip，也没有被合并进 smoke 的
26 个成功项；源码清点总数 `N=62` 也没有被错误改写成运行记录数
`N′=31`。这是本条目中“测试分层 + 证据保真”的关键部分。

## 禁止做法

- 只设置 `TMPDIR`，却让 Go cache 或 link output 留在 HMDFS；
- 只在 `package()` 或安装结束后签名，忽略 SDK 工具和测试 ELF 的首次执行；
- 用 `chmod 777`、执行权限或 `/bin/sh` 解释器替代 ELF 签名；
- 直接给 `go test -exec` 一个未签名脚本，或跳过 Go 生成的测试 ELF；
- 删除 OCI registry 测试、将 full 结果压成 smoke 结果，或把 timeout 写成
  “上游测试全部通过”；
- 用源码目录、占位程序或 `go run` 代替 Conan 安装包的消费者测试。

## 可复用验证命令

```sh
CI_PACKAGES="archives/c/cek/0.2.0" zsh ci/conan/build_and_test.sh

# 可达 Docker Hub / gcr.io 时补齐完整上游测试
export CEK_UPSTREAM_TEST_MODE=full
python3 scripts/ohc-run.py conan-verify cek 0.2.0
```

在没有外部 registry 的环境中，应保留默认 smoke 的成功证据和 full 的
deferred/失败原因，不应为了让门禁变绿而改变测试集合。

## 审核边界

本文件与 `.kv` 已按同 stem 配对写入 `knowledge/drafts/`，当前仅是草稿：

- 不写入 `knowledge/graph/`、`knowledge/doc/`、`index.tsv`；
- 不自动 promote，不预占正式知识条目；
- `similar_to` 已指向 E077、E124、E134、E250、E318，供维护者查重；
- 最终 B 类认定、合并已有条目或拆分为多条，交由人工审核。

## 来源文件

- `archives/c/cek/0.2.0/conanfile.py`
- `archives/c/cek/0.2.0/test_package/conanfile.py`
- `archives/c/cek/0.2.0/test_package/test.sh`
- `archives/c/cek/0.2.0/notes.md`
- `archives/c/cek/0.2.0/manifest.yaml`
- `archives/c/cek/0.2.0/reports/test-report.md`
- Shadow CI 任务 `#43472`
