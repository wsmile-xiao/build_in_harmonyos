# DRAFT — conandata.yml 注释行裸 URL 被 W3 pre-download 正则误抓，且为真实 URL 字符串前缀导致 replace() 污染

> 状态: 草稿（基于 status-value-lite 1.1.0 R01 真实证据，待查重/提升）。
> 依据: SKILL §3 W3（build_and_test.sh pre-download）+ 知识 E333/E415 边界补充。

## 真实问题（场景）

在 `finish`（W3 本地 CI 模拟）阶段，`ci/conan/build_and_test.sh` 的 pre-download 脚本
用正则 `(?:^|\s)(?:url:?\s*)?["\']?-?\s*(https?://[^\s"\']+)` 扫描 conandata.yml 里的
所有 URL（含注释行），把命中项逐一 curl 下载到 `.build-cache/predl_cache/{md5hash}_{文件名}`，
**只要 body 大于 100 字节就判定"下载成功"**，然后用 `content.replace(url, f'file://{local_path}')`
把 conandata.yml 里的该 URL 原地改写为 file:// 本地路径。

当 conandata.yml 顶部出现**裸 URL 注释行**（如 `# 官方源: https://github.com/nonstd-lite/status-value-lite`），
且该注释 URL 恰好是**真实 sources URL 的字符串前缀**（真实 URL =
`https://github.com/nonstd-lite/status-value-lite/archive/refs/tags/v1.1.0.tar.gz`）时：

1. 注释 URL 被正则误抓为一个下载源；curl 经 gh-proxy 返回 403 页面（5086 字节 > 100B）→ 误判成功，
   写入 `predl_cache/6d0177e3_status-value-lite`。
2. `str.replace(注释URL, file://...)` 是**前缀匹配替换**：因为注释 URL 是真实 URL 的前缀，
   真实 URL 也被替换成 `file://.../predl_cache/6d0177e3_status-value-lite/archive/refs/tags/v1.1.0.tar.gz`。
3. conan `get()` 打开该 file:// 路径：`6d0177e3_status-value-lite` 是**文件**而非目录 →
   `NotADirectoryError: [Errno 20] Not a directory`，W3 的 conan create 失败。

## 根因

1. **pre-download 正则不区分注释/代码**：只要以空白或 `url:` 前缀开头就抓取，注释行内的裸 URL 同样命中。
2. **403/非 200 响应体 >100B 被误判成功**：curl 拿到的错误页被视为有效下载（与 E333 同源缺陷）。
3. **replace() 前缀污染**：注释 URL 若为真实 URL 的字符串前缀，替换会把真实 URL 一起污染
   （本候选新增机制，E333 的连字符截断与 E415 的镜像恢复均不覆盖）。

## 方案（配方侧规避，不改共享脚本）

1. **conandata.yml 注释行禁止写裸 URL**：描述性注释可以写仓库名/版本，但不要出现可被
   正则匹配的 `https://...` 裸 URL；确需标注来源时写成 `https://... （勿写裸 URL）` 之外
   的形式（如拆成 `github.com/nonstd-lite/status-value-lite` 省略 `https://`），杜绝误抓。
2. **恢复官方形态**：W3 失败后核验 conandata.yml 是否被改写为 file:// 路径
   （`grep -nE 'file://|predl_cache' conandata.yml`），有则恢复为官方 URL（sha256 不变）。
3. **重跑**：清理后重新 `finish <pkg> <ver> built`，确认 W3 通过、`.ci-result.json` exit_code=0。

## 验证

```bash
# 失败复现（污染前）：
grep -nE 'file://|predl_cache' archives/s/status-value-lite/1.1.0/conandata.yml
# 修复后（无 file:///无 predl_cache/无裸 URL 注释）：
grep -nE 'file://|predl_cache' archives/s/status-value-lite/1.1.0/conandata.yml || echo CLEAN
python3 scripts/ohc-run.py finish status-value-lite 1.1.0 built   # EXIT_CODE=0, W3 PASS
```

实测：删除注释 URL 行后重跑 finish → W3 本地 CI 通过（`.ci-result.json` exit_code=0、
JC_RESULT=pass），与 E415 的"CI 后恢复"互补（此处是"源头不写裸注释 URL"预防 + 触发机制识别）。

## 查重差异

- **E333**（pre-download 连字符截断 → FileNotFoundError）：同为 pre-download 误判下载成功，
  但 E333 是正则字符类排除 `-` 截断 PyPI 文件名；本候选是注释行 URL 被误抓 + **字符串前缀
  replace 污染真实 URL** → NotADirectoryError。机制不同、修复不同（E333 改 URL 形态，
  本候选禁止裸 URL 注释）。部分思维重叠，机制互补。
- **E415**（gh-proxy 镜像改写后需恢复 conandata）：E415 讲"CI 后事务性恢复官方形态"；
  本候选讲"改写**过程中**注释 URL 前缀污染"的触发机制与**源头预防**。互补不重叠。
- **DRAFT-lexy-E017-residual-cleanup**：讲 E017 生成的 .orig/.bak/.lock 残留清理；
  不覆盖注释 URL 前缀 replace 污染。不重叠。

## 适用范围

所有 conandata.yml（或任何被 CI pre-download 正则扫描的配方文件）中：
1. 注释行含裸 `https://` URL；且
2. 该 URL 是真实 sources URL 的字符串前缀
的三方库。规避方法：注释不写裸 URL / 前缀不重叠 / 改 URL 形态。