# c-data-structures 0.0-git0c2d777456 适配笔记

## 编译环境
- 构建系统: custom（header-only 库，无 configure/make/CMake；配方仅打包头文件）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（OHOS aarch64 profile: ci/conan/profiles/ohos-aarch64）
- 状态: published

## 编译步骤

1. 官方源码: https://github.com/schellingb/c-data-structures
   Snapshot commit 0c2d7774560f7c59a839d4e0162e350b63629579（上游无 release tag）
   tarball: https://github.com/schellingb/c-data-structures/archive/0c2d7774560f7c59a839d4e0162e350b63629579.tar.gz
   SHA-256: a1980927ac46d875aa06bdb48a0f53009f9c35e1a5a837d3f9901bc5054d82d2
2. 任务读取: GET /tasks/c-data-structures（executor=pc4-45，task_id
   c-data-structures-0.0-git0c2d777456-r01-pc4-45-20260927T131114Z，身份三项一致）
3. worktree 创建: 目标分支 feat/c-data-structures-0.0-git0c2d777456 零匹配，
   worktree_creation_authorized=true → 从可审计 main (32018bae04) 创建唯一专用
   worktree /storage/Users/currentUser/zhuo/worktrees/c-data-structures-0.0-git0c2d777456
   （worktree list --porcelain 恰好 1 个匹配）
4. lang-preflight（R47）: detected=c，任务语言 cpp，c↔cpp 兼容族，匹配通过
5. 上游测试编译运行（探索）: clang -O2 -Wall -Wextra test.c -o upstream_test
   → 首次运行在 test_hmap64 挂死（死循环，VmSize 涨至 2GB+）
6. 根因定位: tinyhashmap64.h hmap64__grow 首次分配 new_max=16（非 2^n-1 全 1
   掩码），探测循环 i &= maxlen 只产生槽 0/16；插入 "foo"+"bar" 后探测 "baz"
   与 "bar" 同槽 0 → 线性探测 i++ 后再次 &16 永远回到 0/16 → 死循环。
   上游 32 位版 tinyhashmap.h 用 new_max=15 正确，64 位版为笔误。
7. 修复: patches/0001-fix-tinyhashmap64-initial-new-max.patch（16→15），
   -O0/-O2 全量 test.c 均通过（test_buf/test_hmap/test_hmap64 + DONE，exit 0）
8. conan-init 生成配方 → 改写为 header-only 形态（conanfile-headeronly.py.tmpl 变体 A）：
   package() 拷贝 *.h → include、UNLICENSE → licenses；package_id 清空单一 id；
   package_info 置空 libs/bindirs。conandata.yml 声明补丁。
9. test_package: 真实消费者 test.c，仅通过安装后的公开头
   tinybuf.h/tinyhashmap.h/tinyhashmap64.h 调用宏 API（BUF_PUSH/BUF_INSERT/
   BUF_REMOVE/BUF_SWAPREMOVE、HMAP_SET_STR/HMAP_GET_STR/HMAP_PTR_STR/
   HMAP_DEL_STR、HMAP64_SET/HMAP64_GET）断言可观察结果。
10. conan create 验证配方自包含 + 消费者编译运行通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 直接传仓库页 URL 下载到 HTML | 需传 tarball URL 而非仓库主页 | 改用 GitHub commit snapshot 归档 URL（无 tag） |
| 2 | 上游 test.c 在 test_hmap64 挂死（timeout 124） | tinyhashmap64.h hmap64__grow 首次 new_max=16 非 2^n-1 掩码，探测掩码只命中槽 0/16，冲突后线性探测死循环 | patches/0001-fix-tinyhashmap64-initial-new-max.patch（16→15，与 32 位版一致）；-O0/-O2 全量验证通过 |
| 3 | /tmp 只读（E002） | 执行机 /tmp 为只读文件系统 | 全部临时产物放 worktree 内 .ohc-tmp/（TMPDIR 指向可写目录） |
| 4 | 兜底 ~/ohpcd-ai-worker-result.json 是其他库残留（crossguid） | 共享兜底文件被先前任务占用 | 本任务 result 显式 --out 指定 .ohc-tmp/result 目录，不覆盖他库记录 |

## 源码修改

patches/0001-fix-tinyhashmap64-initial-new-max.patch
- 文件: tinyhashmap64.h（hmap64__grow）
- 内容: `size_t new_max = (old_ptr ? old_hdr->maxlen * 2 + 1 : 16);`
        → `size_t new_max = (old_ptr ? old_hdr->maxlen * 2 + 1 : 15);`
- 理由: 首次分配容量必须是 2^n-1（全 1 掩码），探测循环 `i &= hdr->maxlen`
  才可覆盖全部槽位；16=0b10000 只命中 0/16 两个槽，碰撞后死循环。
  上游 32 位版本（tinyhashmap.h:172）用 15，64 位版本是复制时的笔误。

## 依赖版本

无第三方强制依赖（header-only，仅标准 C 头 stdlib/string/stdint）。

## 上游测试台账（R51 双口径，2026-09-27 实际运行）

### 枚举结果

上游源码仅一个独立测试源文件 `test.c`（main → test_buf/test_hmap/test_hmap64
三个用例函数），无 ctest、无 make check、无 pytest、无基准/样例/fixture/脚本。

| 枚举项 | 位置 | 分类 | 是否独立上游用例 |
|---|---|---|---|
| test_buf（动态数组增删改插/OOM） | test.c:45-122 | 官方用户测试 | ✅ 是 |
| test_hmap（32 位哈希表全 API + OOM） | test.c:134-232 | 官方用户测试 | ✅ 是 |
| test_hmap64（64 位哈希表全 API + OOM） | test.c:234-327 | 官方用户测试 | ✅ 是 |
| README 示例片段 | README.md | 文档示例 | ❌ 否（文档） |
| 头文件内嵌示例注释 | *.h | 文档注释 | ❌ 否（文档） |

独立上游用例总数: 3（test_buf / test_hmap / test_hmap64，均为主程序实际调用）

### 运行结果（修复补丁后）

| 用例 | 编译 | 运行 | 结果 |
|---|---|---|---|
| test_buf | clang -O2 test.c | ./a.out | 通过 |
| test_hmap | 同上 | 同上 | 通过 |
| test_hmap64 | 同上 | 同上 | 通过 |

全量通过率: 3/3 = 100%（补丁修复前 test_hmap64 因上游缺陷挂死 = 不可运行）。

## 交付物

header-only 包（无编译产物）:
- include/tinybuf.h
- include/tinyhashmap.h
- include/tinyhashmap64.h
- licenses/UNLICENSE

## 知识路径决定（Path B — 知识库扩展）

完整台账与七轴查重见 `reports/knowledge-candidate-ledger.md`（reports/ 随最终
回报提交，不入 PR）。摘要：

| 候选 | 四范围查重 | 决定 |
|---|---|---|
| tinyhashmap64.h 首次 new_max=16 非 2^n-1 掩码 → 探测死循环 | 全仓未命中（E321/E257/E307 仅覆盖 header-only 配方一般形态） | **new_draft** |
| 纯 header-only C 库无构建系统配方形态 | E321/E257/E307/E322 已覆盖 | **reuse_existing** |

- 草稿：`knowledge/drafts/DRAFT-c-data-structures-tinyhashmap64-probe-mask.{kv,md}`
  （同 stem 配对，随本 PR 提交）

## 知识沉淀（✅ 已提取）

- ✅ 开放寻址哈希表初始容量必须为 2^n-1（全 1 掩码）：tinyhashmap64.h
  hmap64__grow 首次 `new_max=16` 时探测掩码 `i &= maxlen` 只命中槽 0/16，
  插入两个字符串键后探测缺失键线性探测死循环（上游 test_hmap64 挂死、
  VmSize 暴涨）；32 位版 tinyhashmap.h 用 15 正确，64 位版是复制笔误。
  修复 16→15，-O0/-O2 全量 test.c 通过（DRAFT-c-data-structures-tinyhashmap64-probe-mask）

## 注意事项

- header-only 库无 commands.json（非 CLI，构建产物无 bin/ 可执行文件，R38）
- 补丁修改的是上游算法缺陷而非平台适配，需在 PR 中说明
- 版本号 0.0-git0c2d777456 表示上游无 tag，取 commit 快照
---

**编译结束**: 2026-09-27 22:11
**最终状态**: published
