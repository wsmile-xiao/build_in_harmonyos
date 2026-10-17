# ctop 0.7.7 适配笔记

## 编译环境
- 构建系统: custom (Go)
- 编译日期: 2026-08-06
- 编译器: go (conan recipe auto-downloads Go SDK 1.24.0)
- 状态: built

## Conan 适配说明

ctop 0.7.7 之前已有手动编译记录（2026-06-17），本次为 Conan 配方适配。
conanfile.py 参照 chkbit 6.6.0 模式编写，自动处理 Go SDK 下载、ELF 签名。

## 编译步骤

1. Conan recipe 自动设置 Go 交叉编译环境：
   - CGO_ENABLED=0
   - GOOS=linux, GOARCH=arm64
   - GOPROXY/GOSUMDB 配置中国镜像
   - TMPDIR/GOCACHE/GOMODCACHE 隔离工作区

2. Release 编译（conan create 内部执行）：
   ```bash
   go build -tags release -ldflags "-s -w -X main.version=0.7.7 -X main.build=0.7.7" -o ctop .
   ```

3. ELF 签名（OHOS 平台，conan recipe 内部执行）：
   - 使用 binary-sign-tool sign -selfSign 1 签名

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-X flag requires argument of the form importpath.name=value` | ctop的version变量在main包中，需要使用`main.version`格式 | 使用`-X main.version=0.7.7`替代`-X version=0.7.7` |
| 2 | binary-sign-tool报"not trust command"错误 | 直接调用binary-sign-tool不支持，需要使用`sign -selfSign 1`模式 | conanfile.py 中使用 subprocess.check_call 调用 |

## 源码修改

无。ctop 0.7.7在HarmonyOS上无需任何源码修改即可编译。

## 依赖版本

- Go SDK 1.24.0 (conan recipe 自动下载)

## 验证结果

conan-verify 全部通过（G0-G4, L2/L4/L5）：
- G1: 配方完整性 ✅
- G2: conan create (干净构建) ✅
- G3: 系统同名库隔离 (R26) ✅
- G4: 产物完整性 ✅

本地 CI 模拟 (W3) 通过：
- setup.sh ✅
- build_and_test.sh ✅

test_package 验证：
```bash
$ ctop -v
ctop version 0.7.7, build 0.7.7 go1.24.0
```

## 注意事项

- ctop是纯Go项目，CGO_ENABLED=0编译产生静态ELF，无外部依赖
- version变量在main包，ldflag需要`main.version`格式
- ctop使用 `-tags release` 构建标签
- ctop需要容器运行环境才能正常使用其功能（-v仅验证编译和签名正确）
- conanfile.py 参照 archives/c/chkbit/6.6.0/conanfile.py 模式编写

---
**编译结束**: 2026-08-06
**最终状态**: built
