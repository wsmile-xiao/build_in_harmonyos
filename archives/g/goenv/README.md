# goenv — Go Version Manager

Go版本管理工具，类似于rbenv/pyenv，用于安装和管理多个Go版本。

## 基本信息

- **项目**: https://github.com/go-nv/goenv
- **版本**: 3.1.1
- **语言**: Go
- **构建系统**: Go (CGO_ENABLED=0 静态编译)
- **License**: MIT

## 鸿蒙编译要点

- Go项目，CGO_ENABLED=0静态编译，无需configure/make
- 需要设置正确的GOROOT（使用~/usr/local/go，避免旧版1.23.6工具链冲突）
- go test在鸿蒙平台无法执行（ELF签名限制），功能通过手动验证
- TMPDIR必须设为/data/storage/el2/base/cache（/tmp只读）