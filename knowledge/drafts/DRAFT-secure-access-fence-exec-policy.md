# DRAFT-secure-access-fence-exec-policy：HarmonyOS SecureAccessFence exec 政策——外来预编译 ELF 不可用，官方签名工具 selfSign 实测边界

> 草稿（DRAFT）— 来自 keycloak-archlinux 2.0.1 HarmonyOS PC (aarch64) 真机适配的真实调查。
> 与 `.kv` 同 stem 配对，字段见 knowledge/drafts/DRAFT-secure-access-fence-exec-policy.kv。
> provenance：首稿随候选 ec8f9a7d03 提交；按 Curator 字段级返工意见修订后随候选
> 1efc715948 提交（principles 改挂 P017/P019、similar_to 补 §2.3 规格族、
> fallback 拆字段、verification_cmd 自包含化）。
> 表述口径：**设备实测经验事实**，非普适定律。binary-sign-tool 对外来工具 ELF 的失败根因未定
> （esbuild ELF 布局 vs 签名工具版本 vs kubeadm CI 环境配方前提），复测前不得外推。

## 问题

在真机上运行第三方预编译 aarch64 原生二进制工具（Node.js、esbuild 等）时 exec 一律被拒；
尝试的各类"让外来二进制跑起来"的手段全部失败：

1. 外来预编译 ELF exec → `Permission denied`（rc=126），内核拒绝，与 shell 无关；
2. 手工注入 `.note.ohos.ident`（五种变体）→ 仍 EACCES；
3. 设备官方签名工具 `binary-sign-tool sign -selfSign 1`（kubeadm 同款配方）：
   - 对 OHOS 构建的对照 ELF：`add codesign section success` + `write code sign data success`，签名后可执行（探针 exit 42）；
   - 对 esbuild 官方 linux-arm64 制品：`[Error] [sign_elf.cpp] [WriteCodeSignBlock] [146] Failed to save 4K data to .codesign section` → sign failed，不产出文件；
4. 注入+签名组合、注入变体 F+签名 → 均失败；
5. npm 侧 `@esbuild/linux-arm64-musl` 不存在（404，0 个版本）。

## 机制（实测归纳）

- 设备 `const.SystemCapability.Security.SecureAccessFence = true`。
- OHOS 工具链（clang 15.0.4，`/data/service/hnp/bin/clang`）构建的任何 ELF（含 `-static`）
  自动携带 `.note.ohos.ident`（SHT_NOTE + PT_NOTE，实测载荷 28 字节：
  namesz=12 / descsz=4 / type=1 / name="OHOS"+8NUL / desc=0x00000001）与 `.ohos.randomdata`。
- 校验同时依赖 **section 名与内容**（对可运行二进制：改 shstrtab 中 section 名 → EPERM；
  清零 note 内容 → EPERM；抹掉 section 表 → 拒绝）。校验点在 exec() 内核路径
  （python `os.execv` 与 shell 均拒），静态/动态二进制同受影响。
- 外来制品类别与实测结果：

| 制品 | 链接形态 | exec 结果 |
|---|---|---|
| nodejs.org linux-arm64（glibc） | glibc 动态 | 未上设备（缺 glibc loader，理论不可行） |
| Towartz/nodejs-arm v26.8.2（android NDK） | 静态+libc++_shared，INTERP=/system/bin/linker64 | EACCES rc=126 |
| @esbuild/linux-arm64 0.21.5（Go） | 全静态 ET_EXEC | EACCES rc=126 |
| 手工注入 note（A/C/D/E/F 变体） | — | 全部 EACCES；注入+签名组合失败 |
| OHOS clang 自建（任意 ELF，含 -static） | musl | 正常（对照 exit 42） |
| binary-sign-tool selfSign → OHOS 对照物 | — | add codesign section success，可执行 |
| binary-sign-tool selfSign → esbuild 官方制品 | — | Failed to save 4K data to .codesign section，sign failed |

## 推荐方案：ohos-clang-selfbuild-or-pure-jvm

1. **优先纯 JVM/纯资源路径**：需要"现代 JS 工具链"的上游构建路径在真机不可用时，
   找上游的双构建路径（keycloak-archlinux 2.0.1 即：keycloakify/vite 路径 → gradle 经典路径）。
2. **确需原生工具时用 OHOS clang 设备自建**（产物自动合规）。node v22.14.0 自建已验证：
   `./configure --fully-static --with-intl=none`（CC/CXX 传绝对路径，musl python posix_spawn
   不解析 PATH）+ zlib CRC32 SIMD 禁用（绕 OHOS clang15 后端对 crc32b intrinsic 的崩溃）+
   `make --jobserver-style=pipe`（HMDFS 禁 mkfifo）。注意：磁盘证据止于 configure 产物与
   gyp 再生成失败（`gyp: Undefined variable python in tools/v8_gypfiles/v8.gyp` → make Error 1），
   编译从未启动；`python`→`python3` 符号链接是候选修法但未验证成功。
3. **不要注入/签名绕过**（见 forbid 表）。
4. 预取通道（unofficial-builds、Towartz/nodejs-arm、npm 平台包）在 x86 构建机可用，真机无效。

## 残差边界（如实注明）

- **签名失败根因未定**：esbuild 的 Go 静态布局无法容纳 `.codesign`、签名工具版本差异、
  kubeadm CI 环境的配方前提，三者均未被排除。该结论仅覆盖"本设备签名工具对外来工具 ELF
  的实测行为"。
- **localSign 不适用**：需要应用签名材料（HarmonyOS 应用发布链），工具类 ELF 没有该材料。
- 换签名工具版本、或对布局可容纳 `.codesign` 的外来 ELF（非 Go 全静态）可能有不同结果——
  使用前必须按 `.kv` 的 `verification_cmd` 在目标设备复测。

## 验证

- Auditor 全新 shell 实测（权威证据）：
  - `reports/curator/probe/auditor-exec-policy.txt`（probe-1/2/3/4/4b：外来 exec 拒、
    OHOS 对照 exit 42、移除 note 被拒、selfSign 双向结果）
  - `reports/curator/probe/auditor-sign-combo.txt`（probe-5 注入+签名、probe-6 变体 F+签名、
    probe-7 npm musl 包 404）
- Builder 侧互证观测（同现象）：hello-static 改名 section/清零 note/抹 section 表 → 拒绝；
  android node、esbuild 官方制品 A/C/D/E/F 五变体注入 → 全拒。

## 适用面

- 所有要在 HarmonyOS PC 真机运行第三方原生二进制工具的适配（JS 工具链、Go 工具、
  任何 glibc 预编译 aarch64 制品）。
- 与 DRAFT-12609（真机 Java/Maven 构建链四坑）、DRAFT-rjj666（node v8 musl Signal 5）互补：
  那两条讲"工具怎么跑起来"，本条讲"外来预编译工具根本跑不起来，必须自建或绕行"。
