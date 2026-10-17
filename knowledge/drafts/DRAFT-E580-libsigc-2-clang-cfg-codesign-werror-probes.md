# OHOS clang cfg 文件注入 -Wl,--code-sign 破坏 Meson -Werror 探针 — -Qunused-arguments 对冲

- **草稿 ID**: DRAFT-E580-libsigc-2-clang-cfg-codesign-werror-probes
- **来源**: libsigc-2/2.12.2 适配本地验证（feat/libsigc-2-2.12.2 分支）
- **分类**: meson / ohos-platform / clang-wrapper / compiler-probes / code-sign
- **状态**: 本地草稿（未创建 Issue/PR，未生成知识编号，无远端链接，无审核结论）

## 问题 / 错误签名

- `conan create`（Meson 构建）在编译期探针处失败，meson-log.txt 中：

  ```
  Command line: `clang++ -c ... -Werror=unused-command-line-argument ...`
  error: -Wl,--code-sign: 'linker' input unused
         [-Werror,-Wunused-command-line-argument]
  ```

- 受影响探针（libsigc++ 2.12.2）：`gcc_template_specialization_operator_overload`
  （决定 `SIGC_TEMPLATE_SPECIALIZATION_OPERATOR_OVERLOAD` 宏）。
  探针失败 → 宏未定义 → lambda slot 走 `sun_forte_workaround` 分支 →
  `sigc++/adaptor_trait.h` 与 `base.h` 编译错误（模板操作符重载解析失败）。
- 复现：本地 OHOS SDK 工具链（`usr/local/bin/clang++` sh 包装脚本 +
  `aarch64-unknown-linux-ohos.cfg`）下运行 `meson setup` 即触发；
  同一配方在 CI 的 `/data/service/hnp` clang（无 cfg 注入）不受影响。

## 根因

1. 本地 OHOS SDK 的 clang 包装脚本读取 `aarch64-unknown-linux-ohos.cfg`，
   该 cfg 将 `-Wl,--code-sign` **前置到每次 driver 调用**（保证产物带
   `.codesign`/`.note.ohos.ident`）。
2. Meson 的编译-only 探针以 `-Werror=unused-command-line-argument` 运行：
   编译阶段出现链接器专用旗标时，clang 将其判为 unused 并升级为错误。
3. 结果：探针误判「编译器不支持该特性」，上游按降级路径生成
   `sigc++config.h`，与源码真实能力不符。

## 最小修复方案

在 `archives/l/libsigc-2/2.12.2/**` 范围内：

1. **配方** `conanfile.py` `generate()`（`os == "OHOS"` 分支）：

   ```python
   tc.extra_cflags.append("-Qunused-arguments")
   tc.extra_cxxflags.append("-Qunused-arguments")
   ```

   `-Qunused-arguments` 仅抑制 driver 对未消费旗标的诊断，不触碰源码级
   警告、上游测试条件或链接步骤。
2. 修复后探针按真实能力通过（`SIGC_TEMPLATE_SPECIALIZATION_OPERATOR_OVERLOAD`
   正确定义），最终 `.so` 仍带 `.codesign` 节与 `.note.ohos.ident`
   （readelf -SW / readelf -n 验证），SONAME/NEEDED 不受影响。

## 验证证据

- 修复前 meson-log：探针命令带 `-Werror=unused-command-line-argument`，
  `-Wl,--code-sign` 触发 `error: 'linker' input unused`，构建失败。
- 修复后（加 `-Qunused-arguments`）：同一探针返回码 0，
  `sigc++config.h` 定义 `SIGC_GCC_TEMPLATE_SPECIALIZATION_OPERATOR_OVERLOAD 1`；
  上游 32 测试全过（shared/static 两个变体）；`.codesign` 节保留。
- 作用域隔离：该 flag 仅在 `str(self.settings.os) == "OHOS"` 分支追加，
  其他平台不受影响。

## 适用边界

- **仅对冲无法控制的工具链注入**：`-Qunused-arguments` 只用于 OHOS
  clang cfg 前置 `-Wl,--code-sign` 这类适配层无法逐条剥离的 driver
  旗标；不得用于掩盖配方/脚本自身传错的旗标（那类错误应修正传参本身）。
- **不作全局通用开关**：不加入全局 profile、非 OHOS 分支或其他包的
  公共构建参数；本配方内也只挂在 `os == "OHOS"` 条件下，Linux 构建
  保留原生 unused-argument 诊断。
- **优先配置层修复**：若后续 OHOS SDK 允许在 cfg/包装脚本层把
  `--code-sign` 只注入链接命令（或以 `-Xlinker` 分离传递），应优先
  该方案并移除本对冲 flag；`-Qunused-arguments` 是当下「无法修改
  SDK cfg」约束下的次优选择。

## 风险 / 范围评估

- `-Qunused-arguments` 是 clang driver 官方旗标（抑制「unused argument」
  类诊断），语义稳定；若上游未来新增真正需要报警的未消费旗标，
  本地构建会静默——可接受（CI 侧无 cfg 注入，仍会报警）。
- 与 E050（copy-replace-symlink）、E073（configure-static-only）、
  E219（CI buildenv python）无重叠：本条专门覆盖「工具链 cfg 注入
  链接器旗标 × 编译探针 -Werror」这一交叉故障面。
