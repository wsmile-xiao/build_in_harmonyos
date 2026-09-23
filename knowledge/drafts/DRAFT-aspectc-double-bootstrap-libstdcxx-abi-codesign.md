# Draft: 编译器类三方库双重自举死锁 → 外部静态库补齐 + MINI 免 weave；跨编译器 ABI 统一；签名前移除 .codesign

> Status: DRAFT | Source: aspectc 2.5 (OpenHarmony PC), PR #8631 | 原则: 无
> 严重度: 🔴 high | 分类: bootstrap/toolchain/clang/abi/lld/elf/signing | 自动修复: ✅ patch + conanfile 选项

> **结构化数据**: [graph](../knowledge/graph/DRAFT-aspectc-double-bootstrap-libstdcxx-abi-codesign.kv) 对应 draft .kv

---

## 错误特征

```
（构建期）ld.lld: error: unable to find library -lclangSema / -lclangAST ...
（织入期）make: *** No rule to make target 'ac++' ... （完整 Puma 需织入，无 aarch64 官方二进制）
（链接期）undefined reference to 'std::__cxx11::...'  /  ld.lld: error: duplicate symbol '...abi...'
（运行期）symbol lookup error: secure_getenv  /  exec format / 加载器拒绝 .codesign 段
```

（配套：`cannot find -lclang*`、`-stdlib=libstdc++ not supported`、
`objcopy --remove-section .codesign`、`patchelf --set-rpath` 等。）

## 根因

- aspectc（AspectC++ 织入编译器 ac++/ag++）构建存在**双重自举死锁**：
  ① `FRONTEND=Clang` 需要 clang 18+ 的完整静态库（`-lclangSema -lclangAST ...`），而
  OHOS SDK 只有 clang 15.0.4 且无任何 `libclang*.a`；
  ② 完整 Puma 含 ASPECTS 必须用 ac++/ag++ 自身织入，而官方无 aarch64 二进制、
  2.x 不再发布 woven 包——前端静态库缺失与自举织入缺失互为死锁；
- Alpine 的 LLVM 对象基于 **libstdc++** 编译，与 OHOS 默认 **libc++** 混链会因
  `std::__cxx11` vs `std::__n1` mangling 失败；
- 产物是 OHOS ELF 工具，SDK lld 链接产物自带 `.codesign` 段，签名前须移除，且
  RUNPATH 注入与签名顺序不可颠倒。

## 首错（First Error）

`FRONTEND=Clang` 下 make 链接 ac++/ag++ 时 `unable to find library -lclangSema`（OHOS SDK
无 clang 18 静态库），早于任何可运行产物。

## 诊断顺序（Diagnosis Order）

1. 读上游构建文档确定 FRONTEND 选项与自举方式（aspectc 须区分 FRONTEND=Clang/Gcc）；
2. `find <OHOS_SDK> -name 'libclang*.a'` 确认 SDK 无静态库；`llvm-config --version` 确认版本；
3. 判定织入自举是否可免：查上游 Makefile 的 `MINI=1` / MINI 构建选项（免 weave 出
   libMiniPuma.a）；
4. 查目标平台 musl 匹配的外部源（Alpine aarch64 clang18-static/llvm18-static 与 OHOS 同为 musl）。

## 失败替代方案（Fallback）

若目标平台无法取得与 libc++ 匹配的 clang/LLVM 静态库，且上游无 MINI 免织入构建，
则本工具不可直接适配——须先解决前端库来源（如自编 clang 18，成本极高）或放弃该库。

## 验证边界（Validation Boundary）

- 链接必须全程无 `unable to find library` / `duplicate symbol` / `undefined reference`；
- 统一 ABI 后混链对象无 `__cxx11`/`__n1` 冲突（`nm` 抽查）；
- 产物签名后可在 OHOS 运行：test_package 冒烟（ag++ 织入 → 签名 → 运行输出），
  exit ≠ 127 且输出正确；签名前 `.codesign` 段必须已移除。

## 解决方案

1. **打破自举死锁**：Alpine 3.21 aarch64（musl，与 OHOS 匹配）装
   clang18-static/llvm18-static 补齐 283 个 `.a`；Puma `MINI=1` 免 weave（libMiniPuma.a）。
2. **ABI 统一为 libstdc++**：全部源码 `-nostdinc++ -isystem <libstdc++ headers>
   -nostdlib++ -lstdc++`，绕过 OHOS clang 拒绝 `-stdlib=libstdc++`。
3. **CXX link-wrapper**：aspectc 自身 LDFLAGS 把 `-lstdc++` 排在 libacmodel/libMiniPuma
   之前致 lld 单遍扫描无法回补；链接末尾追加 libstdc++.a + secure_getenv stub，
   `-nostdlib++` 防 SDK libc++abi duplicate 符号。
4. **签名前清理**：`objcopy --remove-section .codesign`；先 `patchelf --set-rpath`
   注入 RUNPATH 再签名（顺序不可颠倒）。
5. **conanfile.py**：FRONTEND=Clang + Puma MINI=1；CXX=wrapper 脚本；LDFLAGS 末尾补
   libstdc++.a -lstdc++；签名步骤 objcopy 移除 .codesign。

## 跨库复用价值

- 任何 `FRONTEND=Clang` 的编译器/静态分析工具（Puma、clang 前端驱动的语言工具）在
  OHOS 上的适配——「SDK 无 clang 静态库 → 外部 musl 静态库补齐」是通用模式；
- 任何需要跨 libc++/libstdc++ 混链的工具链——「统一 ABI + link-wrapper 收尾补库」通用；
- 任何 SDK lld 链接的 OHOS 原生工具——「签名前 objcopy 移除 .codesign」通用。
