# NetworkManager 上游测试入口的两个假失败源

## 场景

libnm 1.52.1 在 OHOS aarch64 上 `-Dtests=yes` 后注册 54 项 meson 测试，`conan create` 的
`build()` 内实际执行 `meson test -v -C <build_folder>`。

54 项中 14 项 FAIL。其中两类是**上游测试入口自身的缺陷**，与被适配的库无关。

---

## A. `run-nm-test.sh` 的 `die()` 把崩溃归一化成 exit status 5

### 症状

testlog 里只能看到：

```
 7/54 NetworkManager:platform/test-address-linux    FAIL  4.97s  exit status 5
```

`exit status 5` 不含任何原因信息。

### 根因

`tools/run-nm-test.sh` 用

```bash
"${NMTST_DBUS_RUN_SESSION[@]}" "$TEST" "${TEST_ARGV[@]}"
```

包住被测二进制，并注册 `die()` 处理各种失败。子进程被**信号**杀掉时（本环境是沙箱 seccomp
拒绝 `NETLINK_ROUTE` socket），脚本把它统一归一化成 exit status 5。

**真实原因只在 bash 自己打印的那一行里**：

```
run-nm-test.sh: line 286: 65339 Bad system call (core dumped) ...
```

### 怎么快速看出来

```bash
grep -n "Bad system call\|run-nm-test.sh: line" <build_folder>/meson-logs/testlog.txt
grep -E "FAIL +[0-9.]+s +exit status" <build_folder>/meson-logs/testlog.txt
```

两个命令对照就能区分：
- **exit status 5** + `Bad system call (core dumped)` → 被信号杀（沙箱/内核限制）
- **exit status 1** → 脚本自身判定失败（走的是另一条分支，如下面的 B）

libnm 本例中 10 项 exit status 5，全部是沙箱 seccomp 拒绝 `NETLINK_ROUTE`：
`platform/test-{address,cleanup,link,route,tc}-linux`、`devices/test-lldp`、`test-l3cfg`、
`src/libnm-client-impl/tests/test-{nm-client,remote-settings-client,secret-agent}`、
`test-keyfile-settings`。

---

## B. `check-exports.sh` 用裸 `nm` 做符号比对 → 21 个已导出符号被误报为缺失

### 症状

```
 3/54 NetworkManager:check-local-exports-libnm    FAIL  5.99s  exit status 1

>>linker script ".../libnm.ver" contains symbols that are not exported by library
   ".../libnm.so.0.1.0":
     1 nm_access_point_get_last_seen@libnm_1_0_6
     2 nm_device_get_metered@libnm_1_0_6
     ...
    21 nm_utils_wifi_5ghz_freqs@libnm_1_0_6
```

注意是 **exit status 1**，不是 5 —— 与 A 的形态可区分。

### 根因

`tools/check-exports.sh` 拿**裸 `nm`** 的输出，与 `libnm.ver` 里的 `#<sym>@<ver>;` 注释行做
字符串比对。

- 裸 `nm` 读的是 **`.symtab`**，**不打印 `@version` 标签**
- 带版本标签的是 **`nm -D`**（读 `.dynsym`）

于是脚本认定 21 个符号"未导出"，而实际上：

```bash
$ nm -D <pkg>/lib/libnm.so | grep "nm_utils_wifi_2ghz_freqs"
nm_utils_wifi_2ghz_freqs@@libnm_1_0_6
```

21 个全部导出，带 `@libnm_1_0_6` / `@@libnm_1_2_0` 标签。**纯误报**，无需任何配方改动。

---

## 修复 / 处置

这两项都不需要改配方，正确做法是**在配方里维护显式 allowlist**，逐项写明技术原因：

```python
ENVIRONMENT_BLOCKED_TESTS = {
    "platform/test-address-linux": "sandbox seccomp denies NETLINK_ROUTE -> Bad system call",
    "check-local-exports-libnm":   "upstream check-exports.sh compares bare `nm` (.symtab, no "
                                   "@version) against libnm.ver; `nm -D` shows all 21 exported",
    ...
}
```

并在解析 testlog 后校验：**任何不在 allowlist 内的失败 → 直接 `raise ConanException`**。
这样既不会"挂掉也不管"，也不会把误报当成真实缺陷去反向修改符号可见性。

## 关键词

`run-nm-test.sh`, `die()`, exit status 5, `Bad system call`, core dumped,
`check-exports.sh`, `libnm.ver`, linker script, not exported, `nm`, `nm -D`, `.symtab`, `.dynsym`,
`@version`

## 相关条目

- **E370** —— 上游测试结果解析/计数的同类陷阱
- **E274** —— 同属"符号/链接元数据"误判家族
