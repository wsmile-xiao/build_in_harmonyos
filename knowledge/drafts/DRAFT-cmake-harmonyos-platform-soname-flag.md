# CMAKE_SYSTEM_NAME=HarmonyOS 无平台模块导致共享库缺 DT_SONAME，应在链接期显式定义 SONAME flag

- 形态：knowledge/drafts 条目草稿（最终编号 Exxx 由知识库主编确认）
- 配套 kv：`knowledge/drafts/DRAFT-cmake-harmonyos-platform-soname-flag.kv`
- 申报路径：B【知识库扩展】（L1 平台/构建系统语义层，单库发现即可申报）
- 来源 run：accessibility-26.04.3（qaccessibilityclient/0.6.0 + accessibility-inspector/26.04.3，双包权威 CI PASS；2026-09-08 起后者包名重构为 accessibility/26.04.3——L0n/L0m 门禁，上游产品不变）

## 1. 一句规则

以 `CMAKE_SYSTEM_NAME=HarmonyOS` 配置的 CMake 工程因平台模块缺失而拿不到
`CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG`，所有共享库都不带 `DT_SONAME`、
消费者把链接路径原样写进 `DT_NEEDED`；应在链接期显式注入
`CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname,"`，而不是逐消费者修补
或发布路径形产物。

## 2. 机理链（每环有独立可复现证据）

1. **系统名注入**：Conan OHOS profile 将 `os=OHOS` 映射为
   `CMAKE_SYSTEM_NAME=HarmonyOS` 写入 CMakeToolchain。
2. **平台模块缺失**：CMake 按 `Modules/Platform/<SYSTEM_NAME>.cmake` 查找；
   设备上 hnp cmake 4.1.2 与 SDK cmake 3.28 均无 `Platform/HarmonyOS.cmake`
   （`ls` → No such file or directory）。存在 `Platform/OHOS.cmake`，但其全文
   仅 `include(Platform/Linux)`，且系统名为 HarmonyOS 时不生效。
3. **flag 未定义**：`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,"` 定义在
   `Platform/Linux.cmake`（`grep -n SONAME` 可见），该链路断裂后 CMake 不向
   链接器传 `-Wl,-soname`，也不生成版本化文件名。
4. **症状**：lld 对无 `DT_SONAME` 的输入库，把 `IMPORTED_LOCATION`（conan-cache
   绝对路径）或构建树相对路径（`../../bin/...`）原样写入消费者 `DT_NEEDED`；
   产物离开构建环境即 `Error loading shared library`。这正是 E537 记录的
   症状面；本条把根因落到了平台模块缺失。
5. **工具链本身支持**：`clang --target=aarch64-linux-ohos -shared ... -Wl,-soname,libt.so.1`
   产出 `(SONAME) libt.so.1`（llvm-readelf 实证）——缺口只在 CMake 变量层。

## 3. 推荐修复（producer 侧，两行）

```python
# conanfile.py generate() / CMakeToolchain
tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
```

上游目标声明 `VERSION`/`SOVERSION` 时，lld 产出真实 `DT_SONAME` 并版本化文件
名，消费者 `DT_NEEDED` 记录裸 soname 名，经 `LD_LIBRARY_PATH`/RPATH 解析。
producer 一次修复覆盖全部消费者，且保持工具链链接期自签名有效（无需任何
post-link 处理）。本 run 两包（qaccessibilityclient 0.6.0、
accessibility-inspector 26.04.3）按此修复后双包权威 CI PASS。

## 4. fallback（诚实权衡）

- **消费侧桥接（E537 方案）**：`-l` 裸名 + `target_link_directories`/
  `IMPORTED_SONAME`。仅在 producer 不可改时用；逐消费者修补、不消除产物缺陷。
- **post-link 改写 + E077 四步重签**：`llvm-objcopy --remove-section .codesign`
  → `patchelf --replace-needed ...` → `binary-sign-tool sign -inFile F -outFile F
  -selfSign 1` → `chmod a+x F`。归档探针实证（run
  `reports/builder/probe-soname-sign/`，2026-09-04）：
  - naive 改写不重签 → exec `Operation not permitted`（rc=126）；
  - 未先 remove-section 直接重签 → `.codesign section already exists` →
    SignElf 29（rc=1）——即 E077 `forbid_2` 记载的失败模式，初版探针曾误判为
    "后处理不可行"，本条予以更正；
  - 完整四步后可执行文件 `--version` 与共享库 `ctypes.CDLL` dlopen 均 rc=0。
  权衡：每产物多改段/签名两步，量产需 E077 批量脚本；优先级低于链接期修复。

## 5. 反模式

1. **发布路径形 DT_NEEDED 产物**（conan-cache 绝对路径或 `../../bin` 相对路径）：
   只在构建机可解析；L5b 门禁只扫 `lib/lib*.so` 一级目录，可执行与子目录
   产物漏网，发布/用户侧才暴露。
2. **patchelf 后不重签 / 未 remove-section 直接重签**：前者 rc=126 被加载器
   拒绝，后者 SignElf 29 拒签；两者叠加容易被误判为"平台不支持 patchelf"
   而放弃正确方案。

## 6. 去重与关系

- `E537`：记录症状（无 SONAME → 路径泄漏）与消费侧修补；本条补全根因
  （Platform/HarmonyOS.cmake 缺失 → SONAME flag 未定义）并给出 producer 侧
  两行泛化修复。
- `E077`：签名-修改-重签机理与四步流程；本条 fallback2 直接引用并以其
  forbid_2 解释 naive 失败模式，无冲突（初版"不可行"主张已被探针撤回）。
- `E096`：同根因（平台语义缺失）的另一个后果面（C++ 标准检测失败需显式
  `CMAKE_CXX_STANDARD`）；本条是 SONAME 后果面，互补不重复。
- 检索记录见 Curator 报告 §1.4（graph/index.tsv、E*.kv grep patchelf/SONAME、
  pre-scan-rules.yaml、knowledge/drafts、经验仓均无本条覆盖）。

## 7. 原则挂钩

`P-SIGN-001`（ELF 签名必须与运行环境匹配——fallback2 的签名体系约束）、
`P-PACK-001`（任何修改 ELF 的操作后必须重签——fallback2 的流程合规依据）。

## 8. 五项质量门槛自检

1. 规则式标题 + 问题类 slug（无库名-版本命名；库名仅进 source_event 当案例）——✔
2. rec + 双 fallback（含诚实权衡）+ 2 条 forbid（reason+consequence）——✔
3. verification_cmd 自包含（ls/grep/printf+clang+readelf 三段，新 shell 可跑，
   不引用本 run 日志路径）——✔
4. principles 挂钩（P-SIGN-001/P-PACK-001）、affected_scope 泛化句式、
   similar_to 链 E537/E077/E096——✔
5. 本 run 配额：仅此 1 条（a11y 运行时边界归 notes、L0i 流程知识降级经验仓、
   C++20 面去重于 E096）——✔
