# E-DRAFT: clang15 在 -Werror 下将 -Wfortify-source（sscanf 溢出）与 -Wmisleading-indentation 升级为硬错误

- **触发实例**：astronomy 2.1.9 适配（2026-09-19，分支 feat/astronomy-2.1.9）
- **错误签名**：
  - `'sscanf' may overflow; destination buffer in argument 4 has size 20, but the corresponding specifier may require size 21 [-Werror,-Wfortify-source]`
  - `error: misleading indentation; statement is not part of the previous 'if' [-Werror,-Wmisleading-indentation]`
- **类别**：toolchain-strict-warning（工具链严格告警类）
- **严重度**：2（编译期确定性失败，处置模式固定）

## 症状

上游 `generate/ctbuild` 用 `-Wall -Werror` 编译 C 单元测试时，OHOS clang15 报两类
硬错误：

```text
ctest.c:6626:59: error: 'sscanf' may overflow; destination buffer in argument 4 has size 20,
                      but the corresponding specifier may require size 21 [-Werror,-Wfortify-source]
novas/novas.c:3431:10: error: misleading indentation; statement is not part of the previous 'if'
                        [-Werror,-Wmisleading-indentation]
```

## 根因

上游测试代码按 gcc 环境的告警面编写。OHOS 工具链 clang15 的
`-Wfortify-source`（对 `sscanf` 的 `%Ns` 定宽说明符做缓冲容量检查，
`char[20]` 配 `%20s` 需要 21 字节容纳 NUL）与 `-Wmisleading-indentation`
（对缩进不规则的条件语句告警，NOVAS 这类数值库常见）比 gcc 更严格，
且都被 `-Werror` 升级为错误。

## 处置（不动源码、不加补丁）

测试构建时**按类降级**（不是笼统 `-Wno-error`）：

```bash
clang -O3 -ffp-contract=off -Wall -Werror \
      -Wno-error=fortify-source -Wno-error=misleading-indentation \
      -o ctest -I ../source/c/ ../source/c/astronomy.c ctest.c -lm
```

对 ctbuild/generate 等多脚本构建，用 CC 包装脚本在参数末尾追加
（保证在 `-Werror` 之后，顺序不会重新启用）：

```sh
#!/bin/sh
exec clang "$@" -Wno-error=fortify-source -Wno-error=misleading-indentation
```

库本体（astronomy.c）保持严格编译零告警。

## 验证

- `./ctest all`：42/42 全部 PASS
- `./generate`（含 novas.c）：构建成功，`validate_top2013` PASS

## 适用边界

- **适用**：clang15/OHOS 工具链下用 `-Werror` 构建含 `sscanf %Ns` 定宽
  缓冲或缩进不规则 C 代码（数值库/大表生成代码）的测试/工具链构建。
- **反例**：若 `-Werror` 必须保留且 sscanf 调用确有溢出风险，应改缓冲
  大小（`char[21]` 配 `%20s`）而非降级告警；库本体不得用降级掩盖问题。

## 查重

- 完整重复：无；因果重复：无
- 部分重叠：E063（add-cflags-disable-werror，`-Wno-error=` 通用手法，
  但关键词与示例仅覆盖 int-conversion/incompatible-pointer/implicit-function/
  format-truncation，不含 fortify-source 与 misleading-indentation）
- 新增差异：两类新告警（sscanf 缓冲溢出 + 缩进类）的具体触发与处置组合
- 关系：similar_to E063

## 决定

**new_draft（路径 B）**——部分覆盖 E063 且存在已由真实日志验证的新增差异，
可跨库复用。
