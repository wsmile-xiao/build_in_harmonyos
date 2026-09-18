# E-DRAFT: OHOS/musl 不导出 glibc 遗留全局符号 sys_errlist/sys_nerr —— 1996 年代捆绑库链接失败应整体替换为 registry 预编译现代库

- **触发实例**：irpas 0.10（Phenoelit，捆绑 libpcap-0.4，1996 年版）HarmonyOS PC 适配（2026-09-16，task irpas-0.10-r01-pc4-18-20260916T121334Z）
- **错误签名**：`ld.lld: error: undefined symbol: sys_nerr / sys_errlist`（pcap.c pcap_strerror() 引用）
- **类别**：musl / ohos / link / legacy-code / bundled-library / libpcap
- **严重度**：2（链接期确定性失败，修复模式固定）

## 症状

```text
ld.lld: error: undefined symbol: sys_nerr
>>> referenced by pcap.c:181 (./pcap.c:181)
>>>               pcap.o:(pcap_strerror) in archive ./libpcap-0.4/libpcap.a
ld.lld: error: undefined symbol: sys_errlist
>>> referenced by pcap.c:182 (./pcap.c:182)
>>>               pcap.o:(pcap_strerror) in archive ./libpcap-0.4/libpcap.a
clang-15: error: linker command failed with exit code 1
```

## 根因

glibc 长期导出全局数组 `sys_errlist[]` 与整数符号 `sys_nerr`，老式 C 代码（1996 年捆绑
libpcap-0.4 的 `pcap_strerror()`）直接引用它们做错误信息映射。OHOS musl libc 不提供
这两个全局符号，链接阶段即失败。捆绑老库往往还有连锁平台问题（config.guess 1996 年版
不识别 OHOS → `can not guess host type`；C89 语法告警；`net/bpf.h` 依赖等），逐项修补
成本高且偏离上游维护轨迹。

## 决策：registry 预编译现代库整体替换（R18）

本次不修补捆绑 libpcap-0.4（也不伪造 glibc 符号 stub），而是：

1. **不构建捆绑老库**：主 Makefile `all: libpc ${PROGRAMS}` → 只构建 16 个工具目标
   （配方内 build() 显式目标列表，等价于去掉 libpc 依赖，源码树最小改动）。
2. **registry 预编译替换**：`conan install --requires=libpcap/1.10.6 --requires=libtirpc/1.3.7
   -r=ohpcd`（R18 预编译优先；libtirpc 解决 `rpc/types.h` 缺失，见 E015 系知识）。
3. **依赖注入**：generate() 注入 include/lib 路径（组件兼容：includedirs/libdirs +
   package_folder 拼接，兼容 `_Component` 无 include_paths 属性的 conan 2 API），
   R49 走 build_folder 私有 prefix；build() 用 `CFLAGS=-I… -L…` + `CLIBS="-lpcap -ltirpc"`。
4. **捆绑头文件按需保留**：`-I./libpcap-0.4` 仅提供 `net/bpf.h`（源码树头文件），不链接其库。

## 验证（真实日志）

```bash
conan create archives/i/irpas/0.10 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# G2 PASS；16 个 CLI 全部构建成功；无参运行 rc∈{0,1} 且输出 usage（hsrp 启动后阻塞由测试超时兜底）
# test_package：消费者（16 工具 + netenum 业务）+ 鸿蒙专项（uname/raw-socket/CLI 运行）全过
```

## 适用边界与反例

- 适用：OHOS/musl 构建时链接期 `undefined symbol: sys_errlist/sys_nerr`；携带 1996 年代捆绑
  第三方库（尤其 libpcap 系）的老 C 工具；registry 已有现代替代版本（R35 用 conan download
  验证二进制而非 list）。
- 反例：glibc 环境不触发，无需处理；若代码量小且依赖可静态修补（如 `sys_errlist[errno]`
  → `strerror(errno)`，参照 archives/d/dicom3tools notes 先例），且非 1996 捆绑大库，
  优先修补保留上游结构。

## 关系

- similar_to: E406（SHA256 多路径交叉验证）、E299（source 失败分层）、
  E561-draft（HTTP Content-Encoding 透明解压哈希层错位）、
  DRAFT-cronutils-1.1-raw-makefile-ohos-cli-signing（raw Makefile CLI + OHOS）
- caused_by: musl 不导出 glibc 遗留全局符号
- prerequisite_of: （无）
- conflicts_with: （无）

## 配套草稿

- `knowledge/drafts/DRAFT-irpas-0.10-musl-errlist-registry-replace.kv`（同 stem 结构化条目）