# hcl2json 0.6.9 适配笔记

## 编译环境
- 构建系统: custom (Go project)
- 编译日期: 2026-06-18
- 编译器: go 1.26.4 linux/arm64
- 状态: built

## 编译步骤

1. 下载源码: `https://api.github.com/repos/tmccombs/hcl2json/tarball/v0.6.9`
2. 解压到构建目录
3. Go 编译: `CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -ldflags='-s -w -X main.version=0.6.9' -o hcl2json .`
4. 测试: `go test ./...` — PASS
5. Staging 安装: 将 hcl2json 复制到 `$TEST_PREFIX/$DEFAULT_PREFIX/bin/`
6. 功能验证: hcl2json 正确转换 HCL 到 JSON

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub SSL 证书问题 | 鸿蒙环境 curl SSL 验证失败 | 使用 curl -k 跳过验证，手动下载 |
| 2 | /tmp 只读 | HMDFS 限制 (E002) | 使用 $TMPDIR 替代 |
| 3 | 自动 URL 搜索失败 | nicknisi/hcl2json repo不存在 | 改为使用 tmccombs/hcl2json (正确的GitHub仓库) |
| 4 | init-build 默认 autotools | Go项目不使用autotools | 手动编译(Mode B)，manifest system改为custom |

## 源码修改

无补丁，源码不需要修改即可在鸿蒙上编译（纯Go项目，CGO_ENABLED=0 静态编译）。

## 依赖版本

- go 1.26.4 (linux/arm64)

## 验证结果

```bash
$ ./hcl2json --version
0.6.9

$ go test ./...
?   github.com/tmccombs/hcl2json           [no test files]
ok  github.com/tmccombs/hcl2json/convert    0.042s

$ ./hcl2json test.tf
{
    "resource": {
        "aws_instance": {
            "example": [
                {
                    "ami": "ami-12345678",
                    "instance_type": "t2.micro"
                }
            ]
        }
    }
}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| hcl2json-0.6.9-ohos-aarch64.tar.gz | ~4MB | 预编译包（待打包） |

## 注意事项

- 这是纯 Go 项目，使用 CGO_ENABLED=0 进行静态编译
- 源码来源是 tmccombs/hcl2json（不是 nicknisi/hcl2json，后者不存在）
- Go 项目无需 configure/make，直接 go build
---

**编译结束**: 2026-06-18 01:37
**最终状态**: built
