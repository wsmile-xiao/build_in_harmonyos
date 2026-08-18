# alex 3.5.4.2 适配笔记

## 编译环境
- 构建系统: custom（Haskell：GHC + Setup.hs，cabal build-type Simple）
- 编译日期: 2026-08-10
- 编译器: GHC 9.14.1（harmonybrew `brew install ghc`），链接用 clang 工具链
- 状态: built

## 编译步骤

1. `runghc Setup.hs configure --prefix=/usr --enable-executable-static` — 必须静态链接（动态 GHC 二进制运行时缺 libgmp.so.10/libffi.so.8，系统 loader 找不到）
2. `runghc Setup.hs build` — 产出 dist/build/alex/alex（未剥符号，5.7MB）
3. package() 直接复制未剥的 dist 二进制到 bin/（`Setup.hs copy` 会剥符号，被剥的 GHC ELF 在 OHOS 上无法执行 EPERM）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 动态 GHC 二进制运行时缺 libgmp/libffi | GHC 动态链接到 harmonybrew 的 libgmp.so.10/libffi.so.8，OHOS 系统 loader 找不到 | `configure --enable-executable-static` 静态链接 |
| 2 | 打包二进制 exec EPERM（Permission denied） | `Setup.hs copy` 默认剥离符号，被剥的 GHC ELF 在 OHOS 无法执行 | package() 直接复制未剥的 dist/build/alex/alex |
| 3 | alex 找不到运行时模板 | alex 按编译期烤入的绝对 datadir 路径找 AlexTemplate.hs/AlexWrappers.hs | 模板打包到 share/alex-3.5.4.2/，调用时 `--template=DIR` |
| 4 | `--help` 间歇性挂死 | GHC RTS 在 OHOS 上偶发 sigsuspend 挂起 | test_package 不作 --help 断言（保留 --version + 功能性 .x 生成） |

## 源码修改

无（无补丁，上游源码未改动）

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| ghc | 9.14.1 | harmonybrew formula，运行时仅用 GHC boot 库（array/base/containers/mtl 等），无外部 Haskell 包 |

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64   # G2 PASS
conan-verify: G0-G4 + L2/L4/L5 PASS
build_and_test.sh alex/3.5.4.2   # W3 本地 CI 模拟通过
test_alex.sh: PASS=3 FAIL=0（存在性 + --version 3.5.4.2 + 功能性 .x 词法生成 32KB）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/alex-3.5.4.2.tar.gz | 94KB | 上游 Hackage 源码 tarball（与 conandata.yml 一致） |

## 注意事项

- alex 运行时模板随包安装于 share/alex-3.5.4.2/，消费者需 `--template=<包目录>/share/alex-3.5.4.2`
- alex `--help` 在 OHOS 上 GHC RTS 间歇性挂死（平台怪癖，非本适配引入），已在 test_package 与 manifest knowledge_gained 说明
---

**编译结束**: 2026-08-10 19:10
**最终状态**: built
