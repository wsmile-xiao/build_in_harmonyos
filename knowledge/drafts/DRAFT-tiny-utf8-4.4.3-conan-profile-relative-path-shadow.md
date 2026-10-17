# DRAFT — conan 相对路径 profile 被同名缓存 profile 遮蔽 → settings.os.version 未定义；须用绝对路径

基于 tiny-utf8 4.4.3 R01 真实证据（`conan create -pr:h=ci/conan/profiles/ohos-aarch64` 直接失败）

## 问题描述

直接调用 conan（绕过 ohc-run.py 包装）时，用**相对路径**指定 profile：

```bash
conan create archives/t/tiny-utf8/4.4.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

报错：

```
ERROR: There are invalid packages:
tiny-utf8/4.4.3@ohpcd/stable: Invalid: 'settings.os.version' value not defined
```

而同一个仓库文件 `ci/conan/profiles/ohos-aarch64` 内容正确包含 `os=OHOS / os.version=6.0 /
compiler=clang 15 / compiler.libcxx=libc++ / compiler.cppstd=17`。

## 根因

conan 解析 `-pr:h=ci/conan/profiles/ohos-aarch64` 时，**优先命中 conan 缓存中同名 profile**
（历史任务曾把 `ci/conan/profiles/ohos-aarch64` 存进 cache：`conan profile list` 显示
`ci/conan/profiles/ohos-aarch64 / ohos-aarch64 / pangomm-cxx17` 等），而不是仓库文件。
缓存版 profile 内容与仓库文件不一致（展示为 `compiler.cppstd=gnu14 / compiler.libcxx=libstdc++11`
且**无 os.version**），因此 conan 校验 settings 时报 `settings.os.version value not defined`。
相对路径不保证解析到文件，缓存优先 → 间歇性"环境相关"差异（干净缓存机器正常、残留缓存机器必现）。

## 解决方案

**profile 一律用绝对路径**，确保命中仓库文件：

```bash
PROFILE="$(pwd)/ci/conan/profiles/ohos-aarch64"
conan create archives/t/tiny-utf8/4.4.3 \
  -pr:h="$PROFILE" -pr:b="$PROFILE" --build=missing --user=ohpcd --channel=stable
```

修复后 conan create RC=0，test_package 2/2 测试通过。

## 验证

- 绝对路径后输入 profile 正确显示 `os=OHOS / os.version=6.0 / compiler.cppstd=17 / compiler.libcxx=libc++`
- tiny-utf8 实测：conan create RC=0，CTest 2/2（test_tiny-utf8 + test_tiny-utf8-ohos）通过
- 日志 SHA-256: 2124827c4374bdce48d94808871b9f3c32d1d331e6f608216bbb7ba23f774eb3

## 适用边界 / 反例

- 适用：本地直接调 conan（含脚本/CI 内嵌）且机器 conan 缓存曾出现同名 profile 的场景
- 反例：缓存无同名 profile 时相对路径可正常工作（所以只在特定环境复现）；
  用 ohc-run.py 包装命令时它内部转绝对路径，一般不受影响
- 注意：这不是仓库文件本身的问题（文件内容正确），是 profile 解析优先级问题

## 查重差异

四范围（knowledge/graph/index.tsv、doc/、graph/、drafts/）检索
"缓存 profile / profile 遮蔽 / relative profile / settings.os.version" 均无命中，
判定为新增知识。

*由 tiny-utf8 4.4.3 R01 生成（2026-09-05），知识候选台账见 .oh-executor/tiny-utf8-r01-knowledge-ledger.log*