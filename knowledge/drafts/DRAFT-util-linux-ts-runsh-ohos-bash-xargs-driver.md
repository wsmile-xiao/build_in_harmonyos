# OHOS 用户空间 toybox xargs 不支持 GNU xargs 的 -I 替换符且 /bin/bash 路径不存在，util-linux tests/run.sh 测试驱动器必以 "xargs error" 与 "bad interpreter" 失败——需按名构建本组件 check_PROGRAMS、以 bash 显式解释测试脚本（run.sh 驱动器一行适配）、前置构建目录内 xargs→busybox shim，并用官方 harness 的 [<component>] 过滤执行

DRAFT id: DRAFT-util-linux-ts-runsh-ohos-bash-xargs-driver

## 问题

liblastlog2 2.42.2（util-linux 2.42.2 子项目）在 OHOS aarch64 上执行上游
测试时，官方测试入口存在三层与设备用户空间不兼容的驱动器问题：

1. 全量 `make check` 连带构建所有组件的 check_PROGRAMS，其中
   `lib/test_netlink.c` 编译失败：musl/OHOS sysroot 的
   `linux/socket.h` 与 `sys/socket.h` 重复定义 `struct sockaddr_storage`。
   该文件与被移植库无关，但会让 `make check` 在到达测试执行前中断。
2. `tests/run.sh` 驱动器以 `bash -c "'<script>' \"$OPTS\" || ..."` 直接
   exec 各测试脚本，内核按脚本 `#!/bin/bash` shebang 解释；OHOS 无
   `/bin/bash`，7 个脚本全部报
   `bash: <script>: /bin/bash: bad interpreter: No such file or directory`，
   汇总为 `7 tests of 7 FAILED`。
3. run.sh 用 `xargs -I '{}' -P $paraller_jobs -n 1` 分发脚本；PATH 首位的
   toybox xargs 只支持 `[-0Pprt] [-snE STR]`，不含 `-I`，报
   `xargs: Unknown option 'I'` → `xargs error`，套件根本无法分发。

## 根因

- `make check` 的构建范围（全部 check_PROGRAMS）超出聚焦包边界，属于上游
  全仓测试入口的固有语义，不是被测库的缺陷。
- 脚本 shebang 依赖 `/bin/bash` 的绝对路径，而 OHOS 把 bash 放在
  工具链 PATH（`bash` 可用、`/bin/bash` 不存在）。
- toybox xargs 与 GNU xargs 选项面不一致：`-I`（替换符）缺失；busybox
  xargs 支持 `-I`/`-P`，且 busybox 已在工具链 PATH 上。

## 方案

保持官方测试本体（脚本与断言）零改动，仅适配驱动器与调用方式：

1. 按名构建本组件的 check_PROGRAMS（如 `make test_lastlog2_dlopen ...`），
   绕开 `make check` 的全量构建语义。
2. 以官方 harness 组件过滤执行（上游 TESTS_COMPONENTS 机制，
   `tests/run.sh [options] [<component> ...]`）：
   `bash tests/run.sh --srcdir=<src> --builddir=<build> --nonroot
   --show-diff --parallel <component>`。
3. 补丁（一行）把 run.sh 分发行从 `bash -c "'<script>'"` 改为
   `bash -c "bash '<script>'"`：脚本由 bash 解释执行，shebang 行退化为
   注释，run.sh 的失败记录与汇总（`All N tests PASSED`）逻辑保持原样。
4. 构建目录内建 `xargs -> busybox` 符号链接 shim 并前置 PATH，使 run.sh
   的 `xargs -I ... -P ...` 落到 busybox 实现；shim 只存在于构建目录，
   不进入交付物。

## 自包含微探针（任意 OHOS 设备独立复跑验证机理，无需本仓）

[P1] toybox xargs 不支持 -I（run.sh 驱动器失败根因）：

```sh
printf 'a\nb\n' | xargs -I '{}' -n 1 echo '{}'; echo rc=$?
# 预期: "xargs: Unknown option 'I'" 且 rc!=0
```

[P2] busybox xargs 支持 -I/-P（shim 可行性）：

```sh
printf 'a\nb\n' | busybox xargs -I '{}' -P 2 -n 1 bash -c "echo got {}"; echo rc=$?
# 预期: 输出 got a / got b 且 rc=0
```

[P3] 无 /bin/bash 时内核按 shebang exec 失败、bash 显式解释绕过
（patch 0003 的机理）：

```sh
test ! -e /bin/bash && command -v bash >/dev/null && command -v busybox >/dev/null \
&& d=$(mktemp -d) && printf '#!/bin/bash\necho shebang-bypassed\n' > "$d/t.sh" \
&& chmod +x "$d/t.sh" && { "$d/t.sh"; echo direct_rc=$?; } 2>&1 | tail -1 \
&& bash "$d/t.sh"; echo bash_rc=$?; rm -rf "$d"
# 预期: direct_rc=126（bad interpreter）；bash 路径输出 shebang-bypassed 且 bash_rc=0
```

## 验证

- liblastlog2/2.42.2 在 ohos-aarch64 上：上游 harness 输出
  `All 7 tests PASSED`，7 个 ts 脚本逐项 `... OK`
  （dlopen / pam_lastlog2_output / remove_entry / rename_user /
  write_read_user / y2038_ll2_read_all / sqlite3_time）。
- 消费方 test_package 10 项断言全过（ll2_* 全链路），L1e 破坏性反向
  测试确认测试真实依赖被测包。

## 关联

- 本地可核实同族条目：
  - `E010`（toybox 兼容性：sed/expr 等 GNU 选项面差异，与 xargs -I 同族）；
  - `E098`（toybox 缺失命令需手动替代，与 xargs→busybox 替代同族）；
  - `E265`（OHOS 上运行上游测试的 shell/目录/工具链差异处理方法）；
  - `DRAFT-cdb-20251021-hmdfs-shebang-script-exec-refusal`（OHOS 解释器与
    `#!` 脚本调用族：shebang 语义差异的另一机理面）。
- 官方 KB HEAD 候选关联（本地 base graph 无此编号，合并时由主编终判）：
  E534（musl GNU extensions）、E467（AutotoolsDeps）。
- `DRAFT-util-linux-login-2.42.2-ohos-musl-pam-portability`：同源 tarball
  的 musl 兼容模式（`!__GLIBC__` 守卫、AutotoolsDeps 探测）。
