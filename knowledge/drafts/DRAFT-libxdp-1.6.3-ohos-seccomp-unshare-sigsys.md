# DRAFT-libxdp-1.6.3-ohos-seccomp-unshare-sigsys

**一类问题**：OHOS 的 seccomp 不放行 `unshare(CLONE_NEWNET|CLONE_NEWNS)`，任何用 `unshare -n -m`
建私有 net/mount namespace 的上游测试 runner，在第一步就被 SIGSYS 杀掉（core dump），用例一条不跑。

## 使用说明（判定 + 处置）

1. **判定**：runner 打印 `Executing tests in separate net- and mount namespaces` 后立刻
   `invalid system call (core dumped)`，且没有任何用例输出——即命中本类。
2. **取证**（忠实模式，不跳过 unshare）：
   ```sh
   sudo env PATH=$SHIMS:/data/service/hnp/bin:/usr/bin:/vendor/bin:/system/bin \\
     /data/service/hnp/bin/bash ./test_runner.sh ./test-libxdp.sh
   # → Executing tests in separate net- and mount namespaces
   # → zsh: invalid system call (core dumped)
   ```
3. **处置**：只要结果可置 `DID_UNSHARE=1` 让 runner 跳过 unshare 重执行（落宿主 netns）；
   要判"上游不可跑"，就以本 SIGSYS 为硬证据如实申报，不要写"未执行"、也不要为点亮 L1c 在 build() 里硬塞 make test。

## 适用范围

- 一切用 `unshare -n`/`-m`（或 `CLONE_NEWNET`/`CLONE_NEWNS`）做隔离的上游构建/测试脚本；
- OHOS 真机（seccomp 策略固定）；不适用 glibc 桌面 Linux（unshare 正常）。

## 输入 / 输出定义

- **输入**：一个含 `exec unshare -n -m "$0"` 的 runner + 顶层用户态（OHOS）。
- **输出**：忠实模式 → `invalid system call (core dumped)`（SIGSYS）；`DID_UNSHARE=1` → 跳过隔离、落宿主 netns 继续。

## 示例

libxdp 1.6.3 真机实测：忠实模式 10 用例一条未跑（SIGSYS）；`DID_UNSHARE=1` 后 10 条全跑，
结果 0 PASS / 8 环境阻塞 / 2 link-only（另见 DRAFT-libxdp-1.6.3-ohos-xdp-tests-unrunnable）。
