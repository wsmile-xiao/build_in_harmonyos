# Draft: `DRAFT-GUEST-MUSL-NO-FD-CHK-FORTIFY-HELPER`
> Stem: `guest-musl-missing-fd-chk-fortify-helper` — pairs with the same-stem `.kv`

# 本地 guest musl 缺 `__fd_chk`：libX11/libXdmcp 在 aarch64 产物上 relocation 失败（exit=127）

## 基本信息

- **ID**: DRAFT-GUEST-MUSL-NO-FD-CHK-FORTIFY-HELPER
- **严重度**: 2（环境类，但极易被误判成配方缺陷）
- **类别**: environment | qemu | loader | libc | testing
- **触发工具**: conan | qemu | ld | clang
- **阶段**: testing
- **来源**: xcolmix 1.07 适配（2026-10-03，OHOS aarch64）
- **同源**: pitfall T017（arc4random 类），本条是**另一类符号**

## 错误特征

```
Error relocating …/libforms-1.2.4/p/lib/libforms.so.2: __fd_chk: symbol not found
Error relocating …/libx11-6.4.0/p/lib/libX11.so.6: __fd_chk: symbol not found
Error relocating …/libxdmcp-1.1.5/p/lib/libXdmcp.so.6: arc4random_buf: symbol not found
127
```

三个特征同时出现时基本可以定案：

1. **exit=127**（不是 1，也不是断言失败码）；
2. 每条错误都是 `Error relocating <某个**依赖** .so>:<符号>: symbol not found`
   —— 栈里全是依赖库，**没有一条指向被测二进制**；
3. 补上 `arc4random` shim 后仍有 `__fd_chk` 一类残留，说明不止一类符号。

## 根因

本机执行 aarch64/OHOS 产物靠 `binfmt_misc` +
`/opt/ohos-guest/lib/ld-linux-aarch64.so.1`，那份 guest libc 是 **stock musl 1.2.6**，
比 OHOS 的 musl 旧，缺两类符号：

| 符号 | 谁需要 | 真机 OHOS libc | 本地 guest libc |
|---|---|---|---|
| `arc4random` / `_buf` / `_uniform` | libXdmcp、libzip … | 有 | 无 |
| **`__fd_chk`** | libX11 1.8.10、libXdmcp、libXau、libXpm、libforms | 有 | 无 |

`__fd_chk` 的来历值得单独记一笔 —— OHOS 在 `<sys/select.h>` 里把 `FD_SET`/`FD_CLR`
改成了带边界检查的宏：

```c
void __fd_chk(int fd);
#define FD_SET(d, s) do { __fd_chk(d); ((s)->fds_bits[(d)/(8*sizeof(long))] |= (1UL<<((d)%(8*sizeof(long))))); } while(0)
#define FD_CLR(d, s) do { __fd_chk(d); ((s)->fds_bits[(d)/(8*sizeof(long))] &= ~(1UL<<((d)%(8*sizeof(long))))); } while(0)
```

任何 1990-2000 年代的 X11 / socket 代码都大量使用 `FD_SET`/`FD_CLR`，于是它们的
`.so` 带一个 `U __fd_chk`。真机 libc 导出它（SDK
`sysroot/usr/lib/aarch64-linux-ohos/libc.so` 的 `nm -D` 可见，且全部 `__*_chk`
—— `__memcpy_chk`、`__read_chk`、`__poll_chk` … —— 别名到同一个 `__chk_fail`
地址），本地 guest libc 没有 ⇒ 加载期 relocation 失败。

反向确认两条命令：

```bash
grep -n '__fd_chk' <sysroot>/usr/include/sys/select.h
nm -D --defined-only "<DevEco SDK>/native/sysroot/usr/lib/aarch64-linux-ohos/libc.so" | grep __fd_chk
```

## 处置

1. **先分层，再判内容**（与 T003 的 worker 类判据并列）：
   worker/环境类迹象 → loader 类迹象（exit=127 + 依赖库 relocation + 空输出）
   → 才轮到内容类（有具体 diff / 断言失败信息）。
2. **在容器/环境侧**补 shim 做反证，不动配方、不动代码。`__fd_chk` 语义很窄，
   照那个宏实现即可（越界即 `abort()`）：

   ```c
   #include <stdlib.h>
   #include <stdio.h>
   #include <sys/select.h>
   void __fd_chk(int fd)
   {
       if (fd < 0 || fd >= FD_SETSIZE) {
           fprintf(stderr, "__fd_chk: invalid fd %d\n", fd);
           abort();
       }
   }
   ```

   ```bash
   /opt/ohos-toolchain/clang -shared -fPIC -O2 fdchk.c -o libfdchkshim.so
   export LD_PRELOAD=/opt/ohos-guest/lib/libarc4shim.so:/root/xc-shims/libfdchkshim.so
   conan create … -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
   # => exit=127 变成 rc=1，输出符合预期
   ```

3. 宿主 x86 ld.so 会刷
   `ERROR: ld.so: object … from LD_PRELOAD cannot be preloaded … ignored.`，
   **属正常噪声**，不要当成失败。
4. **绝不能把 shim 塞进配方。** 自查：
   `grep -rn 'arc4shim\|fdchk\|LD_PRELOAD\|preload' archives/<字母>/<包>/`
   应当只命中 `notes.md` 的说明文字；命中 `conanfile.py` 就是 P1。

## 预防

1. 本地要真跑"链接了老 X11/网络栈"的 aarch64 产物时，默认本地门禁 L1 会红在
   运行期，先按上面第 1 条判别，别直接开单。
2. `/opt/ohos-guest/lib/libarc4shim.so` 只覆盖 `arc4random*`；
   用前先 `nm -D --defined-only` 确认它导出了缺的符号，`__fd_chk` 要另建。
3. 别为了"让本地门禁变绿"往配方里塞 `LD_PRELOAD`/shim/运行期补丁。
4. 依赖侧若真的与 OHOS libc 不匹配（例如某个依赖包在真机上就缺符号），
   另开 issue/PR 处理依赖包，不要在下游配方里绕过。

## 一个连带发现：框架把 stderr 并进 JSON 载荷

跑 `ohc-run.py conan-verify` 时 G4 阶段崩在
`scripts/ohc/conan_verify.py:736` 的 `json.loads`。根因在同文件 `_run()`
第 119 行：`last_out = (r.stdout or "") + (r.stderr or "")` —— stdout 与 stderr
被拼成一个字符串，而上面那些宿主预载告警恰好写在 stderr，于是 JSON 尾部多出文本
（`JSONDecodeError: Extra data`）。这是**框架侧健壮性**问题（G0/G1/G2/G3 全 PASS
说明配方本身干净），按红线不改框架脚本；报告里如实并列两方输出即可。

## 关联

- pitfall T017（arc4random 类，同一处置流程）
- `archives/x/xcolmix/1.07/notes.md` §9.1
- `archives/x/xcolmix/1.07/reports/test-report.md` §5.1、§5.3
