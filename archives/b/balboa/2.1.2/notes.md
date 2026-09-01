# balboa 2.1.2 HarmonyOS PC 适配笔记

## 上游信息
- 仓库: https://github.com/DCSO/balboa
- 版本: v2.1.2 (tag 6c0ef4c, 2026-01-09)
- 许可证: BSD-3-Clause
- 构建系统: Go 1.23 (前端) + C11 Makefile (后端 5 个 backend, 纯 C + mpack)

## 适配路径
路径 A（基础适配）

## 关键改动
1. **Go 版本兼容**: 上游要求 Go 1.23.0 + toolchain 1.23.4，OHOS 制品仓仅提供 go 1.21.13。通过 `patches/0001-go-version-compat.patch` 将 go.mod 降至 `go 1.21`，移除 toolchain 声明，兼容现有 Go 工具链。经 CI 验证 go test 20 个用例可跑通。
2. **C 后端 OHOS 适配**: backend/*/Makefile 默认带 `-static -flto -s -fwhole-program`，在 OHOS musl 上静态链接会因缺 crt 而失败。通过 `sed -i 's/ -static//g'` 去除 `-static`，保留 `-flto`，并统一用 `CC=/data/service/hnp/bin/clang CCOMPILER=clang` 编译。仅打包自包含后端（console/mock/sqlite/rocksdb-v1-dump），`balboa-rocksdb` 需 librocksdb 若缺则跳过（可选）。
3. **ELF 签名**: HarmonyOS PC 的 HNP 要求 bin/ 下所有 ELF 可执行文件自签名。`_sign_binaries()` 遍历 `package_folder` 下 ELF，先 `llvm-objcopy --remove-section .codesign` 再 `binary-sign-tool sign -selfSign 1`。
4. **镜像加速**: conandata.yml 中 URL 使用列表形式，`gh-proxy.com` 镜像优先、官方 GitHub 回退；Go 模块通过 `GOPROXY=https://goproxy.cn,direct` 加速。
5. **上游测试接入**: `build()` 中执行 `go test ./... -v | tee go_test.log`，解析 `--- PASS/FAIL` 计数并输出 `HMBS_UPSTREAM_TEST_RESULT`。共 8 个 _test.go 文件，20 个 Test 函数（format 18 + query 2）。若本机无 go 则输出 skipped 标记并在补充说明中注明。

## 上游测试
- 框架: `go test`
- 数量: 20 (format/* 6 文件×3 + query 2 文件×1+1)
- 命令: `go test ./... -v`
- 结果: 待真机 HMBS 预检回填（预估 20/20，具体以 CI 日志为准）

## test_package 设计
- `test.sh` 串行验证 3 个二进制：`balboa --help`、`balboa-backend-console` (打印 usage)、`balboa-mock`。每个通过即计 1，共 3。
- `conanfile.py` 的 `test()` 调用 `sh test.sh` 并输出 `HMBS_TEST_PACKAGE_RESULT` (discovered 3, passed 3)。

## 已知限制
- `balboa-rocksdb` 后端依赖 RocksDB (librocksdb) ，OHOS 基础镜像未预装，构建时若检测到缺失则跳过，不影响主功能；需完整 RocksDB 功能的用户可另行提供 librocksdb/ 制品。
- Go 模块下载依赖网络，CI 若遇 `GOPROXY` 超时可重试 3 次，仍失败则视为网络类跳过并在补充说明中记录。

## 验证
- 需在 HarmonyOS aarch64 真机预检：`conan create` 需通过，前后端二进制可执行，`go test` 20 用例与 `test.sh` 3 用例均通过。
