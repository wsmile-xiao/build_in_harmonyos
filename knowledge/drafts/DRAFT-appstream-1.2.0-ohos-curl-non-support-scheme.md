# DRAFT-appstream-1.2.0-ohos-curl-non-support-scheme — libcurl 无 SSL 时 URL 格式校验误报（CURLU_NON_SUPPORT_SCHEME）

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: medium (2) | **Category**: build / dependency / curl / validation
> **Audience**: 使用 libcurl URL API 做格式校验、但构建仓 libcurl 未编译 SSL 的校验器/解析器

## 触发（trigger）

- appstream 1.2.0（archives/a/appstream/1.2.0，R03）：ohpcd libcurl/8.5.0 未启用 SSL
  （`curl_version_info` protocols 无 https），as-validator 对 `https://` URL 报
  "URL format is invalid"。

## 症状（symptom）

```
as-validator 校验 https URL → "URL format is invalid"（CURLUE_BAD_SCHEME）
```

URL 格式合法但被误报为格式错误；可达性（check_urls）与格式校验被混为一谈。

## 机制（root cause）

`as_curl_is_url()` 用 `curl_url_set(cu, CURLUPART_URL, url, 0)` 做格式校验；
libcurl 未编译某 scheme 的协议处理器时，curl_url_set 对该 scheme 返回
CURLUE_BAD_SCHEME——格式解析与协议可用性耦合。格式校验本应只关心 URL 语法。

## 修复（fix）

`curl_url_set(cu, CURLUPART_URL, url, CURLU_NON_SUPPORT_SCHEME)`：放行非支持 scheme
的 URL 格式校验；可达性仍由调用方（priv->check_urls / appstreamcli --no-net）单独控制。
补丁：0006-curl-is-url-non-support-scheme.patch。

## 验证（verification）

- as-validate_metainfo.cli：meson test 1/1 OK（rc=0）
- as-test_validate：7/7 PASS（rc=0）
- 直接运行 `appstreamcli validate --pedantic --no-net` → "Validation was successful."

## 适用边界 / 反例

- 适用：任何"格式校验"类 libcurl URL 用法，且平台 libcurl 缺 scheme 处理器；
- 反例：确需验证 scheme 可达/受支持（如仅允许 http）的场景不可盲目放行。

## 关系

- 查重：grep "curl_url|CURLUE_BAD_SCHEME|URL format is invalid" 在 knowledge/graph/
  无命中；E006/E034 为 SSL 证书错误（不同面）。
- similar_to: []；caused_by: []；prerequisite_of: []；conflicts_with: []

## 证据

- 补丁：archives/a/appstream/1.2.0/patches/0006-curl-is-url-non-support-scheme.patch
- 台账：archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md 候选 9
