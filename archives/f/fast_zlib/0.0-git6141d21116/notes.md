# fast_zlib 0.0-git6141d21116 适配笔记

## 编译环境
- 构建系统: custom（上游 genmake 工程，实际由 conanfile.py 直接 clang 编译）
- 编译日期: 2026-09-28
- 编译器: clang 15 (aarch64-linux-ohos, /data/service/hnp/bin/clang)
- 状态: published

## 编译步骤

1. 源码：fast_zlib 上游仓库 —— 上游无 release tag，按 git snapshot 惯例版本号 `0.0-git6141d21116`
   （commit 6141d21116692cd95c0c5dc17106758c372b9fc4，2022-10-14 "Updated for zlib 1.2.13"）。
   仓库快照用 codeload 下载（github.com 主页超时；codeload 200 OK），校验 SHA-256
   `bd299601789aacce05d3d7cdb82e9e09d8128ec96b631e885819b0e23d0487c8`。
2. 嵌入依赖：fast_zlib 不是独立库，是对 zlib deflate 的 longest_match 快速替换
   （Sources/match.h），构建必须带 zlib 1.2.13 源码（上游 zlib/ 目录仅占位 readme.txt）。
   下载官方 zlib v1.2.13（GitHub tag 归档，SHA-256
   `1525952a0a567581792613a9723333d7f8cc20b87a81f920fb8bc7e3f2251428`）放入 `zlib/`。
3. 补丁：应用上游官方 `Sources/zlib_1.2.13.patch`（zlib≥1.2.13 移除 ASMV 后
   longest_match 不可替换，需补丁恢复 ASMV 守卫）。conandata `strip: 1`（补丁路径带
   original//patched/ 前缀）。
4. 构建：conanfile.py 用 compile-commands 思路直接编译 zlib COMMON_FILES +
   `Test/deflate_stub.c`（`#define ASMV; #include "deflate.c"; #include "match.h"`，
   等价上游 genmake TYPE=C 目标）为 `libz.a`（静态）。R26：zlib 是系统同名库，静态-only。
5. 验证：conan-verify 全部门禁（G0-G4 + L2/L4/L5）通过 ↓

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 下载超时（Errno 110） | 网络对 github.com 主域直连超时 | 用 codeload.github.com / ghfast.top 镜像下载；conan-verify 自动注入 E017 镜像 |
| 2 | 上游补丁应用失败 "source/target file does not exist" | conan patch 默认 strip=0，但补丁路径带 `original/`/`patched/` 前缀 | conandata 补丁条目加 `strip: 1` |
| 3 | conan create 产物为空 "No files in this package!" | `copy()` 的 dst 用了相对路径，落到了 build 目录而非 package 目录 | package() 中 dst 改用 `os.path.join(self.package_folder, "lib"/"include")` 绝对路径 |
| 4 | test_package CMake "Library 'z' not found" | 空产物导致 libz.a 未进包 | 同 #3 |
| 5 | zlib 1.2.13 编译大量 `-Wdeprecated-non-prototype` 警告 | K&R 风格函数定义 + clang 15 新警告 | 警告不阻塞（上游代码风格），不加 -Werror |

## 源码修改

- `patches/zlib_1.2.13.patch`：上游官方补丁（Sources/zlib_1.2.13.patch 原样），
  给 zlib 1.2.13 deflate.c 恢复 ASMV 守卫，使 fast_zlib 的 match.h 可以替换 longest_match。

## 依赖版本

- 无 conan 外部依赖（fast_zlib 自带 zlib 1.2.13 嵌入源码，非 requires 依赖；R36 不适用）
- 嵌入源码：zlib 1.2.13（官方 madler/zlib v1.2.13 tag）

## 验证结果

```bash
# conan-verify（G0-G4 + L2/L4/L5 全过）
python3 scripts/ohc-run.py conan-verify fast_zlib 0.0-git6141d21116   # → PASS

# 上游测试 4/4 通过（详见 reports/upstream-tests-ledger.md）
./obj/bin/test-C-linux <data> --level=9       # "NewC":9 → rc=0
./obj/bin/test-Orig-linux <data> --level=9    # "Orig":9 → rc=0
zlib-example <dir>                            # rc=0
echo hello | zlib-minigzip | zlib-minigzip -d # rc=0
```

## 注意事项

- fast_zlib 优化的是 deflate 内部 longest_match（C 版快速匹配），公开 API 面与 zlib 完全一致；
  消费者用 `zlib.h` 公开头即可，无需知晓内部实现。
- ASM 变体（match32.asm）为 x86 专用，aarch64 平台不适用，未打包。
- 包名 `fast_zlib` 提供 zlib 兼容库（libz.a），cmake target `fast_zlib::fast_zlib`。
## R02 返工：HarmonyOS 专项测试（2026-09-28）

- 缺口：r01 未新增鸿蒙特有测试（适配交付硬门禁）。
- 新增 `test_package/ohos_specific_test.c`：
  - 核验 `fast_lm_copyright` 符号链接（llvm-nm libz.a → R fast_lm_copyright），证明快速匹配实现真实接入 OHOS 产物；
  - compress2/uncompress 1MB 往返（ratio 0.02）+ 流式 deflate/inflate Z_FINISH 往返；
  - UNALIGNED_OK 未对齐访问路径在 OHOS aarch64 行为正确；
  - zlibVersion()==1.2.13。
- 运行：clang 15 (aarch64-linux-ohos) 编译 rc=0；实际运行 rc=0（reports/ohos-specific-test-run.log）。
- test_package CMakeLists/MANIFEST 注册该用例；conan-verify G2 test_package 构建并运行
  （Test #2 ohos_specific_test Passed）。
- 三轨计数：上游 4/4、鸿蒙特有 1/1、消费者 1/1。
---

**编译结束**: 2026-09-28 16:50
**最终状态**: published
