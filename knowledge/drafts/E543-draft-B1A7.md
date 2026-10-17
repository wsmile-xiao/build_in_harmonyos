# E543 — CI pre-download 把 conandata.yml 注释里的 URL 当成源码 URL，子串替换污染真实源码 URL

## 错误特征

`conan create` / 本地 W3（`finish` step 5）在 `source()` 阶段失败，日志形如：

```
cronic/v3: WARN: network: Error downloading file https://gh-proxy.com/file:///.../predl_cache/<hash>_cronic/archive/<commit>.tar.gz: ... 403: Forbidden.
ERROR: cronic/v3: Error in source() method, line 65
	get(self, **self.conan_data["sources"], strip_root=True)
	NotADirectoryError: [Errno 20] Not a directory: '/.../.build-cache/predl_cache/<hash>_cronic/archive/<commit>.tar.gz'
```

并且预下载日志里出现意料之外的下载条目（文件名不是源码 tarball，例如 `cronic`）：

```
[step] Pre-download: extracting source URLs from conandata.yml...
  found 3 source URL(s)          ← 期望 1
  [try 1/2.1/3] cronic ← https://gh-proxy.com/https://github.com/justincase/cronic ...
```

## 触发条件

- 构建系统：任意（此问题与语言无关，纯 CI/配方数据链路）
- 阶段：configuration（`conan create` 的 source/预下载阶段）
- 配方 `conandata.yml` 的**注释**里写有裸 `http(s)://` URL

## 根因分析

`ci/conan/build_and_test.sh` 的 **Pre-download** 步骤用正则扫描 `conandata.yml` **整个文件**（包含注释行）提取所有 URL：

```python
url_pattern = r'(?:^|\s)(?:url:?\s*)?["\']?-?\s*(https?://[^\s"\']+)'
urls = list(dict.fromkeys(re.findall(url_pattern, raw, re.MULTILINE)))
```

下载后逐条做**子串替换**，把远程 URL 换成 `file://` 本地路径：

```python
for url, local_path in downloaded.items():
    content = content.replace(url, f'file://{local_path}')
```

若注释里写有仓库根 URL（如 `# Upstream: https://github.com/owner/repo`），它会被并入 `downloaded`。当这个注释 URL 是真实源码 URL 的**前缀子串**时（本例 `https://github.com/justincase/cronic` 是 `https://github.com/justincase/cronic/archive/<commit>.tar.gz` 的前缀），先替换短 URL 会把长 URL 改写成：

```
https://gh-proxy.com/file:///.../predl_cache/<hash>_cronic/cronic/archive/<commit>.tar.gz
```

该 URL 既不可解析（`gh-proxy.com/file:///...` 403）又会让 conan 的文件下载器落到一个"被当作目录的文件路径"上，最终抛 `NotADirectoryError`。

## 解决方案

### 推荐方案

`conandata.yml` 注释中**不要出现裸 `http(s)://` URL**。需要指向上游时用无 scheme 的写法（`github.com/owner/repo`、`habilis.net/cronic`），全文件只保留 `sources.url` 一个真实 URL。

验证（应为 1）：

```bash
python3 -c "import re;raw=open('archives/<l>/<pkg>/<ver>/conandata.yml').read();print(len(re.findall(r'https?://',raw)))"
# 或复算预下载提取结果：
python3 -c "import re;raw=open('archives/<l>/<pkg>/<ver>/conandata.yml').read();print(re.findall(r'(?:^|\s)(?:url:?\s*)?[\"']?-?\s*(https?://[^\s\"']+)',raw,re.M))"
```

### 禁止做法

- ❌ 为了让注释"可点击"而在 `conandata.yml` 里写完整 `https://…` URL —— 会被预下载当源码下载并参与子串替换。
- ❌ 把注释 URL 写成 `sources.url` 的前缀（即便有 scheme 也一样中招）。

### 回退方案

若确需保留注释 URL，务必使其**不是** `sources.url` 的子串（例如指向 README 全文页而非仓库根），或直接去掉 scheme。

## 验证

```bash
# 复现（注释含源码 URL 前缀时）
grep -n 'https\?://' archives/<l>/<pkg>/<ver>/conandata.yml   # 出现 >1 行即风险
# 修复后
python3 scripts/ohc-run.py finish <pkg> <ver> built          # W3 通过
```

## 关联条目

- 同源机制：CI mirror-fallback 会把单值 `url:` 改写成 `[gh-proxy, 原url]` 列表；本地 W3 结束时可能未还原，提交前须 `git checkout -- conandata.yml` 还原为官方单 URL。
- 相关条目：待主编指派（本条目为草稿）。
