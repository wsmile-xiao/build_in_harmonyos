# DRAFT-libxdp-1.6.3-ohos-xdp-tests-unrunnable

**一类问题**：XDP/AF_XDP 上游测试需要"挂 bpffs + 建 veth(rtnetlink) + 加载 BPF 程序"三项内核能力；
OHOS 内核对三者均不放行，于是测试在真机上**可执行但必失败**——必须逐条如实申报，不能写 PASS。

## 使用说明（判定 + 处置）

1. **判定**：跑上游套件后日志里同时/分别出现下列三条（任一即命中对应子类）：
   ```
   Unable to mount /sys/fs/bpf                              # 内核无 bpffs，或 mount 被拒
   ip: can't talk to rtnetlink: Permission denied           # SELinux 拒 netlink，建不了 veth
   ./test_xdp_*: Operation not permitted (rc=126)           # BPF 程序执行被拒
   ```
2. **取证**：置 `DID_UNSHARE=1` 跑官方入口并把整段结果存档：
   ```sh
   sudo env DID_UNSHARE=1 PATH=$SHIMS:/data/service/hnp/bin:/usr/bin:/vendor/bin:/system/bin \\
     make -C lib/libxdp test V=1 2>&1 | tee ~/libxdp-upstream.log
   grep -E "Unable to mount /sys/fs/bpf|rtnetlink: Permission denied|Operation not permitted" ~/libxdp-upstream.log
   ```
3. **处置**：按 R51 逐条列"环境阻塞"，把"可执行子集"（纯编译+链接）与环境阻塞分开；用不依赖内核能力的
   消费者 test_package 补验证非 syscall 面，并标注"适配完整性需人工确认"。

## 与 E318 的差异

E318（HarmonyOS 上 go test 临时 ELF 未签名导致测试无法执行）只覆盖"临时 ELF 未签名 → exec 拒绝"
这一条；本条是**三条并列判据**：① 内核无 bpffs（`Unable to mount /sys/fs/bpf`）、
② SELinux 拒 netlink veth（`rtnetlink: Permission denied`）、③ BPF 程序执行 EPERM。
其中 ③ 的 `Operation not permitted` 与 E318 表象相同，但根因是 **BPF syscall/加载被拒**，而非 ELF 签名；
①② 与 E318 完全无关。故本条不合并进 E318，仅互引。

## 适用范围

- 一切在 OHOS 上跑 XDP/eBPF/AF_XDP 上游测试的库（xdp-tools/libxdp、libbpf、bpftool…）；
- **不适用**：纯用户态解析/错误路径类测试（不碰 bpffs/netlink/BPF），它们可以正常跑。

## 输入 / 输出定义

- **输入**：需要 bpffs/veth/BPF 的上游测试 + OHOS 真机（内核缺 BPF、SELinux 严）。
- **输出**：逐条原始报错（bpffs / rtnetlink / EPERM），而非笼统"未执行"；可执行子集单列。

## 示例

libxdp 1.6.3 真机实测（`DID_UNSHARE=1`）：4 条 `Unable to mount /sys/fs/bpf`；
3 条 `rtnetlink: Permission denied` + `Operation not permitted`(126)；1 条 SKIPPED（未构建）；
2 条 link-only（编译+链接）。合计 0 PASS / 8 环境阻塞 / 2 link-only。
