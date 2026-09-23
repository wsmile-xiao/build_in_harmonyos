# DRAFT: 交互式终端包装脚本须从 CLI 包排除（无头 CI L2 冒烟挂起）

> 草稿条目 `DRAFT-ired-0.6-interactive-tty-wrapper-exclude-headless-l2`（.kv 配对见同目录同名 .kv）

## 问题

上游 CLI 工具集有时附带交互式终端包装脚本（例：ired 0.6 的 `vired`，vi 风格可视编辑器包装），内部执行：

```sh
stty -echo -icanon min 1
getkey() { dd if=/dev/tty count=1 bs=1; }   # 无限等待按键
while : ; do ... case "`getkey`" in ... esac; done
```

无头 CI / conan test_package / L2 smoke test 环境中 stdin=/dev/null、无 tty，脚本进入无限等待。更严重的是：

- `timeout 15 <bin> --version` 只 SIGTERM 直接子进程；
- 父 sh 死后管道子进程（`sh vired -` / `dd`）以孤儿残留并持续占用，`timeout` 无法回收；
- 整个 `build_and_test.sh` 卡死在 L2 步骤远超预算（ired 实测 >290s，无任何输出进展）。

## 根因

交互式终端脚本依赖控制终端与按键输入，且 `stty raw + dd if=/dev/tty` 组合对子进程组的信号回收不干净（`timeout` 的默认信号仅发给直接子进程）。

## 方案

打包边界决策（而非打补丁改脚本）：

1. `conanfile.py package()` 只 copy 真实 CLI ELF 工具（ired/bdiff），排除交互式终端脚本（vired），并在 notes.md/manifest.yaml 记录排除理由与适用边界；
2. `commands.json`（R38/L0k）同步只声明已交付工具，避免声明与包内容不一致；
3. `test_package` 消费者测试只验证已交付工具；
4. 判定边界：脚本含 `stty .*-echo.*-icanon`、`dd if=/dev/tty`、无 `-t` 的 `read` 且非 `--version` 早退 → 属交互终端脚本，无头 CI 下不可冒烟，应从包中排除（或按 E214 补参数早退）。

## 验证（ired 0.6）

- 排除 vired 后 W3 `build_and_test.sh` 完整通过：JC prdiff 0 junk、conan create、L1a/L1b/L5/L1e、L2 对 ired/bdiff 非阻塞警告；`.ci-result.json` exit_code=0；
- 消费者 `test_ired.py` 8 断言通过；上游 `t/test.sh` 16/16 通过。

## 适用边界 / 反例

- 适用：附带交互终端脚本的 CLI/工具包在无头 CI 的打包决策；
- 反例：不要修改上游脚本伪造 `--version` 通过；不打补丁硬塞 pty；不把 L2 挂起误报为平台阻塞；
- 与 E214（交互式 read 阻塞，方案为补丁/早退）现象同族但方案不同（打包排除）；与 DRAFT-E569（TUI 程序 /dev/tty 测试须 pty 双通道）互补：E569 讲"要测怎么办"，本条目讲"不该交付的交互包装不要放进包"。

## 关系

- `similar_to`: E214, DRAFT-E569-mdp-stdin-tty-freopen-pty-dual-channel
- `caused_by`: 无（平台交互环境差异）
- `prerequisite_of`: 无
