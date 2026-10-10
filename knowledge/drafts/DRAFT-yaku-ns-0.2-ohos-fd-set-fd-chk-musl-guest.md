# OHOS 的 FD_SET 依赖 `__fd_chk()`，WSL guest musl 无此符号（DRAFT 草稿）

> 状态：草稿（DRAFT，待人工审核）｜来源：yaku-ns 0.2 OHOS aarch64 适配（2026-10-03）｜severity: 2

## 问题

yaku-ns 0.2 适配完成后，本地交叉验证（`conan create -pr:h=ohos-aarch64-wsl`）
在 test_package 执行阶段全红：

```
FAIL [1/5] yaku-ns --version exits 0 and names the program
rc=127 output='Error relocating .../p/bin/yaku-ns: __fd_chk: symbol not found\n'
```

7 项 DNS 功能测试同样一条都没跑起来。乍看是「配方编出来的二进制有问题」。

## 根因：不是配方问题，是本地 guest libc 比真机旧

OHOS 的 `<sys/select.h>` 把 fd_set 操作改写成带边界检查的调用：

```c
void __fd_chk(int fd);
#define FD_SET(d, s) do { __fd_chk(d); ((s)->fds_bits[(d)/(8*sizeof(long))] |= ...); } while(0)
```

yaku-ns 的事件循环用 `select()`，因此产物带上一个未定义符号。**两端都要查**：

| 端 | libc | `__fd_chk` | 实测 |
|---|---|---|---|
| 真机 / CI worker | OHOS musl 分支 | **有** | `readelf --dyn-syms .../sysroot/usr/lib/aarch64-linux-ohos/libc.so \| grep __fd_chk` → `69: 0000000000011d80 4 FUNC GLOBAL DEFAULT 13 __fd_chk` |
| 本机 WSL guest `/opt/ohos-guest` | 通用 musl 1.2.6 | **无** | `nm -D --defined-only /opt/ohos-guest/lib/libc.so \| grep -c __fd_chk` → `0` |

于是 binfmt/qemu 在本地加载产物时直接失败并 `exit 127`；同一份二进制搬到真机
则正常运行。这是**跨宿主产物差异**。

### 判别信号

- `exit 127` + 输出只有一行 `Error relocating ...: <sym>: symbol not found`
  ⇒ **loader/符号解析类**，先别改配方；
- `exit 1` + 具体 diff / 断言信息 ⇒ 才是内容类。

## 处置

**先分层再动手**：看到该签名，先 `readelf --dyn-syms <产物>` 确认是 `U <sym>`
（未定义、由 libc 提供），再分别查真机 libc 与本地 guest libc 是否导出。
只查一端就会把环境问题误判成移植缺陷。

本例两端一比即知是宿主缺符号，**配方一行不改**。本地自证用 shim（不提交）：

```sh
cat > /tmp/fdchk.c <<'EOF'
void __fd_chk(int fd) { (void)fd; }
EOF
/opt/lpk-fixed/clang -shared -fPIC /tmp/fdchk.c -o /tmp/fdchk.so
nm -D --defined-only /tmp/fdchk.so | grep __fd_chk     # 先确认确实导出了
LD_PRELOAD=/tmp/fdchk.so <packaged-binary> --version   # → yaku-ns 0.2, rc=0
```

x86 宿主进程会刷 `ERROR: ld.so: object '/tmp/fdchk.so' ... cannot be preloaded ...
ignored.`，属正常噪声，不要被它误导成失败。

配套 shim 后，15 项断言在本地全部通过（CLI 5 + ELF 头 3 + DNS 服务 7），
与 CI 同源门禁 `G0/KC/JC/L0/L1/L2/L4/L5` 全 pass。

## 禁止的做法

1. **把 `LD_PRELOAD`/shim 塞进 `conanfile.py`**：用环境补丁伪装产品行为，
   同时踩 R33/R49 与「不许降低标准换绿」红线。
2. **往 `test_package/` 注入 shim**：消费者测试必须验证真实产物；注入后
   L1e 反向破坏测试（移走 `bin/` 重跑）就失去意义。
3. **为了让本地变绿去改 `FD_SET` 的调用方式**（例如换成 `poll()`）：那是在改
   上游软件以迁就本地环境，属于降低标准。

## 预防

- 验视含 `select()`/`FD_SET` 事件循环的 aarch64 OHOS 包时，默认本地门禁可能红在
  运行期，先按上面的三层判别，别直接开单。
- shim 只用来看「内容是不是好的」，报告里必须写清本地/CI 运行环境的这一差异，
  不把 shim 后的绿灯冒充成真机绿灯。
- 同族：T017（`arc4random`，guest musl 早于引入）、E235。

## 关联

- 本包 notes.md「本地（WSL）执行的已知环境限制」一节记录了同一现象及其红线自查。
- 同族知识条目：T017（`arc4random` 缺符号）、E235。