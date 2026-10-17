# algolia (algolia/cli) 1.14.0 上游测试报告

## 结论

**上游测试用例数：457**
**实测通过率：457/457 = 100%**（本地 OHOS 实测，0 FAIL，0 SKIP）
**test_package 消费测试：3/3 通过**（--version / --help / auth --help）

## 上游测试运行方式

上游测试命令：`go test ./... -p 1`（Makefile `test` 目标）。

本地 OHOS 实测命令（需 -exec 签名包装器，见下）：

```
go test -exec /data/storage/el2/base/haps/entry/files/algolia-go/sign-exec.sh -v ./... -p 1 -count=1
```

### OHOS 测试二进制签名问题（关键适配点）

go test 每次生成的测试二进制为未签名 ELF，OHOS 上直接 fork/exec 报
`permission denied`。解法：`go test -exec <sign-exec.sh>`——包装器先用
`llvm-objcopy --remove-section .codesign` 去旧签名，再用
`binary-sign-tool sign -selfSign 1` 签名，最后 `exec` 测试二进制
（与配方 `_sign_elf_if_ohos` 同款逻辑）。

### 测试范围说明

- **测试包**：91 个包 ok（`go test ./...` 全绿）；40 个包无测试文件
- **用例数**：`--- PASS` 457 个，`--- FAIL` 0 个，`--- SKIP` 0 个（含子测试）
- **e2e 排除**：`e2e/` 目录有 `//go:build e2e` 标签，默认不参与 `go test ./...`
  （需 testscript 环境 + Algolia 账号，上游 CI 亦按此处理）
- **网络**：API 客户端测试均使用 httpmock/httptest mock，无真实网络依赖

## 实测日志

完整日志：`reports/upstream-test-log.txt`（2613 行，go test -v 输出）

摘要统计：

```
$ grep -c "^--- PASS" upstream-test-log.txt
457
$ grep -c "^--- FAIL" upstream-test-log.txt
0
$ grep -c "^ok " upstream-test-log.txt
91
```

代表性输出：

```
ok  	github.com/algolia/cli/api/crawler	0.320s
ok  	github.com/algolia/cli/api/dashboard	0.444s
ok  	github.com/algolia/cli/internal/analyze	0.330s
ok  	github.com/algolia/cli/pkg/auth	0.404s
ok  	github.com/algolia/cli/pkg/cmd/apikeys/create	0.358s
...
ok  	github.com/algolia/cli/pkg/utils	0.334s
```

## test_package 消费测试

`test_package/test.sh` 3 项断言（R34 反空壳，真实执行被测包二进制）：

1. `algolia --version` → 输出 `algolia version v1.14.0`（ldflags 注入版本号）
2. `algolia --help` → 输出 `The official command-line tool to interact with Algolia`
3. `algolia auth --help` → 子命令帮助正常

本地 conan create（ohos-aarch64 profile）退出码 0，test 全 PASSED。
