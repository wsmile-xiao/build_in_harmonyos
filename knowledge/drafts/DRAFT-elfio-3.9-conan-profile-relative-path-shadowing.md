# DRAFT: Conan profile 相对路径被 ~/.conan2/profiles 同名路径遮蔽（os.version 缺失）

## 问题

在 OHOS 适配任务中用**相对路径**指定 Conan profile 时（如
`-pr=ci/conan/profiles/ohos-aarch64`），Conan 可能解析命中本机
`~/.conan2/profiles/` 下的**同名嵌套路径旧副本**，而非 worktree 内的官方 profile，
导致 host profile 缺失 `os.version`，构建在启动前即被拒绝。

## 实测证据（elfio 3.9，2026-09-05）

- 触发任务: `elfio-3.9-r01-pc3-7-20260904T192711Z`
- 首错: `conan create archives/e/elfio/3.9/conanfile.py --name=elfio --version=3.9
  -pr=ci/conan/profiles/ohos-aarch64 -s build_type=Release` →
  `ERROR: There are invalid packages: elfio/3.9: Invalid: 'settings.os.version' value not defined`
- 佐证: `conan profile show -pr=ci/conan/profiles/ohos-aarch64` 显示 host profile 为
  `compiler.cppstd=gnu14`、`compiler.libcxx=libstdc++11` 且**无 os.version**，
  与 worktree 内 `ci/conan/profiles/ohos-aarch64`（os.version=6.0、libc++、cppstd=17、
  含 tools.build:compiler_executables）**内容不符**。
- 根因定位: 本机存在 `~/.conan2/profiles/ci/conan/profiles/ohos-aarch64`（旧版，无
  os.version、libstdc++11）；相对路径解析优先命中该 home 副本。settings.yml 中
  `OHOS: version: ["5.0","6.0"]` 使 os.version 为 OHOS 必填子项，缺失即抛 Invalid。

## 方案（绝对路径强制指定官方 profile）

```bash
# 用 worktree 内官方 profile 的绝对路径，host 与 build 分开显式指定
conan create archives/e/elfio/3.9/conanfile.py --name=elfio --version=3.9 \
    -pr:h=$(pwd)/ci/conan/profiles/ohos-aarch64 \
    -pr:b=$(pwd)/ci/conan/profiles/ohos-aarch64 \
    -s build_type=Release
```

- 验证: `conan profile show -pr:h=$(pwd)/ci/conan/profiles/ohos-aarch64
  -pr:b=$(pwd)/ci/conan/profiles/ohos-aarch64` 应显示 os=OHOS、os.version=6.0、
  libcxx=libc++、cppstd=17 及 compiler_executables conf。
- 结果: conan create 构建通过，test_package 双测试（test_elfio + test_harmonyos_elf）
  全部 PASS（exit=0）。

## 适用边界

- 仅当本机 `~/.conan2/profiles` 下存在与相对路径同名的嵌套副本时触发；CI 环境（无该
  遮蔽）不受影响；用绝对路径即可绕开。
- 不适用于需要依赖 detect 默认 profile 的场景（此时反而应显式选官方 OHOS profile）。

## 查重差异

- E455（libcxx 误配）: 根因是 profile **内容**误配（detect 默认 libstdc++11），修法是换
  官方 profile 内容；本候选根因是 profile **路径解析**遮蔽，修法是绝对路径显式指定，
  机制与方案均不同（similar_to）。
- 知识库检索 `settings.os.version|conan profile 相对路径|~/.conan2/profiles|遮蔽`
  无既有条目；本草稿是首个记录 Conan profile 相对路径解析遮蔽问题的条目。
