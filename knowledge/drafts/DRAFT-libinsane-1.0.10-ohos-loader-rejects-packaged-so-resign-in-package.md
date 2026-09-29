# DRAFT-libinsane-1.0.10-ohos-loader-rejects-packaged-so-resign-in-package — OHOS 加载器拒收**配方自己 install 出的 .so**（`.codesign` 在、路径与 LD_LIBRARY_PATH 全对，仍 rc=127 且 errno 为空）⇒ 生产者须在 `package()` 内重签

> 路径 B 草稿（**B判定 = create**，Issue **#3549**）。随 `libinsane/1.0.10` 的 PR 原子提交到 `knowledge/drafts/`，
> `.kv` 与 `.md` 同 stem 成对。判重按 §6.2「组合型知识不判重」，组分清单与组合后新增的解题路径见文末。

## 一句话机制

HarmonyOS 动态链接器只加载**对本机有效**的 ELF 签名。meson/autotools 装出来的 `.so` 带着链接期写入的
`.codesign` 占位段（实测 4096 B），装载器判它无效 ⇒ 在**解析 NEEDED 的第一步**就拒绝，随后连串
`Error relocating … symbol not found`，外层 conan 记 `Error 127 while executing`。

**关键辨识点：报文里 errno 位置是空的**——既不是 `Permission denied`（E517 那族），也不是
`No such file or directory`（缺库那族）。路径、权限、SONAME、`LD_LIBRARY_PATH` 十二个目录全都正确也没用。

## 症状指纹（逐字）

```
[    ] RUN: ./test_libinsane
Error loading shared library libinsane.so.1: (needed by ./test_libinsane)
Error loading shared library libinsane_gobject.so.1: (needed by ./test_libinsane)
Error relocating ./test_libinsane: lis_compare: symbol not found
… （lis_getenv / lis_free / lis_get_version / lis_api_sane / lis_strerror 同）
ERROR: libinsane/1.0.10@ohpcd/stable (test package): Error in test() method, line 40
    self.run(test_bin, env="conanrun")
    ConanException: Error 127 while executing
```

## 四臂对照（决定性证据）

| 臂 | 变量 | 结果 |
|---|---|---|
| ① | 原样 `.so`（包目录内） | rc=127 |
| ② | 只补 `LD_LIBRARY_PATH`（12 个依赖目录全给） | 仍 rc=127 |
| ③ | 平铺实体文件（排除 SONAME 软链 / HMDFS 因素） | 仍 rc=127 |
| ④ | `llvm-objcopy --remove-section .codesign F` → `binary-sign-tool sign -inFile F -outFile F -selfSign 1` → `chmod a+x F` | **rc=0，断言全过** |

②③ 排除"库找不到 / 软链 / 目录"三类假因；④ 是唯一有效的修法 ⇒ 归因到**签名有效性**。

## 解法（rec_approach = `resign-shared-libs-in-package`）

在配方 `package()` 末尾对 `package_folder/lib` 下所有 `*.so` 与 `*.so.*` 逐个「去旧签 → 自签 → 恢复执行位」：

```python
for so in sos:
    if objcopy:
        self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
    self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))
    os.chmod(so, os.stat(so).st_mode | 0o111)
```

- **工具缺失时 warning 并跳过**（交叉 SDK 环境没有 `binary-sign-tool`），不把配方判死。
- 参照实现：本仓 `archives/g/glib/2.84.0.2/conanfile.py` 的 `_sign_shared_libs()`；全仓 **1149 个配方**引用
  `binary-sign-tool`，其中 **663 枚**补丁/配方同形态。
- ⛔ **不碰 conan 缓存里他人的包**（`forbid_2`：`llvm-objcopy`/`binary-sign-tool` 作用于共享缓存 = 跨任务污染）。
- ⛔ 不用「拷一份副本再签」掩盖根因（`forbid_1`：HMDFS 对 `.so` 软链/跨目录拷贝支持不完整，症状会时好时坏）。

## fallback（次选）

`test_package` 的 `test()` 前对**拷到临时目录的副本**重签后执行 —— 只在不便改 `package()` 时用，
且仍不得写依赖缓存、不得跳过断言。

## 与既有条目的层次差（判 create 的依据）

| 条目 | 它覆盖的 | 与本条的差 |
|---|---|---|
| **E077** | `strip`/`patchelf` 改写 ELF 后 `.codesign` 失效 → 执行报 `Operation not permitted`（rc=126），四步重签 | 症状签名不同（rc=126 + EPERM vs rc=127 + **errno 为空**）；触发工具不同（strip vs install/装载器） |
| **E135** | `.so` 未签名被拒加载，`error_signature` 点名 `libintl.so.8`，`rec=sign-elf-library`（手动 `ohc-run.py sign-elf`） | 签名点名具体库、解法是**事后手动签**，不是**生产者在 `package()` 内自动签**；本条根因是"段在但无效"而非"没有段" |
| **E452** | 任务**私有目录里的副本**即使 `.codesign` 存在也会被拒（`copied shared ELF … RC 127`），`rec=force-resign-private-runtime-copies` | 作用对象是**消费侧拷贝**，且 forbid 明确禁止改缓存；本条是**生产者对自己刚 install 出的产物**签，落点在 `package()` |
| **E517** | 发布来的 `.so` 签名被消费设备拒绝，`dlopen` 报 `Permission denied` | 症状签名不同（有 errno vs errno 为空），路径不同（dlopen vs exec-time NEEDED） |

⇒ **组分**：①"段在但无效"的空 errno 签名（无条目覆盖）＋ ②"生产者在 `package()` 内自动重签"这一落点
（E077 是事后/strip 族、E135 是手动、E452 是消费侧）。**组合后新增的解题路径与适用面**＝
「凡产出 `.so` 的配方都应在 `package()` 里签一次，且判据是『唯一能修好的只有重签』而不是『库找不到』」。

## 关联

- 宿主：`libinsane/1.0.10`（任务 8230），分支 `feat/libinsane-1.0.10`，HEAD `07ddf1b7b9b067747d0591cc556e95dc13f73f18`。
- Issue：[#3549](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3549)。
- 一手读数：`reports/conan-create.log`（G2 前后两轮）、`reports/upstream-meson-test.log`、
  修复实现见该 PR 的 `conanfile.py` `_sign_shared_libs()`。
