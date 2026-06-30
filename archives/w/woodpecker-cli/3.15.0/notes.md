# woodpecker-cli 3.15.0 编译笔记

## 编译环境
- 构建系统: Go
- 编译器: Go 1.26.4
- 日期: 2026-06-08
- 状态: built

## 编译步骤
1. 安装 Go 1.26.4（goenv install）
2. 批量 ELF 签名 Go 工具链
3. 设置 GOPROXY=goproxy.cn
4. 编译：make build-cli
5. 签名二进制

## 验证结果
./woodpecker-cli --version
输出: woodpecker-cli version 3.15.0

## 注意事项
- HMDFS 需要 ELF 签名
- TMPDIR=/data/storage/el2/base/cache
