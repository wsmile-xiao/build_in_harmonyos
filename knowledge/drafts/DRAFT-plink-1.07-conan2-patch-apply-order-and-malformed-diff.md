# DRAFT: Conan 2 里补丁「日志说打了、源码却没变」的两种成因

- **package**: plink/1.07（PLINK 1.07 适配）
- **context**: 需要给上游源码打补丁的 Conan 2 配方，补丁挂在
  `patches/` 并由 `export_conandata_patches` + `apply_conandata_patches` 消费
- **verdict**: 两种成因都会让补丁对编译零作用，且日志都显示「已打补丁」

## error_signature

**成因 1 —— 调用位置错**（日志完全正常，看不出任何异常）：

```
plink/1.07: Apply patch (compat): <patch_description>
...
sets.cpp:771:37: error: redefinition of 'i' with a different type:
    'vector<Individual *>::iterator' (aka '__wrap_iter<Individual **>') vs 'int'
```

**成因 2 —— diff 畸形**（日志同样只有一行 `Apply patch`）：

```
plink/1.07: Apply patch (compat): <patch_description>
plink/1.07: WARN: ...0001-xxx.patch: file 1/3:	 b'sets.cpp'
plink/1.07: WARN: ...0001-xxx.patch:  hunk no.1 doesn't match source file at line 778
```
（成因 2 的这一类 WARN 只在「真不匹配」时出现；**完全无 WARN 也不代表打上了**，
因为解析器可能整段跳过。）

## root_cause

1. **Conan 2 的执行顺序是 `source()` → 复制源码到构建树 → `build()`。**
   `apply_conandata_patches()` 永远作用于 `self.source_folder`。写在 `build()`
   里时它改的是导出树 `p/<recipe_id>/s/<source>`，而 `make` 编的是刚复制过去的、
   **未打补丁**的 `p/b/<pkg_id>/b/<build>`。
   特别注意：`folders.source` 与 `folders.build` **同名不等于同一物理目录**——
   前者在 `p/<rid>/s` 下，后者在 `p/b/<pid>/b` 下，`basic_layout` 下必然不同。

2. **手写 unified diff 时描述段末尾缺一个换行**，`cat header diff > patch` 会把
   散文最后一行和 `--- a/<file>` 粘成一行：

   ```
   byte-identical.--- a/sets.cpp
   ```

   于是 `^--- a/sets.cpp` 这一行**根本不存在**。GNU `patch` 靠 `+++` 和 `@@`
   仍能打上（我手工 `patch -p1` 成功、`i_iter` 出现 4 处），但 Conan 的解析器
   找不到成对的文件行，**整段静默跳过**。这正是「GNU patch 能过、Conan 静默跳过」
   让人怀疑人生的组合。

## rec_approach

- **补丁一律写在 `source()` 里。** 这是唯一正确的位置（仓内 `jpegoptim`、`jailkit`
  等配方同此）。`build()` 里只做编译/打包。
- **补丁文件一律机器生成，不手写：**

  ```bash
  cat header.txt > 0001-xxx.patch
  printf '\n' >> 0001-xxx.patch          # ← 关键：保证描述段以换行结束
  for f in sets.cpp elf.cpp idhelp.cpp; do
    diff -u --label "a/$f" --label "b/$f" "a/$f" "b/$f" >> 0001-xxx.patch || true
  done
  ```

  `--label` 同时消掉了 diff 里的时间戳，让补丁可复现。
- **生成后做结构校验**（比事后 debug 便宜得多）：

  ```bash
  for f in sets.cpp elf.cpp idhelp.cpp; do
    n=$(grep -cE "^--- a/$f\$" 0001-xxx.patch)
    m=$(grep -cE "^\+\+\+ b/$f\$" 0001-xxx.patch)
    [ "$n" -gt 0 ] && [ "$m" -gt 0 ] || echo "MALFORMED: $f"
  done
  ```

- **落地验证不要只看日志**：在解包后的源码目录里 grep 补丁引入的标识串
  （本例 `grep -c i_iter sets.cpp` 应为 4），确认字节真的变了。
- **in-tree Makefile 项目**再叠一条：`self.folders.source = "src"` /
  `self.folders.build = "src"`，并让 `make` 跑在 `self.build_folder`——
  那棵树是「已打补丁」的复制品。

## forbid

| 模式 | 后果 |
|---|---|
| 在 `build()` 里 `apply_conandata_patches()` | 改导出树、编复制品，补丁零作用；报错与未打补丁时逐字相同 |
| 手写 unified diff / 描述段末尾无换行 | 缺 `---` 行，Conan 静默跳过；且与 GNU patch 行为不一致，无法互验 |
| 只凭日志 `Apply patch` 就认为补丁生效 | 该行只说明「开始处理」，不代表有 hunk 被应用 |

## 附带发现（同源误判高发）

1. **CI 的 `Pre-download: extracting source URLs from conandata.yml` 会把 conandata 里
   任何 `http(s)://` 串当源码地址去下载。** 注释里写
   `# Bug-Closed: http://bugs.debian.org/667325` 会被当成第二个待下载文件，
   真的去抓一张 HTML 页，日志出现 `[ok] 667325），仅重命名... (10KB) via mirror 1`
   这种怪行。conandata.yml 的注释里不要留裸 URL，出处写进 `patches/` 文件头或 notes.md。
2. 该步骤会把 conandata.yml 临时改写成 `file://` 列表再"还原"。**别信还原声明**，
   一律 `git diff` 判定（T006/T011/T025）。
3. `conan create` 会在 `test_package/` 留下 `conanbuild.sh` / `conanrun.sh` /
   `deactivate_*.sh`；提交前必须删，否则 JC4 临时构建产物检测会拦。
