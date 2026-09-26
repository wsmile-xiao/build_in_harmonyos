# E636 — OHOS CI worker（HNP python/AppSpawn 沙箱）无法 dlopen 用户空间 C 扩展 .so

- **状态**: 草稿（contributor U4D2）
- **严重度**: 3（blocking）
- **阶段**: runtime / testing
- **来源事件**: undertime 4.3.1 适配，CI #58278（2026-09-24）

## 错误特征

```
Error loading shared library <路径>/xxx.cpython-312.so: Permission denied
ModuleNotFoundError: No module named 'regex._regex'            # 后缀不匹配时的表象
ModuleNotFoundError: No module named 'ephem._libastro'
cannot import name '_regex' from partially initialized module 'regex'  # 部分加载
```

CI 日志同源证据：`coverage` 的 C tracer 加载同样报 `Permission denied`（no-ctracer 回退纯 Python，
仅警告；而 regex/ephem 无纯 Python 回退，直接 ImportError）。

## 触发条件

1. 构建/测试解释器是 **HNP python**（`/data/service/hnp/bin/python3`，运行于 AppSpawn 沙箱内），
   其 `EXT_SUFFIX` 通常为 `.cpython-312.so`（platform=harmonyos-aarch64）。
2. 运行时尝试 dlopen **用户空间**（如 `$HOME/usr/local`、conan cache、`--target` 目录）下的
   C 扩展 `.so`。
3. 镜像提供的是 `cp312-ohos_aarch64` wheel，其 `.so` 后缀为
   `cpython-312-aarch64-linux-ohos`——与 HNP python 后缀不匹配（importlib 找不到）；
   即使手工改名匹配后缀，AppSpawn 沙箱仍拒绝 dlopen（Permission denied）。
4. 本地开发 python（如 `usr/local/bin/python3` 3.12.9，EXT_SUFFIX 带 `-aarch64-linux-ohos`）
   无此限制 → **本地 W3 全绿 ≠ CI 全绿**（W0b 环境语义不可迁移的又一实例）。

## 根因

AppSpawn 沙箱对用户空间共享库的 dlopen 实施权限/策略限制；HNP python 运行于该沙箱内，因此
任何用户空间的 C 扩展 `.so` 都加载失败。后缀不匹配只是表象之一（importlib 找不到），改名后仍被
沙箱拒绝则是本质。

连带效应：**硬依赖 C 扩展的 pip 包在 CI 完全不可用**——`dateparser`（依赖 `regex`）、`ephem`、
`regex` 本身。有纯 Python 回退的包（`pyyaml` 的 `_yaml`、`simplejson` 的 `_speedups`、
`coverage` 的 tracer）不受影响，这解释了 afl-utils 用 simplejson 能过 CI 而 undertime 用
dateparser 挂掉的现象。

## 解决方案（推荐）

配方内 pip 依赖**只选纯 Python 包，或带纯 Python 回退的包**；对硬依赖 C 扩展的上游依赖：

1. **源码补丁回退**：如 `dateparser` → 在上游 `parse_date_dateparser` 的
   `except ImportError` 分支回退到已依赖的纯 Python `python-dateutil`
   （`dateutil.parser.parse` + 按 dateparser `TIMEZONE=local_zone` 语义 `astimezone(local_zone)`）。
2. **方案 A 关闭可选特性**：如 `moonphases` 硬依赖 `ephem` → 本包不发布该伴随脚本，PR/README
   说明功能损失面（主工具完整可用）。

undertime 4.3.1 实证：RUNTIME_PKGS 去掉 `dateparser`/`ephem` 后，上游 pytest 在 HNP python
3.12.8 沙箱 10/10 通过。

## 验证证据（可复现）

```bash
# 复现：HNP python 加载改名后的 C 扩展 .so
$ /data/service/hnp/bin/python3 -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))"
.cpython-312.so
# 把 ohos_aarch64 wheel 中 _regex.cpython-312-aarch64-linux-ohos.so 改名 _regex.cpython-312.so
# 后 import regex → ImportError: Error loading shared library ... Permission denied（实测）

# 修复验证：纯 Python 依赖
$ PYTHONPATH=<纯 python deps> /data/service/hnp/bin/python3 -c "from dateutil import parser; print(parser.parse('2020-11-01 12:00:00-04:00'))"
2020-11-01 12:00:00-04:00   # OK

# 端到端：TZ=UTC pytest test_undertime.py → 10 passed（HNP python 3.12.8 沙箱实测）
```

## 适用边界

- 适用：任何经 pip 安装/ vendored Python 依赖的配方；CI 与本地解释器不同（HNP vs usr/local）
  的 OHOS 适配任务。
- 不适用：纯 C/C++ 库（不经 python dlopen）；CI 与本地使用同一解释器且能加载 C 扩展的场景；
  仅需 pyyaml/simplejson/coverage 这类有纯 Python 回退的包。

## 不适用 / 禁止

- ❌ 硬依赖无纯 Python 回退的 C 扩展 pip 包（regex/ephem/dateparser）——CI 必挂。
- ❌ 把"本地 W3 通过"当作 CI 全绿证据——两个解释器的 dlopen 能力不同。

## 关联条目（部分重复说明）

- **similar_to E488**（Python C 扩展 .so dlopen 权限模型，notmuch2）：
  - 重合点：症状均为 OHOS CI 下 dlopen 用户空间 `.so` 报 `Permission denied`，影响 Python
    包真实加载；本地与 CI 判例差异（本地可、CI 拒）。
  - 差异点：E488 归因 HMDFS 文件 owner=20001006/权限 770 致非 owner 用户 chmod 静默失败，
    修复为"复制包 + open/write 重写 .so"；E636 聚焦**pip 依赖选型与配方策略**，归因
    AppSpawn/HNP python 的 dlopen 策略（后缀匹配后仍拒），修复为"依赖只选纯 Python /
    源码回退 / 裁剪可选特性"——不依赖重写 .so。
- **similar_to E502**（CI worker 拒绝 dlopen/LD_PRELOAD 用户目录 .so）：
  - 重合点：根因同一（worker 加载器策略拒用户目录 dlopen，与 ELF 签名无关）；
    "本地 dlopen 成功不可迁移到 worker"这一 W0b 判例一致。
  - 差异点：E502 面向原生库（exec 时 NEEDED 可加载），修复为 probe-then-route-to-exec-time；
    E636 面向 **pip 安装的 Python wheel**（无法走 exec-time NEEDED），新增了
    EXT_SUFFIX 后缀不匹配的实测证据（改名后仍拒 ⇒ 是策略非后缀问题）与配方侧纯 Python
    依赖选型/回退/裁剪的完整方案。
  - 新增价值：给"OHOS 适配 Python 包"提供可直接照做的依赖选型清单（pytz/tzlocal/tzdata/
    python-dateutil 纯 Python；pyyaml/simplejson/coverage 有纯 Python 回退；regex/ephem/
    dateparser 不可用），并示范 dateutil 回退补丁 + 可选特性裁剪（moonphases）。

查重覆盖 `knowledge/graph/`、`knowledge/doc/`、`knowledge/drafts/`；除上述三条外无更高相似
条目（draft-review: E488 0.42 / E502 0.38 / E143 0.31，均未达 >50% 关键词重合的完全重复阈值）。
