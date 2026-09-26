# E713 — aarch64 plain char 为 unsigned 导致 fgetc/EOF 判据失效（input stream is too big）

- **状态**：DRAFT（`knowledge/drafts/DRAFT-E713-psignifit-aarch64-fgetc-eof.kv` 配对）
- **取号**：`E713`（2026-09-24 `tools/knowledge_id.py --claim --task psignifit-2.5.6`，回查未占用）
- **实测来源**：psignifit 2.5.6 移植（任务卡 9786）W0 + 真机 aarch64 实测；Debian 同源记录 bug **#975467**、补丁 **`debian/patches/arm64.patch`**（`forwarded: no`）

## 现象

```
$ psignifit dat prefs          # aarch64，未打补丁
input stream is too big
rc=1
```

错误文案指向「输入太大」，实际输入只有几百字节 —— 真因是 **EOF 判据在 aarch64 上永不成立**，缓冲区被 0xFF 无限填充直到程序自己的 8192B 上限。

## 根因

ELF aarch64 ABI：plain `char` 是 **unsigned**（x86 是 signed）。

```c
char c;
while((c = fgetc(stream)) != EOF) { ... }   /* batchfiles.c LoadBatchFromFile */
```

`fgetc` 返回 `int`（0–255 或 `EOF=-1`）。赋给 unsigned `char` 后 `EOF` 变成 `255`，`(int)255 != -1` 恒真 → 读到文件尾后继续循环。x86 上 `char` 有符号，`(char)-1 == -1`，循环正常结束 —— 因此**只有交叉到 arm64 才暴露**。

clang 的静态信号（零误报，仅在 plain char unsigned 目标上出现）：

```
warning: result of comparison of constant -1 with expression of type 'char' is always true
         [-Wtautological-constant-out-of-range-compare]
```

## 最小复现（设备可直接执行，源文件落在任务私有目录，非 /tmp）

```sh
clang -O2 $HOME/tmp/psignifit-2.5.6/w0/repro-fgetc-eof.c \
       -o $HOME/tmp/psignifit-2.5.6/w0/repro-fgetc-eof
printf hello | $HOME/tmp/psignifit-2.5.6/w0/repro-fgetc-eof
# aarch64 实测：rc=2，"never reaches EOF after 1000001 reads (last value=255, EOF=-1)"

# 另一条纯判据（平台符号性）：
clang -O2 -o charcheck - <<'EOF'
#include <stdio.h>
int main(void){ printf("plain char is %s\n", ((char)255 < 0) ? "signed" : "unsigned");
                return ((char)255 < 0) ? 0 : 2; }
EOF
./charcheck   # aarch64 实测 rc=2 打印 unsigned
```

## 修法（推荐）

只改**读流那一处**（`LoadBatchFromFile` 内的 `char c` → `signed char c`），与 Debian `arm64.patch` 逐字等价：

```diff
--- a/psig-src/batchfiles.c
+++ b/psig-src/batchfiles.c
@@ -170,7 +170,7 @@
 	FILE * stream;
 	size_t i, bufSize, bufIncrement = 1024, maxBufSize = 8192;
-	char c;
+	signed char c;
 	BatchPtr b;
```

不要顺手改同文件里另外两处 `char c`（它们在内存缓冲上按下标遍历，不读流，改动只放大 diff）。

**禁用修法**：放大 `maxBufSize`（推迟爆发 + 吃内存）、把错误吞掉返回 rc=0（假绿）。

## 预扫描（prescan_pattern）

```
while\s*\(\s*\(\s*c\s*=\s*fgetc
```

命中后再看该文件里变量声明是否为 plain `char`，或直接编译期看 `-Wtautological-constant-out-of-range-compare`。

## 影响面

- 平台：aarch64 / armhf / riscv64 / mips 等 plain char unsigned 的目标。
- 面：**文件与 stdin 输入面**；纯内存遍历不受影响。
- 诊断陷阱：错误文案（"too big"、"invalid"）与真因无关，容易被误判为数据或平台内存问题。
