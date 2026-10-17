# 遗留 zip 内部路径分隔符不一致：zipfile 严格校验拒绝 + conan tools.unzip 静默丢源

> 草稿（DRAFT）— 同 stem 配对：`knowledge/drafts/DRAFT-csstidy-1.4-zip-backslash-source-drop.kv`
> 来源：csstidy 1.4 适配（【知识库扩展】），2026-09-18

## 问题

官方 `csstidy-source-1.4.zip`（2007 年 Windows 工具制作，SourceForge 发布）的 zip 内部条目名
不一致：**central directory 用反斜杠**（`csstidy\background.cpp`），**local file header 用正斜杠**
（`csstidy/background.cpp`）。导致两条工具链路径同时失效：

1. **Python 3.11.4+ zipfile 严格校验拒绝读取**（CVE 加固）：
   `zf.read('csstidy\background.cpp')` 直接抛
   `BadZipFile: File name in directory 'csstidy\background.cpp' and header b'csstidy/background.cpp' differ.`
2. **conan tools.unzip 静默丢弃**：对名称校验失败的条目逐条跳过且**不报错**，
   实测仅解出 9 个根级文件，全部 33 个 `csstidy/*` 源文件（含 14 个 .cpp）丢失；
   源码树残缺，构建必然失败且错误信息指向不明确。

## 根因

zip 规范中每个条目有两处名称记录：local file header 与 central directory。正常 zip 两者一致；
本归档由 Windows 工具生成，local header 写正斜杠、central directory 写反斜杠，两者不一致。
Python 3.11.4+（CVE-2023-45803 系列加固）在读取条目时比对两者，不一致即抛 BadZipFile；
conan 的 `tools.unzip` 实现对该类条目静默跳过（无异常、无警告），造成"解压成功但源缺失"。

## 方案（容错解压）

配方 `source()` 分两步：

1. **下载并校验**：用 `tools.download(self, url=..., filename=archive, sha256=...)`，
   按 conandata.yml 的官方 URL + 官方 SHA-256 校验（R39/PF7 合规，不引入 file:// 或镜像）。
2. **容错解压**：不要用 `tools.get()`（其内部 unzip 会静默丢源），自写解压循环：

```python
with zipfile.ZipFile(archive) as zf:
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")          # 规范化路径分隔符
        entry = zipfile.ZipInfo(name, date_time=info.date_time)
        # 从原条目拷贝全部字段（关键：header_offset/CRC/compress_size/file_size/flag_bits 等）
        for attr in ("compress_type", "comment", "extra", "create_system", "create_version",
                     "extract_version", "flag_bits", "volume", "internal_attr",
                     "external_attr", "header_offset", "CRC", "compress_size", "file_size"):
            setattr(entry, attr, getattr(info, attr))
        data = zf.open(entry).read()                     # 必须用重建的 ZipInfo 打开
        target = os.path.join(dest, *name.split("/"))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as fh:
            fh.write(data)
```

关键点：`zf.read(info.filename)` / `zf.open(info)` 会被严格校验拒绝，必须用
**重建的规范化 ZipInfo** 调用 `zf.open(entry)`，使 local header 名称与 entry.filename 一致，
绕过比对检查。

## 验证

- 容错解压后 42/42 条目全部解出，14 个 .cpp 齐全；
- 与系统 `unzip` 命令解压结果逐字节一致（42 个文件 SHA-256 全等，CONTENT_IDENTICAL=True）；
- `conan create`（G2）PASS；W3 本地 CI：L0 pass（含结构/门禁）、L1e 破坏性反向验证
  （移走 bin/ 后测试失败，证明 test_package 真实依赖产物）、L5 产物基线 pass；
- 官方归档 SHA-256 与 FreshPorts distinfo 记录一致（3295977b…132cd）。

## 适用边界

- **适用**：2007 年前后 SourceForge/GNU 时代 Windows 制作的 zip；Python 3.11.4+ /
  Conan 2.32；任何"解压后源文件缺失但无报错"或 `BadZipFile: ... and header ... differ` 场景。
- **反例（不适用）**：
  - codeload GitHub `tar.gz/refs/tags` basename 误判为 zip（根因不同 → E276，用 `filename=` 解决）；
  - 系统缺 `unzip` 二进制（E390）；
  - 资源型数据包质量门禁不适配（E255）；
  - 正常结构 zip（local/central 名称一致）无需容错解压，直接 tools.get。
- **限制**：方案依赖 Python zipfile 可列出 central directory（infolist 正常）；
  对加密 zip 或损坏条目仍需按常规处理。

## 关系

- similar_to: E276（BadZipFile 族）、E255（BadZipFile 症状关键词）、E421（SourceForge 真实路径定位）
- caused_by: 2007-era Windows zip 工具制作不规范（central/local 名称分隔符不一致）
- prerequisite_of: 无
- conflicts_with: 无
