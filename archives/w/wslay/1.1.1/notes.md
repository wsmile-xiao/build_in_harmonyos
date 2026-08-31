# wslay 1.1.1 适配笔记

**日期**: 2026-08-29
**目标**: HarmonyOS PC arm64 (`os=OHOS`, `arch=armv8`, clang 15)
**构建系统**: Autotools

## 源码与补丁

- 官方源码：`https://github.com/tatsuhiro-t/wslay/releases/download/release-1.1.1/wslay-1.1.1.tar.gz`
- SHA256：`90ce68c6dfd614722d44fbb14563a3f6dacc68b548b20ae382ac4f4952c55268`
- `0001-config.guess.patch`：增加 `aarch64:HarmonyOS:*:*`，输出 `aarch64-unknown-linux-ohos`。
- `0002-config.sub.patch`：接受并保留 `linux-ohos` 操作系统三元组。
- `0003-configure.patch`：将生成的 `configure` 临时目录 `umask 077` 改为 `umask 022`。

前两项对应知识条目 E007；第三项针对设备端 HMDFS 上 `confXXXXXX/subs1.awk: Permission denied` 的 E011 复现。没有在配方中加入 `--build/--host` 绕过参数。

## Conan 配方

- wslay 是纯库，不产生 `commands.json`。
- `shared` 默认开启；关闭 shared 时可选择 `fPIC`。
- CUnit 仅以 `test_requires("cunit/2.1-3")` 提供给上游 `make check`，不会成为 wslay 消费者的运行时依赖。
- `test_package` 使用 CMake 消费者配置，实际调用 `wslay_frame_send()` 和 `wslay_frame_recv()`，覆盖未掩码及掩码文本帧的编码/解码。

## 验证记录

探索源码树已在设备端完成：

```text
./configure       -> build/host/target: aarch64-unknown-linux-ohos
make -j1          -> 成功
make -j1 check    -> CUnit 36/36 tests, 278/278 assertions passed
```

正式验证使用目标 worktree 内的 profile，避免 Conan 缓存中同名旧 profile 覆盖仓库文件；以下命令显式将仓库根目录解析为绝对路径，可在任意目标 worktree 根目录复现：

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
PROFILE="$REPO_ROOT/ci/conan/profiles/ohos-aarch64"
conan create archives/w/wslay/1.1.1 \
  -pr:h="$PROFILE" \
  -pr:b="$PROFILE"
```

绝对路径由当前 worktree 动态计算，仅用于选择仓库内 profile，不写入归档元数据。

## 已知边界

`/tmp` 在设备上只读，且 HMDFS 对 Autoconf 的私有目录权限有特殊行为；构建和测试应使用任务私有、已验证可写的 `$HOME/tmp`。CUnit 是测试依赖，不会被打入 wslay 包。

finish 内置的 G0 helper 在本设备上通过 `subprocess.run(cwd=...)` 启动 HNP bash 时未同步 `PWD`，触发 `working directory cannot be determined`；这不是 wslay 配方错误。将每个验证子进程的 `PWD` 设为其实际 cwd 后，原始 tarball + 3 个补丁的 G0 configure、make 和 install 均通过。Conan W3 则按正常 CI 流程直接通过。
---

**编译结束**: 2026-08-29 13:33
**最终状态**: built
