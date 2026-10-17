# DRAFT-libexecinfo-20180201-conandata-comment-url-predl-pollution — conandata.yml 注释中的裸 GitHub 仓库 URL 被 W3 pre-download 正则捕获并前缀污染官方 tarball URL

- 触发事件：libexecinfo 20180201 适配，finish W3 本地 CI 首次执行失败
- 路径：Path B（知识库扩展）
- 编号：DRAFT-libexecinfo-20180201-conandata-comment-url-predl-pollution

## 现象

conandata.yml 注释里写了一句 `# Source: https://github.com/resslinux/libexecinfo (official upstream)`，
W3 本地 CI（build_and_test.sh）的 pre-download 阶段把它当成了一个"源码 URL"，
下载回来的是 30KB 的 GitHub 仓库主页 HTML，随后 conan create 报：

```
ERROR: libexecinfo/20180201: Error in source() method, line 62
  NotADirectoryError: [Errno 20] Not a directory:
  '/storage/.../.build-cache/predl_cache/c1cff791_libexecinfo/archive/refs/tags/v20180201.tar.gz'
```

## 根因

1. pre-download 的 url_pattern 正则
   `(?:^|\s)(?:url:?\s*)?["\']?-?\s*(https?://[^\s"\']+)`
   对**注释行**也放开匹配——只要行内出现 `https?://` 就捕获，不校验是否 `url:` 字段。
2. 下载器只判 `size > 100` 就算成功，不校验 tarball 格式：仓库主页 HTML（30KB）
   被当作源码缓存。
3. 改写逻辑用 `content.replace(url, f'file://{local_path}')` 做纯字符串**前缀**替换，
   而裸仓库 URL `https://github.com/resslinux/libexecinfo` 恰好是官方 tarball URL
   `https://github.com/resslinux/libexecinfo/archive/refs/tags/v20180201.tar.gz` 的前缀，
   于是官方 URL 被替换成 `file://.../predl_cache/c1cff791_libexecinfo` + 残留的
   `/archive/refs/tags/v20180201.tar.gz`，把 HTML 文件当目录展开 → NotADirectoryError。

## 可复用处置

1. **预防**：conandata.yml 注释中不写裸仓库 URL。需要注明来源时写完整 tarball
   URL，或纯文本描述且不带 `https://` 字样。
2. **排查口诀**：W3 pre-download 显示 `found N source URL(s)` 且 N 大于 conandata
   实际 `url:` 字段数；或 `[try]` 行末尾文件名是仓库名（`libexecinfo`）而非
   `<tag>.tar.gz` —— 即命中本条。
3. **恢复**：删除 `.build-cache/predl_cache/` 里 `file` 显示为 `UTF-8 text` 的误下载
   文件（`c1cff791_libexecinfo` 这类），把 conandata.yml 的 url 还原为官方完整
   tarball URL，注释去掉裸 URL，重跑 finish/W3。

## 判定要点

- 与 E333（pre-download 正则 `[^\s"'-]+` 截断连字符文件名）同源不同机制：
  E333 是"URL 被截断"，本条是"注释裸 URL 被捕获 + 前缀替换污染"；错误形态
  FileNotFoundError（截断） vs NotADirectoryError（前缀替换）；修复手段完全不同。
- 仅当裸 URL 是官方 tarball URL 的字符串前缀时才必然触发；两者无关时只是多
  下载一个 HTML 文件，不影响 conan create，但仍建议避免。
- 与 JC 扫描模式（full/incremental）无关：pre-download 在任何模式下都执行。

## 实证

- libexecinfo 20180201：conandata.yml 注释去裸 URL + 删除误下载 HTML 缓存后，
  `ohc-run.py finish libexecinfo 20180201 published` 的 W3 本地 CI 100%（1/1）通过，
  `.ci-result.json` exit_code=0，log_sha256=`295e03eb6f2cdfe5b1f7e10495975c47661e41717d3820fc59275ab4b467faad`。
