# meek 0.38.0 适配笔记

## 编译环境
- 构建系统: go
- 编译日期: 2026-07-31
- 编译器: go
- 状态: built

## 编译步骤

1. 下载源码包并解压
2. 设置 Go 交叉编译环境变量：
   - `CGO_ENABLED=0`（纯 Go 静态链接，R26）
   - `GOOS=linux`（HarmonyOS 使用 Linux 内核，Go 不支持 ohos）
   - `GOARCH=arm64`（arm64 目标架构，映射 Conan arch=armv8）
3. 构建 meek-client：`go build -trimpath -ldflags "-s -w" -o meek-client ./meek-client`
4. 构建 meek-server：`go build -trimpath -ldflags "-s -w" -o meek-server ./meek-server`
5. 复制二进制到 bin/ 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 不识别 OHOS 平台 | Go 的 GOOS 不支持 "ohos" | 映射为 GOOS=linux（HarmonyOS 内核为 Linux） |
| 2 | Conan arch 与 Go arch 命名不一致 | Conan 用 armv8，Go 用 arm64 | 在配方中映射 armv8/aarch64 → arm64 |
| 3 | Go 依赖管理 | meek 使用 go.mod 管理 Go 模块依赖 | 使用 GOFLAGS=-mod=mod 允许自动下载 |

## 源码修改

无补丁。meek 源码无需修改即可在 HarmonyOS 上编译。

## 依赖版本

- Go 工具链（CI 环境提供，>= 1.21）
- Go modules（go.mod 管理，构建时自动下载）

## 验证结果

### 编译验证（2026-07-31 本地交叉编译）

构建环境：Go 1.23.4 交叉编译目标 linux/arm64

```
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
  go build -trimpath -ldflags "-s -w" -o meek-client ./meek-client
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
  go build -trimpath -ldflags "-s -w" -o meek-server ./meek-server
```

编译产物：
- meek-client: 6,684,824 bytes (6.38 MB)
- meek-server: 6,619,288 bytes (6.31 MB)

ELF 头验证（meek-client）：
- ELF magic: 7f 45 4c 46 ✓
- EI_CLASS: 2 (64-bit) ✓
- EI_DATA: 1 (Little Endian) ✓
- e_type: 0x0002 (ET_EXEC 可执行文件) ✓
- e_machine: 0x00b7 (183 = EM_AARCH64) ✓

### 上游测试用例验证（go test）

共 6 个测试文件，16 个测试函数，全部通过（16/16 = 100%）：

meek-client (9/9 PASS):
- TestMakeProxySpec PASS
- TestAddrForDial PASS
- TestProxyHTTPCONNECT PASS
- TestProxyHTTPProxyAuthorization PASS
- TestProxyHTTPSCONNECT PASS
- TestNewUTLSRoundTripperCase PASS
- TestUTLSClientHello PASS
- TestUTLSServerName PASS
- TestUTLSHTTPWithProxy PASS

meek-server (6/6 PASS):
- TestNewCertContext PASS
- TestDelete PASS
- TestReplace PASS
- TestOriginalClientIPRemoteAddr PASS
- TestOriginalClientXForwardedFor PASS
- TestOriginalClientPrecedence PASS

meek-client-torbrowser (1/1 PASS):
- TestGrepHelperAddr PASS

### 二进制运行验证（预期 ENV-ERROR）

meek-client/meek-server 无环境变量运行时输出 ENV-ERROR no TOR_PT_MANAGED_TRANSPORT_VER 并退出码 1（由 test_package/test.sh 在 HarmonyOS CI 环境验证）。

## 源码 vendoring 说明

CI Worker 无法访问 gitlab.torproject.org（meek 官方源），且 CI 自动镜像 fallback 不覆盖该域名，也无权威 GitHub/GitCode 镜像。因此将官方 v0.38.0 源码包以 `prebuilt.tar.gz` 名义随配方提交（项目 `.gitignore` 对 `prebuilt.tar.gz` 设有例外，参见 md5deep/libtar 先例），由 conanfile.py 的 `exports_sources` + `source()` 本地解压，不再联网下载。

- conandata.yml 的 `url` 仍记录官方 gitlab 地址，用于来源追溯（R39）。
- `sha256`（5b7341...）为 vendored 副本的哈希；该副本由 git clone 重新打包，字节流与官方 GitLab archive tarball 不同，但内容为同一 meek v0.38.0 源码。

## 注意事项

- meek 是 Go 项目，依赖通过 go.mod 管理，非 Conan 依赖
- `go build` 用 `GOPROXY=https://goproxy.cn,direct`（conanfile.py build() 内 setdefault）：CI Worker 不可达默认的 proxy.golang.org，goproxy.cn 可达且含 goptlib 等全部依赖
- CGO_ENABLED=0 确保纯静态链接，无 C 库依赖
- 交叉编译时需正确设置 GOOS/GOARCH（R33）
- test_package 包含 cross_building 检查，x86_64 CI 跳过二进制执行
