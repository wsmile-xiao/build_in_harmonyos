# ctop 0.7.7 适配笔记

## 编译环境
- 构建系统: custom (Go)
- 编译日期: 2026-06-17
- 编译器: go 1.22.10
- 状态: published

## 编译步骤

1. 设置Go交叉编译环境：
   ```bash
   export GOROOT=/storage/Users/currentUser/tmp/golang/go
   export GOPATH=/storage/Users/currentUser/tmp/gopath
   export GOCACHE=/data/storage/el2/base/haps/entry/files/go-build
   export GOOS=linux
   export GOARCH=arm64
   export CGO_ENABLED=0
   export TMPDIR=/data/storage/el2/base/haps/entry/temp
   export PATH=$GOROOT/bin:$PATH
   ```

2. Release编译：
   ```bash
   cd /storage/Users/currentUser/tmp/builds/ctop-0.7.7.work
   go build -ldflags "-X main.version=0.7.7 -X main.build=0.7.7" -o ctop .
   ```

3. Debug编译：
   ```bash
   go build -ldflags "-X main.version=0.7.7 -X main.build=0.7.7" -gcflags="all=-N -l" -o ctop-debug .
   ```

4. 安装到TEST_PREFIX：
   ```bash
   mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin/
   cp ctop ctop-debug $TEST_PREFIX/$DEFAULT_PREFIX/bin/
   ```

5. ELF签名：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $DEFAULT_PREFIX/bin/ctop
   python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $DEFAULT_PREFIX/bin/ctop-debug
   ```

6. 复制签名后的文件到TEST_PREFIX

7. 使用ohc-run.py package打包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-X flag requires argument of the form importpath.name=value` | ctop的version变量在main包中，需要使用`main.version`格式 | 使用`-X main.version=0.7.7`替代`-X version=0.7.7` |
| 2 | binary-sign-tool报"not trust command"错误 | 直接调用binary-sign-tool不支持，需要使用ohc-run.py sign-elf（使用`sign -selfSign 1`模式） | 使用`ohc-run.py sign-elf`命令签名 |

## 源码修改

无。ctop 0.7.7在HarmonyOS上无需任何源码修改即可编译。

## 依赖版本

- Go 1.22.10

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/ctop -v
ctop version 0.7.7, build 0.7.7 go1.22.10
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ctop-0.7.7-ohos-aarch64.tar.gz | ~30MB | Release预编译包 |
| ctop-0.7.7-ohos-aarch64-debug.tar.gz | ~10MB | Debug预编译包 |

## 注意事项

- ctop是纯Go项目，CGO_ENABLED=0编译产生静态ELF，无外部依赖
- version变量在main包，ldflag需要`main.version`格式
- ctop需要容器运行环境才能正常使用其功能（--version仅验证编译和签名正确）
