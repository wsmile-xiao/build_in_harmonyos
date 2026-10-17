# aria 0.1.1 HarmonyOS PC 设备验证

## 输入一致性

- 远端 worktree: `$HOME/ws/wt-aria-0.1.1`
- 分支: `feat/aria-0.1.1`
- 验证提交: `d5e9f85b3d0f2e97ca81303a974dcb786b0a07ea`
- PR diff 基线: `refs/remotes/upstream/main...HEAD`，15 个文件且仅包含 aria 软件目录与对应知识草稿
- 设备环境: Python 3.12.8、Conan 2.29.1、clang 15.0.4、CMake 4.1.2、GNU make 4.4.1
- 任务日志目录: `$HOME/tmp/aria-0.1.1/`
- Conan 日志: `$HOME/tmp/aria-0.1.1/conan-create-force-d5e9f85b3d.log`
- CI 同源日志: `$HOME/tmp/aria-0.1.1/ci-build-and-test-prdiff-official-d5e9f85b3d.log`

远端 worktree 初始仅有继承的 `archives/l/libXext/README.md` 和
`archives/l/libXext/manifest.yaml` 无关改动；aria 归档、CI 脚本、profile 和本次
实际读取的输入均来自上述提交，未清理或覆盖无关改动。
直接使用 fork 的陈旧 `origin/main` 做增量扫描会把历史软件包误计入 JC6；更新远端
`upstream/main` 后，按 CI 脚本支持的 PR diff 模式重跑，最终门禁只读取上述 15 个文件。

## Conan 构建

执行：

```bash
conan create "$HOME/ws/wt-aria-0.1.1/archives/a/aria/0.1.1" \
  --user=ohpcd --channel=stable \
  -pr:h="$HOME/ws/wt-aria-0.1.1/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$HOME/ws/wt-aria-0.1.1/ci/conan/profiles/ohos-aarch64" \
  --build=aria/*
```

结果：退出码 0。clang 编译 `aria.c`、llvm-ar/llvm-ranlib 生成 `libaria.a`，并打包
`aria.h`、`libaria.a` 和 `LICENSE`。

## 消费者测试

`test_package` 使用 CMakeDeps/CMakeToolchain 查找 `aria::aria`，构建过程固定为
`cmake --build ... -- -j20 -j1`，最终 `-j1` 生效且没有 FIFO 权限错误；随后运行
`test_aria`，输出 `aria consumer checks passed`，退出码 0。该程序真实调用
`ar_new_state`、`ar_do_string`、算术/字符串求值、`ar_new_pair`、`ar_car` 和
`ar_cdr`，共 8 个消费者断言。

CI 同源脚本额外完成了 L1e 破坏性反向验证：临时移走包内 `lib/` 和 `include/` 后，
消费者无法继续验证，随后恢复目录，结果为 `L1e: Negative test confirmed`。

## CI 同源门禁结果

执行：

```bash
cd "$HOME/ws/wt-aria-0.1.1"
git diff --binary refs/remotes/upstream/main...HEAD > "$HOME/tmp/aria-0.1.1/pr-d5e9f85b3d-official.diff"
JUNK_PR_DIFF="$HOME/tmp/aria-0.1.1/pr-d5e9f85b3d-official.diff" \
CI_PACKAGES=archives/a/aria/0.1.1 \
CONAN_PROFILE=ohos-aarch64 \
zsh ci/conan/build_and_test.sh
```

结果：退出码 0，单包 `1/1` 通过。

| 门禁 | 结果 | 说明 |
|---|---|---|
| L0 | pass | 结构、MANIFEST、配方和依赖检查通过 |
| L1 | pass | Conan create 和消费者测试均执行 |
| L1e | pass | 破坏性反向验证确认真实依赖 aria |
| L2 | skip | 静态库包没有 `bin/`，无 `--version`/`--help` 目标 |
| L4 | pass | 无补丁，安全扫描通过 |
| L5 | pass | `lib/` 有静态库内容 |

日志中的 `Problem parsing /proc/meminfo` 和 CMake 未识别 HarmonyOS 的提示未影响
编译、链接或运行结果；没有把这些提示计作测试失败。CI 收尾将 `conandata.yml`
恢复为官方 URL，任务私有 `.build-cache/` 不属于提交输入。
