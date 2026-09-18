# DRAFT-8960-raqm-0.11.0-conandata-comment-url-predl-pollution — conandata.yml 注释里的 https URL 被 CI predownload 提取并污染源码 URL 替换

- 触发事件：raqm 0.11.0 适配，W3/CI 的 Pre-download 步骤把注释 URL 当源码下载并 file:// 替换进 conandata
- 路径：Path B（知识库扩展）
- 编号：DRAFT-8960

## 现象

W3 本地 CI / 远端 CI 的 conan create 阶段：

```
ERROR: raqm/0.11.0: Error in source() method
NotADirectoryError: [Errno 20] Not a directory: '.../predl_cache/b4739ed2_libraqm/archive/refs/tags/v0.11.0.tar.gz'
```

predl 日志显示 `[ok] libraqm (30KB)`——一个 HTML 仓库页被当 tarball 下载成功。

## 根因

`ci/conan/build_and_test.sh` 的 Pre-download 用正则从 conandata.yml
**全文**提取 https URL——**注释行也在提取范围**：

```yaml
# Upstream: https://github.com/HOST-Oman/libraqm (tag v0.11.0)   ← 注释 URL
sources:
  url: "https://github.com/HOST-Oman/libraqm/archive/refs/tags/v0.11.0.tar.gz"
```

注释 URL（无 `/archive/...` 尾段）是真源码 URL 的**前缀子串**：

1. predl 下载注释 URL → GitHub 返回 31KB 仓库 HTML 页（>100 字节判成功）；
2. `content.replace(注释URL, file://...)` 把 conandata 里所有 URL 中段污染；
3. conan 拿到 `file:///.../b4739ed2_libraqm/archive/refs/tags/v0.11.0.tar.gz`
   畸形路径 → `NotADirectoryError`。

与 E333（PyPI 连字符截断）同族（都是 predl URL 提取缺陷）但根因不同：
E333 是正则字符类截断 URL 尾段；本条是**注释 URL 作为前缀子串污染**。

## 可复用处置

conandata.yml 注释里**不写任何 https:// URL**：

```yaml
# conandata.yml — raqm 0.11.0
# Upstream: HOST-Oman/libraqm tag v0.11.0 (commit 08ee153...)
sources:
  url: "https://github.com/HOST-Oman/libraqm/archive/refs/tags/v0.11.0.tar.gz"
  sha256: "..."
```

主页由 conanfile.py 的 `homepage` 字段承载。自查：

```bash
grep -E '^#.*https?://' conandata.yml   # 期望无输出
```

改后必须 `rm -rf .build-cache/predl_cache`（坏 HTML 缓存会以 `[cached]` 复活）。

## 验证

raqm 0.11.0（feat/raqm-0.11.0 分支）：
- 修复前：W3 三连败，conan 报错 URL 为 `file://...libraqm/archive/...`
  拼接体（前缀替换污染直接证据）；
- 同款正则对含注释 conandata 提取出 3 个 URL；删注释后仅 1 个正确源码 URL；
- 修复后 W3 全绿（L0/L1/L4/L5 pass，meson test 51/51）。

## 边界

治本在 CI 侧（predl 只解析 YAML 数据段 / replace 精确匹配整行）；
本条是配方侧自防御规范，CI 修复后仍无害。
