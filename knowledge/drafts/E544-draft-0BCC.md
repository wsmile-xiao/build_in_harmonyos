# E544: finish 的 refresh-patch --auto 改名并孤立 conandata 引用的手写补丁 → export_sources 报 Patch file does not exist

## 错误特征
```
ERROR: digestpp/1.0.0@ohpcd/stable: Error in export_sources() method, line 23
    export_conandata_patches(self)
    ConanException: Patch file does not exist: '.../patches/0001-fix-xxx.patch'
```
触发前 patches/ 目录被悄然改名+备份：
```
patches/0001-fix-xxx.patch    → patches/0001-algorithm-detail-xxx.patch
                               + patches/.patch-backup-<ts>/0001-fix-xxx.patch
```

## 触发条件
- 构建系统: conan 2（本仓 ohc-run 工作流）
- 阶段: `finish` 步骤 1（refresh-patch --auto）之后、`conan create` 的
  `export_sources()` 阶段（G2 门禁）
- 前置条件:
  - conandata.yml 的 `patches."<ver>"` 声明了 `patch_file`
  - 补丁是手写/多文件 hunk，且 `.work` 源码树与 `.orig` 存在差异
    （或只同步了部分文件的改动）

## 根因分析
`refresh-patch --auto`（finish step 1）以 `.work` 与 `.orig` 的源码差异为准重建补丁：
- 它按“被修改源文件路径”重命名补丁（`0001-<文件路径>.patch`），并把旧补丁移入
  `.patch-backup-<时间戳>/`。
- 手写补丁如果只在 patches/ 中、未在 `.work` 源码树中落地（或只落地了部分文件），
  工具重建产物与 conandata 的 `patch_file` 引用脱节 → 导出阶段报文件不存在，
  conan create 在 source()/export 阶段失败（G2 FAIL）。

## 推荐方案
**方法**: work-tree-pristine-when-patch-only

**说明**:
1. 若修复只通过补丁文件交付：保持 `.work` 与 `.orig` 完全一致
   （`diff -rq <orig> <work>` 为空），refresh-patch 找不到源码差异即为 no-op，
   不再改写补丁文件名。
2. 若确实要在 `.work` 改源码：先落地全部改动，再运行 refresh-patch --auto
   生成规范补丁，让 conandata 引用工具产物名。
3. 被孤立后恢复：从 `.patch-backup-<ts>/` 恢复 conandata 引用的规范补丁文件名，
   删除自动生成改名物与备份目录，保持补丁 hunk 完整（本案例须双文件 hunk：
   functions.hpp + lsh_provider.hpp）。

## 验证/命令
```
diff -rq <orig> <work>                                  # 应无差异（补丁唯一载体时）
rm -rf patches/.patch-backup-* patches/<auto-renamed>.patch
conan create . -pr:h=ci/conan/profiles/ohos-aarch64     # G2 PASS，安装含补丁标记
```

## 适用范围 / 边界 / 反例
- 适用：本仓所有在 conandata.yml 声明 patch_file、且补丁不经过 refresh-patch
  生成路径的库配方。
- 边界：补丁由 refresh-patch 自己从 `.work` 差异生成时（R7 常规路径）不会命中；
  只有 conandata 引用与工具重命名不一致时才失败。
- 反例：改 conandata 引用工具生成名而没有核对 hunk 内容，可能只剩单文件 hunk
  而丢失另一文件的修复（本案例 functions.hpp 的 rotate_left 修复就曾被丢弃）。

## 七轴查重与关系
- exact/causal_duplicate: false；trigger_overlap: true（与 E254/E484 同在
  refresh-patch 环节）；solution_overlap: 部分（同属 patch 管线一致性）；
  组合/边界新颖性: true（“conandata 引用被工具改名孤立 → export_sources 失败”）
- similar_to: E254, E484, E282, E066

*来源: digestpp 1.0.0 适配（task digestpp-1.0.0-r01-pc4-7-20260928T013018Z）*