# E430-draft — Conan copy() 默认 keep_path=True 造成 bin/bin、lib/lib 嵌套目录且软链悬空

> Contributor: pc4-5 | Status: **DRAFT** | Updated: 2026-09-27 | Severity: 2
> Source: `feat/g810-led-0.4.3` 适配 HarmonyOS PC（任务 g810-led-0.4.3-r01-pc4-5）
> 对应：`knowledge/drafts/E430-draft-A7AC.kv`

## 错误特征
```
ld.lld: error: unable to find library -lg810-led
```
（conan create 的 test_package 消费者链接阶段）
包内实际布局出现嵌套：
```
pkg/bin/bin/g810-led
pkg/lib/lib/libg810-led.so.0.4.3
pkg/lib/libg810-led.so -> libg810-led.so.0.4.3   (悬空：目标在 lib/lib/ 下)
```

## 触发条件
- 构建系统: raw GNU makefile（产物自带 `bin/`、`lib/` 前缀目录）
- 阶段: conan package()（copy 产物进 package_folder）
- 配方写法: `copy(self, "bin/<prog>", src, dst=os.path.join(self.package_folder, "bin"))`
  / `copy(self, "lib/lib<name>.so.<ver>", src, dst=.../lib)`（未显式 keep_path=False）

## 根因分析
Conan `conan.tools.files.copy()` 默认 `keep_path=True`：按 pattern 匹配到的文件
会**保留相对 src 的子路径**复制。makefile 产物本身带 `bin/`、`lib/` 前缀，pattern
又含子路径（`bin/g810-led`），于是目标目录再叠一层 → `pkg/bin/bin/`、`pkg/lib/lib/`。
同时官方 makefile 生成的 `libg810-led.so -> libg810-led.so.0.4.3` 软链被 copy 以
文件形式/悬空链复制，目标文件却被嵌套到 `lib/lib/`，消费者 `-L{pkg}/lib -lg810-led`
报 `unable to find library`。conan create 主包不报错（package() 无编译），
缺陷直到 test_package 链接才暴露。

## 解决方案

### 推荐方案
拷贝自带 `bin/`、`lib/` 前缀的 makefile 产物时显式 `keep_path=False`，软链在
package() 中显式重建：
```python
copy(self, "bin/g810-led", src, os.path.join(self.package_folder, "bin"), keep_path=False)
copy(self, "lib/libg810-led.so.0.4.3", src, os.path.join(self.package_folder, "lib"), keep_path=False)
os.symlink("libg810-led.so.0.4.3",
           os.path.join(self.package_folder, "lib", "libg810-led.so"))
```

### 禁止做法
- ❌ 保留默认 keep_path=True 拷贝自带 bin//lib/ 前缀的产物（嵌套 + 软链悬空）
- ❌ 依赖 conan copy 保留官方 makefile 生成的软链（copy 按文件复制，不保证链接关系）

## 验证（本任务实测）
```bash
# 修复前（keep_path=True）：test_package 链接失败
ld.lld: error: unable to find library -lg810-led

# 修复后（keep_path=False + 显式 os.symlink）：conan-verify 8 门禁全 PASS
#   G2: conan create PASS（含 test_package 消费者 ./consumer + cli_smoke.sh）
# 包内布局核对：
ls -la pkg/lib/   # libg810-led.so -> libg810-led.so.0.4.3（可解析）+ 真实文件同目录
ls pkg/bin/       # g810-led（无 bin/bin 嵌套）
```

## 适用边界
- 适用：raw makefile / 产物自带前缀目录的 conan package() 拷贝
- 不适用：无前缀单层产物的 header-only 复制（如 `*.hpp` 平铺）、
  依赖包资源物化场景（见 E362，那是 symlink 归属/物化语义问题，非嵌套布局问题）

## 查重差异（七轴）
| 轴 | 结论 |
|---|---|
| exact_duplicate | false（无同文条目） |
| causal_duplicate | false（E362 根因=依赖资源物化/禁链文件系统；本条=keep_path 嵌套布局） |
| trigger_overlap | 部分（E362/DRAFT-E720 都用到 keep_path=False，但触发面不同：本条=前缀产物嵌套） |
| solution_overlap | 部分（同为 keep_path=False 手段；本条额外要求显式重建软链） |
| combination_novelty | true（"自带前缀产物 + keep_path 默认值 + 悬空软链"组合未被既有条目覆盖） |
| boundary_novelty | true（明确了与 E362 的边界：物化语义 vs 布局嵌套） |
| test_migration_novelty | true（本任务 test_package 链接失败→修复→8 门禁 PASS 全链路可复现） |

## 关联条目
- 相关: E392（raw makefile 配方三陷阱：dict conf / cwd / BadZipFile）、E362（依赖资源物化）
