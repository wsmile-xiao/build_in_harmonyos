# DRAFT: lang-preflight 对辅助 Android demo 的 build.gradle 误判 mixed

> 草稿编号：DRAFT-crossguid-0.2.2-lang-preflight-aux-gradle-misdetect（同 stem .kv 配对）

## 问题

C++ 三方库源码树含辅助 Android/JNI demo 子工程（`android/`，含 `build.gradle` + `MainActivity.java`）时，
`ohc-run.py lang-preflight`（R47）把任务标记 cpp 的库误判为 `mixed` → 自动写 `env_unsupported`，
整个适配任务被拦下。

## 根因

`scripts/ohc/lang_detect.py` 的 `_manifest_scan` 用**全树文件名字集合**（`names = {p.name for p in files}`，rglob 递归）
匹配 `build.gradle`/`pom.xml`（第 122 行，java/gradle/maven 分支），且该分支排在**顶层** `CMakeLists.txt`
分支（第 124 行，仅 `tops`）之前。辅助工程里的 `build.gradle` 因此压过顶层 CMakeLists 的 c/cpp 判定，
与源码统计（cpp ≥ 70%）冲突 → §4.7 冲突规则 → `mixed` → `env_unsupported`。

## 判定边界（R47 D.4「辅助脚本不算主体」）

主库主体为 C/C++（顶层 CMakeLists + .cpp/.hpp 实源，统计占比 ≥70%）时，辅助目录（android/ demo、
tests/ 参考实现等）的 manifest 不参与主体语言判定 → 应判 `cpp`，c↔cpp 兼容族不迁移。

## 方案

1. 收到 `detected_language: mixed` 且任务语言为 c/cpp 时，先核对主库主体（顶层 manifest + 源码占比）。
2. 复制源码到临时目录剔除辅助子目录后复跑 `lang-preflight`，取得工具自身 cpp 判定作为证据。
3. 记录证据后按 `cpp` 继续适配主流程；仅当主库主体确为非 c/cpp 时才走 `env_unsupported`/`lang_hold`。

```bash
cp -r <src> <copy> && rm -rf <copy>/android
python3 scripts/ohc-run.py lang-preflight <软件> <版本> --src <copy>
```

## 适用边界 / 反例

- 适用：含辅助 gradle/android demo、或任意子目录含 build.gradle/pom.xml 的 C/C++ 库。
- 反例：真实混合语言项目（主交付物确为 Java/gradle）应按 mixed/env_unsupported 如实上报迁移，
  不得以本规则硬适配。

## 验证

- crossguid 0.2.2：全树复跑 `detected=mixed(gradle/maven)`；剔除 `android/` 后复跑
  `detected=cpp`（manifest=CMakeLists.txt project(CrossGuid)，cpp 100%）。两次输出对比为证据。
- 既有条目/草稿：`similar_to` DRAFT-exr_image-0.1.0-rc3-lang-preflight-aux-manifest、
  DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect、DRAFT-onnx-1.20.0-lang-preflight-pyproject-priority-cpp-deliverable-misdetect
  （同根因族：全树 manifest 扫描 + 非 c/cpp 分支优先 + 辅助目录不计主体）；本条目新增触发分支为
  **build.gradle→java/gradle**（Android/JNI demo 整工程 manifest），上述条目均未覆盖。
- 关系字段：`caused_by=[]`、`prerequisite_of=[]`、`conflicts_with=[]`。

## 查重结论

`exact_duplicate=false, causal_duplicate=true, trigger_overlap=partial, solution_overlap=high,
combination_novelty=false, boundary_novelty=true, test_migration_novelty=false` → **new_draft**。

---
*作者: AtomCode | 来源: crossguid 0.2.2 (crossguid-0.2.2-r01-pc4-1) | 2026-09-27*
