# DRAFT：Windows 宿主 conan-verify G2（OHOS 目标）必然失败——三类失败面归因与放行判定

> 来源：xmacro/0.3pre-20000911 本机验证（2026-10-04）；适用于所有「Windows 宿主 + os=OHOS 目标」的包

## 现象

本机 `python scripts/ohc-run.py conan-verify <lib> <ver>` 报 G2 FAIL，
但 `reports/conan-create.log` 里没有任何一行真实的编译器诊断，
典型内容只有一行：

```
[WinError 2] 系统找不到指定的文件。
```

或（依赖解析阶段）：

```
ERROR: xcb-proto/1.17.0: Invalid configuration: xcb-proto supports Linux and OHOS, not Windows
```

## 使用说明（三步归因流程）

1. **读日志全文**：`archives/<lib>/<ver>/reports/conan-create.log`，不要只看 G2 摘要；
2. **按判定规则分类**：
   - **A 类 = 宿主环境限制（放行真机裁决）**，特征：
     - `[WinError 2] 系统找不到指定的文件`（配方根本没被真正执行）
     - `/system/bin/sh: <flag>: inaccessible or not found`（$CXX 空或设备路径）
     - `supports Linux and OHOS, not Windows`（依赖 validate 拒绝宿主 profile）
     - `/data/service/hnp/...`、`CONFIG_SHELL` 等设备路径 not found
   - **B 类 = 配方/源码问题（必须修，不能放行）**，特征：
     - clang 真实启动后的 `error:` 编译诊断（前面有完整编译命令行回显）
     - `conandata.yml` / `source()` / `test_package` 结构类报错
3. **A 类放行条件**：G0/G1 pass + lang-preflight pass + prescan pass +
   L0 批量自查通过 → 排真机；真机隔离 job 的 conan create 结果即权威 G2。

## 适用范围

- Windows 宿主开发机 + `os=OHOS` 目标包的本机 `conan-verify`；
- OHOS CI profile（`ci/conan/profiles/ohos-aarch64`）工具链路径指向设备
  文件系统（`/data/service/hnp/bin/...`）——宿主必然不存在这些路径；
- **不适用**：Linux/macOS 宿主、Windows 原生目标包、或日志出现真实
  clang 诊断的情况（那是 B 类，本条不可引用）。

## 输入输出定义

| 项 | 内容 |
|---|---|
| 输入 | `reports/conan-create.log`（conan-verify 自动生成） |
| 判定 | 日志特征 → A 类（环境限制）/ B 类（配方问题） |
| 输出 A | 归因结论 + notes 写明「G2 由真机 runner 裁决」→ 排真机 |
| 输出 B | 修复配方 → 本机重跑 conan-verify → 过了再排真机 |

## 示例（xmacro 实际闭环）

| 步骤 | 结果 |
|---|---|
| 本机 G2 FAIL，log 仅 `[WinError 2]` 一行 | A 类：配方从未被执行，放行 |
| 本机 G0/G1、lang-preflight、prescan、L0 自查 | 全 pass |
| 真机 r3 第 6 轮 conan create | **pass**，L0-L5 全 pass，exit 0 |
| 结论 | 配方正确；本机 G2 失败纯属宿主环境限制 |

**易混坑（同会话实测）**：`/system/bin/sh: -O2: not found` 虽然长着 A 类
面孔，但根因可能是配方用了空的 `$CXX`（R33）——应从
`tools.build:compiler_executables` conf 取编译器。判定方法：
A 类真环境限制在真机上同样会失败；真机过、本机不过的才是纯宿主限制。

## 实测证据

见上表；commit `c17e551d92`（R33 修复）与真机 run 目录日志（2026-10-04）。
