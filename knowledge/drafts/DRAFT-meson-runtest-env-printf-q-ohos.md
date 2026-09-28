# DRAFT-meson-runtest-env-printf-q-ohos: OHOS musl/meson 环境中 printf %q 缺失导致 tests 构建中断

## 触发场景

systemd 261.1 适配（2026-09-19）：对 conan 构建目录 `meson setup --reconfigure -Dtests=true`
启用上游测试后，`test-*` 目标构建前先执行生成 `systemd-runtest.env` 的 custom command，
ninja 报 `printf: bad %q@20` 失败，全部测试可执行（363 个 ninja 目标）无法继续构建。

## 症状签名

```
[1/17] Generating systemd-runtest.env with a custom command (wrapped by meson
       because command contains newlines, to capture output)
FAILED: [code=1] systemd-runtest.env
meson --internal exe --unpickle .../meson_exe_printf_*.dat
while executing ['/system/bin/printf', 'SYSTEMD_TEST_DATA=%q\n...', ...]
--- stderr ---
printf: bad %q@20
```

meson 配置时 `find_program('printf')` 在 OHOS 默认 PATH 命中 `/system/bin/printf`
（busybox/系统裁剪版，不支持 `%q` 格式符），随后多行 custom command 由 meson 包成
`meson_exe_printf_*.dat` 序列化该绝对路径，ninja 重放必然失败。

## 根因

1. OHOS 系统 `printf`（`/system/bin/printf`）为 busybox 风格，`%q` 未实现；
2. meson 对含换行的 custom command 走 `meson --internal exe` 包装，程序路径在
   configure 期已固化进 `.dat`；
3. 启用 tests 才触发（tests=false 时无 runtest.env 类生成），因此首错容易被
   误判为"OHOS 无法构建测试"。

## 复现

```
$ /system/bin/printf 'A=%q\n' "x y"; echo "rc=$?"
printf: bad %q@4
A=rc=1
$ /storage/Users/currentUser/usr/local/bin/printf 'A=%q\n' "x y"; echo "rc=$?"
A='x y' rc=0
```

## 修复（二选一）

1. **PATH 优先**：meson configure 前把 coreutils printf 所在目录置于 PATH 前端，
   使 `find_program('printf')` 命中支持 `%q` 的实现（systemd 261.1 实测有效，
   之后 361 个测试目标全部成功构建并运行）。
2. **存量目录**：已 configure 的构建目录中，改写
   `meson-private/meson_exe_printf_*.dat` 的 `cmd_args[0]` 为 coreutils printf 路径，
   或直接以 coreutils printf 手工生成目标 env 文件后 touch（ninja 视为 up-to-date）。

## 验证

- 修复后：`ninja test-hexdecoct ... test-*` 正常链接；批量构建 361 个 ELF 测试可执行，
  逐一运行并产出双口径台账（193 通过 / 40 跳过 / 127 平台限制失败 / 1 超时）。
- 本条目差异已由真实日志验证（ninja FAILED log + 替换成功后构建全量测试目标）。

## 适用边界

- 命中：OHOS + meson + tests 启用 + 含 printf-%q 多行 custom command/env 生成。
- 反例：tests=false；glibc 环境 printf（支持 %q）；不用 meson 的项目。