# OHOS PC 运行时 XDG 环境变量注入应用沙箱缓存路径

> 草稿（DRAFT）。与同目录 `appdirs-1.4.4-ohos-xdg-sandbox-dir-resolution.kv` 成对。
> 来源：appdirs 1.4.4 适配（【知识库扩展】）。

## 问题

纯 Python 的跨平台"目录解析"库（appdirs、platformdirs、pyxdg 等）通常靠
`XDG_*` 环境变量 + `HOME` 决定 user cache / data / state / log 目录。
在 OHOS PC 上这些路径落在哪里、是否需要补丁适配，此前没有明确的平台行为记录。

## 关键观察（实测）

OHOS PC 运行时（hap 应用沙箱）为进程注入：

```
XDG_CONFIG_HOME=/data/storage/el2/base/haps/entry/files
XDG_CACHE_HOME=/data/storage/el2/base/haps/entry/files
HOME=/storage/Users/currentUser
```

因此**遵循 XDG 规范的纯 Python 目录库自动、零补丁**地把 cache/log 目录解析到
应用沙箱（`/data/storage/el2/base/haps/entry/files/<App>/<version>`），
data/state 目录解析到 `$HOME/.local/share|state`。

## 做法

1. 按标准 **python noarch 配方**适配（`package_type=python-require`，模块拷贝到
   `lib/pythonX.Y/site-packages`，`runenv/buildenv` 注入 `PYTHONPATH`，同 E319 家族）。
2. **零补丁**：XDG_* 由 OHOS 运行时注入，库照规范读取即可；HOME 存在时
   user_data_dir 回退 `~/.local/share`（expanduser），行为仍正确。
3. 鸿蒙专项测试断言：`user_cache_dir`/`user_log_dir` 落在 `XDG_CACHE_HOME`
   前缀（沙箱路径）、`user_data_dir`/`user_state_dir` 为绝对路径、version
   三元组生效、5 个函数式 helper + AppDirs 类 5 属性全部返回非空 str。

```bash
# 鸿蒙专项测试核心断言
cache = appdirs.user_cache_dir("OhosApp", "OH", version="1.0")
assert cache.startswith(os.environ["XDG_CACHE_HOME"])   # 沙箱缓存
assert os.path.isabs(appdirs.user_data_dir("OhosApp", "OH"))
```

## 证据（appdirs 1.4.4，2026-09-20 实测）

- `conan create`（ohos-aarch64 profile）PASS；消费者 API PASS；
- `test_ohos_appdirs.py` PASS：
  `OHOS user_cache_dir -> /data/storage/el2/base/haps/entry/files/OhosApp/1.0`
  `OHOS user_log_dir  -> .../OhosApp/1.0/log`（`XDG_CACHE_HOME honoured`）
- 上游 unittest `3/3 = 100%`，**零补丁**（stdlib-only，Python 3.12 无 import 障碍）。

## 适用边界

- ✅ 适用：纯 Python、零 C 依赖、遵循 XDG_* 规范、noarch 目录解析库
  （appdirs / platformdirs / pyxdg 家族）。
- ❌ 反例：要处理配置/数据文件**格式**而非仅路径的库；依赖 C 扩展或系统库的
  目录库；硬编码 POSIX 路径、不读 XDG_* 的库需另行适配。
- ⚠️ CI 注意：clean runner 未必注入 `XDG_CACHE_HOME`，断言须容忍未设置时
  回退 `~/.cache`（测试用 `if xdg_cache:` 守卫）。
