# DRAFT-aghermann-1.1.2-conandata-local-file-url-leak

conandata.yml 本地 file:// 缓存路径泄漏导致 CI source() FileNotFoundError

## 现象

PR #10748（aghermann 1.1.2）构建 #61218 在 `conan-build-test` 步骤失败，诊断类别"未知"：

```
ERROR: aghermann/1.1.2: Error in source() method, line 69
	get(self, **self.conan_data["sources"], strip_root=True)
FileNotFoundError: [Errno 2] No such file or directory:
  '.../Desktop/build_in_harmonyos/.storage-tmp/wt-aghermann-pr/.build-cache/predl_cache/f8d228e8_aghermann-1.1.2.tar.xz'
```

本地 `build_and_test.sh` 模拟全绿，PR CI 却在 source() 阶段秒败；L1/L2/L4/L5 全部 skip。

## 根因

本地调试时把 `conandata.yml` 的 `sources.url` 从官方 https URL 改成了指向本机的
`file:///storage/.../predl_cache/f8d228e8_aghermann-1.1.2.tar.xz`，忘记还原就提交推送。
本地该文件存在所以通过；CI worker 干净环境没有这个绝对路径，source() 直接 FileNotFoundError。
属"本地环境状态泄漏进配方"，与 E318/E486 本地缓存污染同族。

注意：CI 脚本的 Pre-download 步骤会"还原 conandata.yml 为官方 URL"，但它只还原**工作副本**；
conan 缓存内已 export 的配方仍带坏 URL，因此失败依旧（本轮日志中 Pre-download 提示还原了但 build 仍败）。

## 解决方案（rec: restore-official-url-before-commit）

提交前把 `sources.url` 还原为官方 https URL（sha256 保持实测值不变）：

```bash
# 还原
git checkout -- archives/a/aghermann/1.1.2/conandata.yml
# 确认无本地路径残留
grep -rn "file://" archives/   # 应无输出
```

上游站点临时不可达时不要改 conandata.yml，用 DOWNLOAD_CACHE 预下载缓存兜底。

## 验证流程

1. `CI_PACKAGES="archives/a/aghermann/1.1.2" CI_BRANCH="feat/aghermann-1.1.2" zsh ci/conan/build_and_test.sh`（zsh，路径格式传包）
2. 全绿后推送回 PR head 分支
3. 评论 `/rebuild` 手动触发 CI（push 不会自动构建）

## 禁止模式

- `sources:` 下 `url: "file://..."` —— 本地环境泄漏，CI 必败
- URL 含 `/storage/`、`/home/`、`/tmp/` 等构建机绝对路径 —— 环境耦合

## 元数据

- severity: 2
- similar_to: E318, E486
- source: PR #10748 build #61218, commit a61bf3aa3e
- date: 2026-09-26
