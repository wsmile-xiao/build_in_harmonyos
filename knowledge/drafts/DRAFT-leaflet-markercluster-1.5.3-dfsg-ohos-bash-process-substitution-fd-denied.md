# DRAFT — OHOS 上 bash 进程替换展开可用但读取 Permission denied：test.sh 哈希比对须走字符串比较

> 状态：草稿（来自 leaflet-markercluster 1.5.3-dfsg 真机适配，2026-09-26）

## 问题

test_package 的 sha256 完整性断言原写法：

```bash
SHAOUT=".lmc-sha-$$.out"
(cd "$D" && sha256sum f1 f2 f3 f4) | awk '{print $1}' > "$SHAOUT"
chk "installed == npm dist sha256" diff <(printf '%s\n' "$EXPECTED") "$SHAOUT"
```

- Windows Git Bash 本地：17/17 全过；
- OHOS 真机（/data/service/hnp/bin/bash）：同脚本该断言 [FAIL]（chk 吞掉
  stderr，静默失败）——其余 15 条全过，哈希本身实测与预期逐字一致。

## 复现

设备上：

- `bash -c 'echo hi <(echo there)'` → 输出 `hi /dev/fd/63`（展开正常）；
- `bash -c 'cat <(echo hi)'` → **`cat: /dev/fd/63: Permission denied`**（RC=1）。

## 根因

bash 进程替换 `<(...)` 依赖重开 `/dev/fd/N` 匿名管道描述符。OHOS 的 `/dev/fd`
仅常规描述符（0/1/2）可重开，**高编号管道 fd 的重开被沙箱/文件系统拒绝**
（Permission denied，非 ENOENT）→ diff 读不到 `/dev/fd/63` → 断言失败。

注意：operations/filesystem-analysis.md 中「/dev/stdin, /dev/fd | ✅ | 一致」
的记录与实测矛盾——该结论未覆盖进程替换产生的高编号管道 fd 场景，本条即
修正/补充该边界。

## 方案

test.sh 中改用**命令替换取哈希列 + 纯字符串比较**（不依赖 diff、不依赖
`<(...)`）：

```bash
ACTUAL=$( (cd "$D" && sha256sum f1 f2 f3 f4) 2>/dev/null | awk '{print $1}' )
if [ "$ACTUAL" = "$EXPECTED" ]; then ok; else fail + 打印 expected/actual 诊断; fi
```

- Windows GNU sha256sum 输出 `hash *file`、OHOS 输出 `hash  file`，均经
  `awk '{print $1}'` 归一为哈希列；
- 失败时打印诊断（expected/actual），避免 chk 吞 stderr 后无法定位。

## 验证

- 替换前：真机 15/16（sha256 断言 [FAIL]）；
- 替换后：真机 conan create + conan test 三轮 17/17 全绿（ohos-aarch64 与
  default 双 profile，2026-09-26）；Windows 本地回归 17/17。

## 适用边界

- 所有在 OHOS 上跑的 bash 测试脚本：任何 `<(...)`/`>(...)` 消费者（diff、
  cat、grep、awk、read 等）都会命中同一限制；
- 临时文件方案可用但须注意 cwd 可写性（hmdfs）；字符串比较最简最稳。

## 查重差异

- operations/filesystem-analysis.md：记录 /dev/fd「✅ 一致」——与实测矛盾，
  本条修正其边界（进程替换高编号管道 fd 不可重开）；
- operations/ohos-adaptation-patterns.md 2.2 节：C 代码里用 `/dev/fd` 而非
  `/proc/self/fd` 的 FD_DIR 宏建议——面向 C 程序的路径选择，与本条 bash
  进程替换的 fd 重开权限限制层次不同；
- DRAFT-8207-libgctp-automake-log-compiler-no-bin-bash：automake 测试 log
  compiler 找不到 /bin/bash 的问题，主题不同；
- DRAFT-libmysofa-1.3.5-node-crashes-on-ohos-use-equivalent-comparator：
  node V8 崩溃 → --jitless/等价比对器，与本条 bash 层限制无关。
