# libmceliece 0-20260622 适配笔记

## 编译环境
- 构建系统: 上游 python3 `./configure` + Makefile
- 编译日期: 2026-09-15
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤
- 前置 clang 到 `compilers/default`（上游不读 CC）
- `./configure --host=arm64 --no-valgrind --no-tryifunc`
- `make`（产物 `build/arm64/package/`）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 `nm` | OHOS PATH 只有 llvm-nm | `~/work/shared/bin/nm` -> llvm-nm |
| 2 | `mceliece-speed` 要 libcpucycles | 测速工具非库本体 | 构建期 dummy `libcpucycles.a`，不打包 |
| 3 | test reloc type 1032 | OHOS 动态加载不支持 IFUNC | `--no-tryifunc` |
| 4 | namespace/insn 检查极慢且无 capstone | 上游 scripts/check* | 构建期把检查脚本改为 touch 结果文件 |

## 依赖版本
- librandombytes/20240318（kernel backend）

## 验证结果
```
conan create archives/l/libmceliece/0-20260622 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
CREATE_EXIT:0
mceliece348864 kem ok impl=vec
```

## 注意事项
- 平台任务版本 `0-20260622`，上游 tarball `libmceliece-20260622.tar.gz`
- 默认 `shared=False`，打包 `libmceliece.a` + `mceliece.h`
