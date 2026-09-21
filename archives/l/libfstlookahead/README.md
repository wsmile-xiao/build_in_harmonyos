# libfstlookahead

libfstlookahead 是 OpenFst 的 LookAheadFst 扩展库，提供带前瞻（look-ahead）信息的有限状态转换器包装类型，
用于在组合（composition）等算法中提前剪枝、减少无效状态扩展。

## 描述

OpenFst 是开源的加权有限状态转换器（FST）库。LookAheadFst 扩展在不可变 FST（ConstFst）之上附加
前瞻匹配器数据（`ArcLookAheadMatcher` / `LabelLookAheadMatcher`），使匹配器能在访问弧之前判定
「该标签是否可达」，从而显著降低组合类算法的搜索空间。常用于语音识别与机器翻译的解码图优化。

本包只构建 LookAheadFst 扩展（`libfstlookahead`）与其三个注册模块
（`arc_lookahead-fst` / `ilabel_lookahead-fst` / `olabel_lookahead-fst`）。

## 版本列表

| 版本 | 状态 | 编译日期 | 测试状态 |
|------|------|----------|----------|
| 1.8.4 | built | 2026-09-20 | 上游 7/7 + 鸿蒙侧 25/25 通过 |

## 鸿蒙平台适配

复用 openfst 1.8.4 已验证的平台补丁（与 `archives/o/openfst/1.8.4`、`archives/l/libfstconst/1.8.4` 同 tarball）：

1. `config.guess` — 添加 aarch64-ohos 平台识别（E007）
2. `config.sub` — 添加 linux-ohos 三元组（E007）
3. `configure` — 修复 toybox sh 下的临时目录权限兼容性（E011/E064）
4. `src/lib/flags.cc` — 显式 `--help` 请求返回成功（E081）

编译要点：
- autotools 构建，`--enable-lookahead-fsts` 单独启用本扩展；上游各扩展开关默认 `no`，
  而 `--enable-bin`（fst::script 与 37 个 fst\* 命令行）默认 `yes` —— 库子包显式 `--disable-bin`：
  上游 1.8.4 的 `src/bin` 没有 lookahead 专用工具，上游测试也只链 `libfst`，而这两部分占整包编译量约 80%
- 手工编译上游测试与消费者程序时，链 `libfst.a` 必须 `-Wl,--whole-archive` 包夹，
  否则 `REGISTER_FST` 静态注册器被链接器剔除、`Fst::Read` 回退 dlopen 失败
- `make install` 用 cp/mkdir shim 替代 toybox `install -c`（HMDFS 权限限制）
- 无外部库依赖，运行时仅需 libc++_shared.so 与 libc.so

## 依赖关系

- 编译依赖：无
- 运行时依赖：libc++_shared.so（clang C++ 运行时）、libc.so（系统库）
- 本包内含同 tarball 的 openfst 核心库产物（`libfst.a`）；如需 `fst*` 命令行工具链
  （fstcompile/fstprint/...）与其它扩展，请使用 `openfst/1.8.4` 或对应子库包（如 `libfstconst/1.8.4`）

## 参考资料

- 官网：https://www.openfst.org/
- 源码：https://openfst.org/twiki/pub/FST/FstDownload/openfst-1.8.4.tar.gz
- LookAhead 文档：https://www.openfst.org/twiki/bin/view/FST/LookAheadFst

---

*最后更新：2026-09-20*
