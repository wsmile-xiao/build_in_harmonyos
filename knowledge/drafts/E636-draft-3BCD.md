# E636 — toybox patch 无法匹配 CRLF 上下文，refresh-patch dry-run 误报失败

## 错误特征

`ohc-run.py refresh-patch --auto` 报 "0001-xxx.patch: dry-run 失败" / "无有效新补丁"；
手动 `patch --dry-run -p1` 对上游源应用 LF 补丁时报 `Hunk 1 FAILED`，但补丁内容
肉眼与文件完全一致。

## 触发条件

- 构建系统: 任意（上游源码为 CRLF 行尾，常见于 Windows 出品/老式 C 库）
- 阶段: 补丁生成（refresh-patch dry-run）/ 本地 patch 应用
- 实测案例: libsoil 1.07.20080707.dfsg（Debian 上游源 CRLF）
- 根因工具: 鸿蒙默认 `/usr/bin/patch` 为 toybox 0.8.12，上下文匹配把 CRLF 行尾当差异

## 根因分析

toybox patch 对 CRLF 源码文件应用 LF 补丁时，上下文行因行尾差异无法匹配，报
"Hunk FAILED"。refresh-patch 的 dry-run 用系统 patch，因此丢弃本应有效的补丁。
注意：Conan 实际应用补丁用的是 patch_ng（纯 Python），对 CRLF 源 + LF 补丁能正确
匹配，**CI 不受影响**——此问题只卡本地 refresh-patch 生成环节。

## 解决方案

### 推荐方案

将 orig 与 work 中被改文件的 CRLF 统一归一化为 LF 后重新生成补丁（补丁本身即 LF；
CI 用 patch_ng 应用，对 CRLF/LF 源皆正确）：

```bash
python3 -c "for p in ('<orig>/<rel>','<work>/<rel>'): d=open(p,'rb').read().replace(b'\r\n',b'\n'); open(p,'wb').write(d)"
# 重建 edit-tracker 基线后
ohc-run.py refresh-patch --auto <软件名> <版本>
```

### 禁止做法

- ❌ 在 conandata.yml 里声明特殊 patch 格式/标志绕过（patch_ng 本就兼容，无需）

## 验证

```bash
# 对 CRLF 文件用 toybox patch 应用 LF 补丁 → 观察 "Hunk 1 FAILED"
# 换 patch_ng: from patch_ng import fromfile; fromfile('patch').apply(strip=1, root=...) → True
```

## 关联条目

- 相关: E254（toybox patch 新文件 dry-run 问题）、E549
