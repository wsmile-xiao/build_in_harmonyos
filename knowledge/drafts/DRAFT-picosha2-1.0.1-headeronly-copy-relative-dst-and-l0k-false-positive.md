# DRAFT-picosha2-1.0.1-headeronly-copy-relative-dst-and-l0k-false-positive：header-only 配方 package() 相对 dst 零产出与 L0k 模板注释误判

> Contributor: pc1-35 | Status: Draft | Updated: 2026-09-05
> Source: picosha2 1.0.1 HarmonyOS PC adaptation（archives/p/picosha2/1.0.1，r01）
> 对应：knowledge/drafts/DRAFT-picosha2-1.0.1-headeronly-copy-relative-dst-and-l0k-false-positive.kv

## 现象

picosha2 1.0.1（header-only SHA-256 库，单头文件 picosha2.h）在 OHOS armv8
Conan 2.x 适配中，conan-verify 与 finish W3 连续出现两类与库本体无关的门禁失败：

```text
# 1. conan-verify G2（conan create）——package() 零产出
picosha2/1.0.1@ohpcd/stable: package(): WARN: No files in this package!
CMake Error in CMakeLists.txt:
  Imported target "picosha2::picosha2" includes non-existent path
    ".../p/include" in its INTERFACE_INCLUDE_DIRECTORIES.

# 2. finish W3（build_and_test.sh L0k）——CLI 工具误判
[fail] L0k: CLI tool detected but commands.json missing (R38)
L0_ERRORS=... commands_json_r38
```

## 根因分析

1. **package() 相对 dst 在 Conan2 缓存构建中零产出**：headeronly 模板生成的
   `copy(self, "*.h", src=self.source_folder, dst="include")` 使用相对目标
   `"include"`，在 conan create 的缓存构建（`b/.../p` 为 package 目录）中，
   相对路径不会可靠落入 package 目录，最终 `package()` 产零文件
   （`No files in this package!`），test_package 的 CMakeDeps 生成的 imported
   target 因此引用不存在的 `.../p/include` 路径，G2 失败。
   修复：dst 必须用绝对路径
   `os.path.join(self.package_folder, "include")`（同已合入的
   args-parser/catch2/doctest header-only 配方做法）。
2. **layout 选择**：headeronly 模板默认 `basic_layout(self)` 在缓存构建中
   `self.source_folder` 与源码解压位置关系不稳定；改用
   `cmake_layout(self, src_folder=".")` 与已合入 header-only 配方一致。
3. **package_type 陷阱**：模板默认 `package_type = "library"`，Conan 2 要求
   "library" 类型必须声明 `shared` option，否则报
   `Package type is 'library', but no 'shared' option declared`（E277 已覆盖该
   报错，直接采用其修复：header-only 用 `package_type = "header-library"`）。
4. **L0k 模板注释误判**：headeronly 模板保留变体 B/C 注释块，其中
   `# copy(self, "picosha2", src=self.source_folder, dst="bin")` 含有
   `dst="bin"` 字样；build_and_test.sh L0k 门禁用 grep 匹配
   `dst\s*=\s*["']bin["']` 判定 CLI 工具，注释也被匹配 →
   "CLI tool detected but commands.json missing" → commands_json_r38 假阳性。
   修复：生成配方后删除变体 B/C 注释块（header-only 库无 bin 产物）。
5. **L0d stub_test_method 门禁**：test_package 的 `test()` 必须含 `self.run()`
   真实执行（`self.run(os.path.join(self.cpp.build.bindirs[0], "test_<name>"),
   env="conanrun")`），纯 `cmake.test()` 无 `self.run` 会被判为 stub。

## 与现有知识的关系（确认去重证据）

检查范围：knowledge/graph + knowledge/drafts（只读快照
knowledge-snapshot-picosha2-1.0.1-r01-pc1-35-20260905T123255Z，HEAD
0b458be188c0740435e57607d31384570d947f57）。
检索词：header-only / headeronly / header-library / package_type / copy / dst /
include / No files in this package / commands_json_r38 / L0k / shared option。

逐字段比较：

| 既有条目 | 覆盖点 | 是否等价命中 |
|---|---|---|
| E257 | conan-verify G1 要求显式 build()（no-op 即可） | 命中（走 A，本轮直接采用） |
| E277 | `Package type is 'library', but no 'shared' option declared` → header-library | 命中（走 A，本轮直接采用） |
| E322 / E470 | header-only CMake INTERFACE 配方形态、package_type=header-library、self.info.clear | 部分命中（配方形态一致） |
| E255 / E241 | L0 门禁对无编译包不适用、commands.json / stub_test_method 规则 | 部分命中（门禁规则层面） |
| — | package() 相对 dst 缓存构建零产出（No files in this package） | **无等价命中，新建** |
| — | headeronly 模板残留注释触发 L0k commands_json_r38 假阳性 | **无等价命中，新建** |

结论：E257/E277/E322/E470/E255/E241 已覆盖 G1 build()、shared option、配方形态
与门禁规则；本条目沉淀两个未覆盖的可复用坑（copy 相对 dst 零产出 + 模板注释
L0k 误判），走路径 B 新建草稿对。

## 方案

1. `package_type = "header-library"`（无 shared option 报错）。
2. `layout`: `cmake_layout(self, src_folder=".")`。
3. `package()`: copy 目标一律
   `os.path.join(self.package_folder, "include")` / `"licenses"` 绝对路径。
4. 删除 headeronly 模板变体 B/C 注释块（含 `dst="bin"` 字样）。
5. `test_package` 的 `test()` 用 `self.run(...)` 真实运行消费者二进制；
   消费者测试（test_picosha2.cpp）真实 include picosha2.h 并对 NIST/RFC 已知
   SHA-256 向量断言（R34）。

## 验证证据

- `conan-verify picosha2 1.0.1`：G1/G0/G2/G3 PASS（G4/L2/L4/L5 适用通过），
  报告 archives/p/picosha2/1.0.1/reports/conan-verify-report.md。
- `finish picosha2 1.0.1 built`：W3 build_and_test.sh RC=0，
  L0 全 pass（Pass rate 100%），W2 PR 原子性通过。
- 上游测试：test/test.cpp 经 CTest 运行 202/202 succeeded（0 failed）。
- 消费者测试 test_picosha2：4 组 NIST/RFC 向量断言全部通过。

## 禁止做法

- `copy(self, "*.h", src=self.source_folder, dst="include")` 相对 dst
  （缓存构建零产出）。
- conanfile.py 中残留 `dst="bin"` / `RUNTIME DESTINATION bin` 字样
  （L0k 误判 CLI 工具）。
- `package_type = "library"` 却不声明 shared option（Conan2 报错，E277）。
- test_package test() 无 self.run() 真实执行（L0d stub_test_method）。

## 适用边界

- 适用：OHOS/CI 下所有 header-only（无构建族 A）C/C++ 库的 Conan 2.x 配方。
- 不适用：有编译产物的库（copy/install 走 cmake install 路径，无此问题）；
  数据/资源包（变体 B/C 有各自模板要点，见 E255/E241）。

## 限制与反例

- 本条目基于 picosha2 1.0.1 单次实证（metrics_confidence 1.0，1 成功 0 失败）；
  模板后续修订若删除变体注释，L0k 误判点将自然消失，但仍保留 copy dst 要点。
- 若上游库头文件位于子目录，copy 模式需相应调整（如 doctest 用 "**/doctest.h"）。
