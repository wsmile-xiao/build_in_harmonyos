# wego 2.4 测试报告

## 1. 上游测试统计

| 项 | 值 |
|---|---|
| `*_test.go` 文件数 | 0 |
| `TestXxx` 函数数 | 0 |
| `BenchmarkXxx` 函数数 | 0 |
| `ExampleXxx` 函数数 | 0 |
| 上游 CI 测试命令 | `go test -v ./...` (`.github/workflows/go-build-test.yml:23`) |
| `go test -v ./...` 本地退出码 | 0 |
| `go test -v ./...` 本地输出 | 4 个包全部 `[no test files]` |
| **上游真实测试数量** | **0** |

> **说明**：wego 2.4 上游不含任何自动化测试。CI 中的 `go test -v ./...` 在无测试文件时仅做包级编译检查，
> 输出 `[no test files]` 并 exit 0。这不代表有测试通过——`[no test files]` 按规则计为 0 个测试，
> 不把包数量当测试数量，不把成功退出的空测试当通过用例。

### `go test -v ./...` 完整输出

```
?   	github.com/schachmat/wego	[no test files]
?   	github.com/schachmat/wego/backends	[no test files]
?   	github.com/schachmat/wego/frontends	[no test files]
?   	github.com/schachmat/wego/iface	[no test files]
```

## 2. test_package 消费测试

wego 是命令行程序（Go CLI application），不是 C/C++ 链接库。test_package 做真实消费测试：

| 项 | 值 |
|---|---|
| 测试脚本 | `test_package/test.sh` |
| 测试命令 | `bash test.sh <bin/wego>` |
| 被测二进制 | Conan 包中的 `bin/wego` |
| 断言总数 | 6 |

### 断言清单

| # | 断言 | 说明 |
|---|------|------|
| 1 | `wego -h` 退出码 == 0 | 主二进制可执行且 help 子命令正常 |
| 2 | stdout 含 `openweathermap` | 默认 backend 在 help 中列出 |
| 3 | stdout 含 `weatherapi` | weatherapi backend 在 help 中列出 |
| 4 | stdout 含 `ascii-art-table` | 默认 frontend 在 help 中列出 |
| 5 | stdout 含 `markdown` | markdown frontend 在 help 中列出 |
| 6 | stdout 含 `Available backends:` | help 输出包含 backend 列表标题 |

### 本地预验证结果

在探测阶段（probe_only_no_upload）已用签名后的 `wego` 二进制预验证：

```bash
$ ./wego -h
Usage of wego:
  -aat-compact        aat-frontend: Compact output
  -b BACKEND          BACKEND to be used (default "openweathermap")
  -backend BACKEND    BACKEND to be used (default "openweathermap")
  -f FRONTEND         FRONTEND to be used (default "ascii-art-table")
  -frontend FRONTEND  FRONTEND to be used (default "ascii-art-table")
  ...
Available backends: caiyunapp.com, json, openmeteo, openweathermap, smhi, weatherapi, worldweatheronline
Available frontends: ascii-art-table, emoji, json, markdown
$ echo $?
0
```

全部 6 项断言在本地预验证中满足：
- `wego -h` exit 0 ✅
- `openweathermap` present ✅
- `weatherapi` present ✅
- `ascii-art-table` present ✅
- `markdown` present ✅
- `Available backends:` present ✅

## 3. 构建验证

| 项 | 值 |
|---|---|
| 源码 SHA256 校验 | ✅ `5ae1c76a322ff2e295034a801755c42b0cb6bdef5ab205af42cf95dbf7c570f4` |
| `go mod download` | exit 0 |
| `go mod verify` | `all modules verified`，exit 0 |
| `go build` | exit 0（CGO_ENABLED=0，非 PIE，静态） |
| 产物 `file` | `ELF executable, 64-bit LSB arm64, static, stripped` |
| 产物签名 | sign-elf rc=0 |
| `wego -h` | exit 0 |
| `go vet ./...` | exit 0 |
| CGO 依赖 | 无（纯 Go，`CGO_ENABLED=0`） |

## 4. 任务平台元数据纠偏

| 项 | 平台显示 | 真实情况 |
|---|---|---|
| 语言 | C++ | **Go**（平台元数据错误） |
| 构建系统 | （未明确） | **Go modules** |

本归档按 Go modules 真实情况编写配方，不沿用任何 C/C++ 案例的构建逻辑。

## 5. 结论

- 上游真实测试数量：**0**
- 新增 test_package 测试断言数量：**6**
- 构建验证：**通过**（go build exit 0，wego -h exit 0，SHA256 校验通过）
- 无未解决问题
