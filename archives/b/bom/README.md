# bom

bom 是 Kubernetes SIGS 发布的软件物料清单（SBOM）命令行工具，用于生成和操作 SPDX 格式的软件清单文档。

## 功能概述

- `bom generate`：从文件、目录、Go 程序或 OCI 容器镜像生成 SPDX 2.3 SBOM 文档
- `bom document`：对已有 SPDX 文档进行输出、合并等操作
- `bom validate`：按 SPDX 文档校验产物（文件/镜像）一致性
- `bom version`：输出版本与构建信息

## OHOS 适配

- 纯 Go 实现（无 cgo），go >= 1.24.0 工具链原生编译，CGO_ENABLED=0
- go 工具链由配方供给：先按 GO、GOROOT、~/usr/local/go、PATH 顺序发现已装工具链，
  未满足时按 chkbit/caddy 先例自举固定版本 go1.25.12 SDK（golang.google.cn 优先、
  dl.google.com 兜底，URL+SHA256 固定写死）到沙箱可写工作区（OHOS_GO_WORKDIR 可覆盖，
  默认 /data/storage/el2/base/haps/entry/files/bom-conan-go），SDK 内逐 ELF 自签后使用
- go.mod 声明 `go 1.24.0`，通过 GOTOOLCHAIN=local 禁止工具链自动下载
- Go 链接器产物为未签名 ELF，HarmonyOS 拒绝执行，构建后必须用 binary-sign-tool
  自签（知识条目 E318）；go test 亦按 E318 逐包编译-签名-运行
- 构建缓存 GOCACHE/GOMODCACHE/GOTMPDIR/TMPDIR 统一置于上述工作区，避开受限路径
- tarball 构建无法注入 git tag，`bom version` 显示 GitVersion: devel 属预期

## 依赖关系

- 编译依赖：go >= 1.24.0 工具链（配方发现或自举），模块代理 goproxy.cn
- 运行依赖：无（静态自包含二进制）

## 参考资料

- 上游仓库：https://github.com/kubernetes-sigs/bom
- 文档：https://sigs.k8s.io/bom
- 许可证：Apache-2.0
