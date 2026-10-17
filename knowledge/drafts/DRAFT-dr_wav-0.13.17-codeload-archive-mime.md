# DRAFT: Conan get() 对 codeload tar.gz 归档 Content-Type/文件名识别误判（dr_wav 0.13.17 确认实例）

> **状态**: 草稿（未审核、未合入正式知识库）
> **查重**: 同一问题已有正式条目 **E276**（`BadZipFile: File is not a zip file|Uncompressing <name> to .|codeload.github.com/.../tar.gz/refs/tags/vX.Y.Z`，修复=显式 `filename=`）。本草稿为 **dr_wav 0.13.17 第二次真实确认实例**，交叉引用 E276，补充官方归档 SHA-256、实际命令/退出码/日志路径，不新增知识编号、不做正式知识库写入。

## 问题签名

- 错误日志：`ERROR: dr_wav/0.13.17: Error in source() method ... BadZipFile: File is not a zip file`
- 触发工具/阶段：Conan `source()`（`get()` 下载并解包）
- 匹配 E276 的 `error_signature`：`BadZipFile: File is not a zip file|codeload.github.com/.../tar.gz/refs/tags/...`

## 根因（与 E276 一致）

Conan `get()` 默认按 `os.path.basename(url)` 推断下载文件名，再按扩展名选择解压算法；codeload.github.com 的官方 tag archive URL 形如
`https://codeload.github.com/<owner>/<repo>/tar.gz/refs/tags/<tag>`，basename 为无扩展名的 `<tag>`（如 `wav-0.13.17`），导致 `unzip()` 误判为 zip 并抛 `BadZipFile: File is not a zip file`。实际下载体是合法 gzip tar（`tar xzf` 可解、SHA-256 校验通过），非配方或补丁错误。

## 本库真实证据（dr_wav 0.13.17, mackron/dr_libs）

| 项目 | 值 |
|------|-----|
| 官方仓库 | https://github.com/mackron/dr_libs |
| 官方标签 | `wav-0.13.17`（commit `660795b2834aebb2217c9849d668b6e4bd4ef810`） |
| 官方 tag archive URL | `https://codeload.github.com/mackron/dr_libs/tar.gz/refs/tags/wav-0.13.17` |
| 归档 SHA-256 | `6a06744f9e961e8417f1ce9ee0d884cc8f00108d1a08845ced7f8696847ff8ec` |
| 归档内 dr_wav.h SHA-256 | `9948d5343a879d4644693b2832005e9fbbb7581929223a1775cbde559a835388`（与单文件核验一致） |
| 归档格式 | tar.gz（gzip，518,811 字节；`curl` 响应 Content-Type 与 `.tar.gz` 实际格式不一致，Conan 无法按 URL 正确识别） |

### 现象复现（修复前）

```bash
cd archives/d/dr_wav/0.13.17
conan create . -pr ohos-aarch64 -r=ohpcd
# ↓ 报错
# dr_wav/0.13.17: Sources correctly downloaded from https://codeload.github.com/mackron/dr_libs/tar.gz/refs/tags/wav-0.13.17
# dr_wav/0.13.17: Uncompressing wav-0.13.17 to .
# ERROR: dr_wav/0.13.17: Error in source() method, line 53
#   get(self, **self.conan_data["sources"][self.version], strip_root=True)
#   BadZipFile: File is not a zip file
```

### 解决方案（推荐方案，与 E276 一致）

在 `source()` 的 `get()` 调用显式传 `filename='<软件>-<版本>.tar.gz'`，让 Conan 按扩展名走 tar.gz 解压器：

```python
def source(self):
    # codeload 响应 Content-Type 为 application/zip，需显式 filename 后缀
    # 让 unzip 按 .tar.gz 识别（否则被误判为 zip 抛 BadZipFile）。
    src = dict(self.conan_data["sources"][self.version])
    src["filename"] = "wav-0.13.17.tar.gz"
    get(self, **src, strip_root=True)
```

URL 保持官方源（R39）不变，conandata.yml 的 sha256 不变。

### 复验（修复后）

```bash
python3 -m py_compile conanfile.py          # exit 0
conan create . -pr ohos-aarch64 -r=ohpcd   # exit 0 → test_package 7/7 PASS
```

- conan create 日志：`archives/d/dr_wav/0.13.17/reports/conan-create.log`
- conan-verify（含 G2 clean build）：`python3 scripts/ohc-run.py conan-verify dr_wav 0.13.17 --profile ohos-aarch64` → exit 0，G1–G4 全部 PASS

## 适用边界

- **适用**：所有 conanfile.py `source()` 用 `get()` 拉取 codeload.github.com 官方 tag archive（`.tar.gz` 形态）的配方。
- **不适用**：
  - raw 单文件 URL（无归档，`download()` 场景）
  - GitHub release asset 中扩展名干净的 `.tar.gz`（basename 非空可被正确识别）
  - 非 codeload 源的普通 `.tar.gz`（如 `github.com/<owner>/<repo>/archive/refs/tags/<tag>.tar.gz`，文件名自带扩展名）
- 本库归档来源已核验合规：官方 tag archive（非 raw 单文件、非镜像），R03 起固定使用。

## 恢复条件 / 备注

- 若 Conan 未来按 Content-Type 而非文件名推断解压算法，本变通可简化为普通 `get()`；当下版本（2.29.1）仍需 `filename=`。
- 当前库 conanfile.py 保留显式 `filename` 及注释说明，供审计追溯。

## 关联

- 查重命中：`knowledge/graph/E276.kv` + `knowledge/doc/E276.md`（正式条目，goblinrs 维护，2026-07-30）
- 本草稿 = E276 的第二个真实确认实例（dr_wav 0.13.17 / mackron/dr_libs），增量证据为官方归档 SHA-256 与复验命令/退出码/日志路径。