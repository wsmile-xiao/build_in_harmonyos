# fork 只代换了一条构建线的版本串时，另一条构建线会产出「版本漂移」的运行库

- **id**: `DRAFT-6818-libdb-5.3.35-fork-version-strings-drift-from-release`
- **severity**: 2（不炸构建，但运行库对外自报错误版本 / region 一致性判定被污染）
- **category**: build, packaging, conan, versioning, observability
- **来源**: `archives/l/libdb/5.3.35` 适配（PR 11637，平台任务 #6818）
- **状态**: UNMATCHED（草稿，待审）

## 一句话

fork 的发布脚本只把 **Autotools 线**的版本刷到 5.3.35（`dist/configure.ac` → `dist/configure`），
而 **Meson 线**的版本串分散在三处、全部停在旧值；其中 `dist/meson/db_subs.json` 是
`gen_header.py` 的替换表，渲染出的 `DB_VERSION_PATCH` / `DB_VERSION_STRING` /
`DB_VERSION_FULL_STRING` 会**编译进库**，并且正是 `db_version()` / `db_full_version()`
的返回值 —— 也就是说，**版本宏不是可忽略的元数据，而是运行时可观测的自报值**。

## 版本串分布（libdb 5.3.35 实证）

| 文件 | 谁读它 | 原值 | 落差 |
|---|---|---|---|
| `dist/configure` | 构建 Autotools 线 | 5.3.35 | ← 发布脚本**只刷了这一处** |
| `dist/meson/db_subs.json` | `dist/meson/gen_header.py` → 渲染公开头 `db.h`，宏**编译进库** | 5.3.29 | 落后 6 个 patch |
| `dist/meson.build` | `cdata.set_quoted(PACKAGE_VERSION/STRING)` → 私有头 `db_config.h`（不安装） | 5.3.34 | 落后 1 个 patch |
| `meson.build` | `project()` 版本，纯元数据 | 5.3.34 | 落后 1 个 patch |

三处的差别不只是「数字不一样」，而是**谁来读、读到的值进入哪个产物**不一样。
只有第二行会造成**功能性**漂移。

## 为什么这不是「元数据无关紧要」

```c
/* src/env/env_open.c:34-38, 59-63 —— db_version() / db_full_version() 的实现 */
return DB_VERSION_STRING;        /* "Berkeley DB 5.3.29: (libdb fork)" */
return DB_VERSION_FULL_STRING;   /* "... 11.2.5.3.29: (libdb fork)" */
```

- 用 Meson 构建出来的运行库，会向**所有消费者**自报 5.3.29。
- `src/env/env_region.c:253` 的 region 版本一致性校验读的是同一批宏，漂移会影响
  **同一进程内不同来源 region 的一致性判定**。
- 因此补丁不是「对齐一下好看」，而是修一个运行时可观测的错误。

## 判据（可复现）

```bash
# 1) 同一个版本号在所有构建描述文件里揪出来，看是否一致
grep -rn "5\.3\.[0-9]\+" dist/configure dist/meson/db_subs.json \
                          dist/meson.build meson.build

# 2) 确认「谁读 db_subs.json」——它驱动公开头 db.h 的渲染
grep -rn 'db_subs.json\|DB_VERSION_PATCH' dist/meson/gen_header.py

# 3) 确认版本宏真的会被消费者观测到
grep -n 'db_version\|db_full_version' src/env/env_open.c
#    → 两个函数都 return DB_VERSION_* 宏

# 4) 补丁前后逐字节比对生成的头（应只有版本宏不同）
diff <(gen_header 前) <(gen_header 后)
```

## 对策与验收

补丁范围**只改版本字符串字面量**，不动任何替换项（类型声明、printf 格式、平台头/尾）
与任何代码，保证生成的头文件除版本宏外逐字节相同。补丁必须覆盖**全部**不一致处
（本例 3 个文件）——只补 `db_subs.json` 会让 `db_config.h` 与 `project()` 继续漂移，
反过来只补 `meson.build` 则运行库仍自报旧版。

验收必须从**消费者视角**做端到端断言：

```
db.h 的编译期宏  ==  db_version() 的返回值  ==  db_full_version() 的全串
                   （本例 family/release 段 11 / 2，全串 11.2.5.3.35）
```

只断言其中一者会漏掉「改了但没生效」的假绿。

## 配方侧落地

```python
def build(self):
    apply_conandata_patches(self)   # patches/0001-meson-version-metadata-align.patch
```

`test_package/test_libdb.c` 的 A 组断言即上述三者同一性检查
（`MANIFEST.yml: test_package_tests[0]`）。

## 不要这么做

- `sed -i` 直接改库源码里的 `#define DB_VERSION_PATCH` → 生成物与「源」脱节，
  下次重新生成头文件时被覆盖。
- `#if 0` / `strcmp` 短路版本断言 → 放弃「改了但没生效」的检测，属于把验收手段
  废掉而不是修复缺陷。
- `skip.*version` / `--gtest_filter=-.*[Vv]ersion` → 伪造通过率；rule4 要求如实
  统计「执行集 X/X + 未执行 Z」并给出技术理由。

## 相关条目

- `DRAFT-6818-libdb-5.3.35-meson-sidesteps-autotools-hmdfs-pits` —— 同批适配的另一条：
  为什么本包选 Meson 而不是 Autotools（也正是「两条构建线并存」这个前提本身）
- `DRAFT-libgmobile-0.7.2-meson-not-installed-is-not-skipped-and-exit-code-is-not-coverage`
  —— 同属「元数据/统计口径不一致导致看起来绿、实际没验到」家族
