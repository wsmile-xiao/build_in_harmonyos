#!/bin/sh
# test_package for spi-tools 0.8.4 — 真实行为断言（AGENTS §10.1 赛道二）。
# 以"软件使用者"身份运行打包后的 spi-config / spi-pipe：断言由退出码 + 输出
# 子串共同决定，任一断言失败即 exit 非 0（conan test 会因此失败）。
#
# 上游无任何自动化测试入口（N_static=0，判据见 MANIFEST.yml），因此本脚本承担
# 的全部是"消费者/使用者"侧的真实执行证据： getopt 校验路径、VERSION 宏（证明
# autoreconf+autoheader+configure 把 AC_INIT 版本真传进了目标码）、usage 文本、
# 以及真实 open() 系统调用路径。
#
# BINDIR 由 conanfile.py 传入（打包后的 bin 目录绝对路径）。
set -u

BIN="${BINDIR:-.}"
SPICFG="$BIN/spi-config"
SPIPIPE="$BIN/spi-pipe"

pass=0
fail=0
skip=0

ok()   { pass=$((pass+1)); printf 'ok   %s\n' "$1"; }
bad()  { fail=$((fail+1)); printf 'FAIL %s\n' "$1"; [ -n "${LAST_OUT:-}" ] && printf '     output: %s\n' "$LAST_OUT"; }

# run <cmd...> : 捕获 stdout+stderr 到 LAST_OUT，返回命令退出码
run() { LAST_OUT="$("$@" 2>&1)"; }

# expect_rc <want_rc> <desc> <cmd...>
expect_rc() { want="$1"; desc="$2"; shift 2; if run "$@"; then got=0; else got=$?; fi; if [ "$got" = "$want" ]; then ok "$desc (rc=$got)"; else bad "$desc 期望 rc=$want 实得 rc=$got"; fi; }

# expect_out <必须出现的子串> <desc> <cmd...>
expect_out() { want="$1"; desc="$2"; shift 2; run "$@" || true; case "$LAST_OUT" in
  *"$want"*) ok "$desc (含 \"$want\")";;
  *) bad "$desc 输出缺 \"$want\"";; esac; }

printf '== spi-tools 消费者测试：BINDIR=%s ==\n' "$BIN"

# --- 1. 交付物存在且可执行（真实 ELF，非空文件） ---
if [ -x "$SPICFG" ]; then ok "spi-config 存在且可执行"; else bad "spi-config 缺失或不可执行"; fi
if [ -x "$SPIPIPE" ]; then ok "spi-pipe 存在且可执行"; else bad "spi-pipe 缺失或不可执行"; fi

# --- 2. 版本宏：-v 必须回显 "spi-config - 0.8.4"（VERSION 由 configure 注入） ---
expect_rc 0 "spi-config -v 退出码 0" "$SPICFG" -v
expect_out "spi-config - 0.8.4" "spi-config -v 回显 AC_INIT 版本串" "$SPICFG" -v
expect_rc 0 "spi-pipe -v 退出码 0" "$SPIPIPE" -v
expect_out "spi-pipe - 0.8.4" "spi-pipe -v 回显 AC_INIT 版本串" "$SPIPIPE" -v

# --- 3. usage 文本（-h 走 display_usage + EXIT_SUCCESS） ---
expect_rc 0 "spi-config -h 退出码 0" "$SPICFG" -h
expect_out "use the given spi-dev character device" "spi-config -h 含 -d 选项说明" "$SPICFG" -h
expect_out "bits per word" "spi-config -h 含 -b 选项说明" "$SPICFG" -h
expect_rc 0 "spi-pipe -h 退出码 0" "$SPIPIPE" -h
expect_out "transfer block size in byte" "spi-pipe -h 含 -b 选项说明" "$SPIPIPE" -h

# --- 4. 参数校验负例：非法值必须 EXIT_FAILURE 且给专有错误 ---
expect_rc 1 "spi-config -m 9（模式越界 [0-3]）失败" "$SPICFG" -m 9
expect_out "wrong SPI mode" "spi-config 非法模式给出专有错误" "$SPICFG" -m 9
expect_rc 1 "spi-config -b 3（每字位数 <7）失败" "$SPICFG" -b 3
expect_out "wrong bits per word value" "spi-config 非法位数给出专有错误" "$SPICFG" -b 3
expect_rc 1 "spi-config -s 5（速率 <10Hz）失败" "$SPICFG" -s 5
expect_out "wrong speed value" "spi-config 非法速率给出专有错误" "$SPICFG" -s 5
expect_rc 1 "spi-config -l 7（LSB 非 0/1）失败" "$SPICFG" -l 7
expect_out "wrong LSB first value" "spi-config 非法 LSB 给出专有错误" "$SPICFG" -l 7
expect_rc 1 "spi-config 未知选项失败" "$SPICFG" -Z
expect_out "wrong option. Use -h for help." "spi-config 未知选项给出专有错误" "$SPICFG" -Z
expect_rc 1 "spi-pipe -b 0（块大小越界）失败" "$SPIPIPE" -b 0
expect_out "wrong blocksize" "spi-pipe 非法块大小给出专有错误" "$SPIPIPE" -b 0
expect_rc 1 "spi-pipe -s 5（速率越界）失败" "$SPIPIPE" -s 5
expect_out "Invalid speed" "spi-pipe 非法速率给出专有错误" "$SPIPIPE" -s 5
expect_rc 1 "spi-pipe -n -2（块数越界）失败" "$SPIPIPE" -n -2
expect_out "wrong block number" "spi-pipe 非法块数给出专有错误" "$SPIPIPE" -n -2

# --- 5. 未指定设备必须失败（device == NULL 分支） ---
expect_rc 1 "spi-config 无 -d 时失败" "$SPICFG" -q
expect_out "no device specified" "spi-config 无设备给出专有错误" "$SPICFG" -q
expect_rc 1 "spi-pipe 无 -d 时失败" "$SPIPIPE" -b 8
expect_out "no device specified" "spi-pipe 无设备给出专有错误" "$SPIPIPE" -b 8

# --- 6. 真实 open() 系统调用路径：设备节点不存在时由 perror 报出节点名 ---
GHOST=/dev/hw9-spidev-does-not-exist
expect_rc 1 "spi-config 打开不存在的 $GHOST 失败" "$SPICFG" -d "$GHOST" -q
expect_out "$GHOST" "spi-config 的 perror 回显了被打开的节点路径" "$SPICFG" -d "$GHOST" -q
expect_rc 1 "spi-pipe 打开不存在的 $GHOST 失败" "$SPIPIPE" -d "$GHOST" -b 8
expect_out "$GHOST" "spi-pipe 的 perror 回显了被打开的节点路径" "$SPIPIPE" -d "$GHOST" -b 8

# --- 7. SPI_IOC 数据面真机探测（有 spidev 节点才做；无节点如实记 SKIP，不改判通过） ---
NODE=""
for cand in /dev/spidev0.0 /dev/spidev0.1 /dev/spidev1.0 /dev/spidev1.1; do
  if [ -c "$cand" ]; then NODE="$cand"; break; fi
done
if [ -z "$NODE" ]; then
  skip=1
  printf 'SKIP 无 /dev/spidev* 字符设备节点，SPI_IOC_* 数据面用例本机不可执行（非配方缺陷）\n'
else
  expect_rc 0 "spi-config -q 在 $NODE 上成功" "$SPICFG" -d "$NODE" -q
  expect_out "mode=" "spi-config 查询回显 SPI_IOC_RD_* 读回的配置" "$SPICFG" -d "$NODE" -q
fi

printf '== 断言合计：通过 %d / 失败 %d / 条件未满足 %d ==\n' "$pass" "$fail" "$skip"
if [ "$fail" -ne 0 ]; then
  printf '消费者测试失败\n'
  exit 1
fi
if [ "$pass" -lt 30 ]; then
  printf '断言数异常偏低（%d），视为测试未真正执行\n' "$pass"
  exit 1
fi
printf '消费者测试全部通过\n'
exit 0
