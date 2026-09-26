# E635 — OHOS 无系统时区数据库：Python 标准库 zoneinfo 需 vendored PyPI tzdata

- **状态**: 草稿（contributor U4D2）
- **严重度**: 2（medium）
- **阶段**: testing / runtime
- **来源事件**: undertime 4.3.1 适配（2026-09-24）

## 错误特征

```
E   zoneinfo._common.ZoneInfoNotFoundError: 'tzlocal() does not support non-zoneinfo timezones like UTC.
    Please use a timezone in the form of Continent/City'

$ python3 -c "import zoneinfo; zoneinfo.ZoneInfo('UTC')"
zoneinfo._common.ZoneInfoNotFoundError: 'No time zone found with key UTC'
```

典型分布：同一套上游 pytest 里，**只有走 stdlib zoneinfo 的用例失败**，走 pytz 的用例正常
（undertime 实测 10 例中 6 例失败、4 例通过，`test_list_zones` 正常）。

## 触发条件

1. 平台无系统 tzdb：`ls /usr/share/zoneinfo` → `No such file or directory`（stdlib zoneinfo 的
   `TZPATH` 系统目录一个都不存在）。
2. 被测代码/依赖经由 **Python 标准库 `zoneinfo`** 解析时区：`tzlocal.get_localzone()`、
   `dateparser`、任何 `zoneinfo.ZoneInfo(...)` 调用。
3. 常见触发场景是把上游 CI 惯用的 `TZ=UTC`（tox.ini 里很常见）带进测试环境——此时 tzlocal 会拿
   `TZ` 当 zoneinfo key 去查库，直接抛错。

## 根因

`zoneinfo` 是"系统数据库优先、PyPI `tzdata` 包兜底"的两级查找：本平台没有系统 tzdb，而包里也没有
`tzdata`，两级都落空 → `ZoneInfoNotFoundError`。

`pytz` 自带一份时区数据，所以用 pytz 的代码路径完全正常；`dateparser`/`tzlocal` 走 zoneinfo，于是失败。
这一半成功一半失败的表象很容易被误判成"测试本身有问题"，而不是平台能力缺口。

## 解决方案（推荐）

把 PyPI 的 `tzdata` 包 vendored 进包内 site-packages：

```bash
pip install --only-binary=:all: --target=<私有 deps 目录> tzdata
```

之后 `zoneinfo` 会自动回退使用它，**不需要改源码、不需要设环境变量、不需要动系统目录**。

对 CLI 包而言这一步是**功能性必需**而非仅测试需要：undertime 要靠 `tzlocal` 判断本地时区，缺 tzdata
时工具本身在该平台上不可用。

## 验证证据

```bash
# 修复前
$ python3 -c "import zoneinfo; zoneinfo.ZoneInfo('UTC')"
ZoneInfoNotFoundError: 'No time zone found with key UTC'

$ TZ=UTC PYTHONPATH=<vendored site-packages> python3 -c "import tzlocal; print(tzlocal.get_localzone())"
ZoneInfoNotFoundError: 'tzlocal() does not support non-zoneinfo timezones like UTC.'

# vendored tzdata 之后
$ TZ=UTC PYTHONPATH=<vendored site-packages> python3 -c "import tzlocal; print(tzlocal.get_localzone())"
UTC
```

undertime 4.3.1 实测：vendored tzdata 前 conan create 内上游 pytest **6/10 失败**，加入后 **10/10 通过**，
且 `bin/undertime --config /dev/null --no-default --date ... --timezone UTC Europe/Paris` 在
`env -i` 裸环境下正常输出对齐表格。

## 适用边界

- 适用：任何在 OHOS 上跑、且依赖 stdlib `zoneinfo`（直接或经 tzlocal/dateparser 间接）的 Python 包；
  对"本地时区"有语义要求的 CLI 工具尤其必须处理。
- 不适用：只使用 `pytz` 自带数据的代码（不受影响）；由其它机制（如环境已有真实 tzdb + TZDIR）已解决的场景。

## 不适用 / 禁止

- ❌ 把 `TZ=UTC` 硬编码当最终交付：时区能力降级为常量，所有本地时间换算失真。
- ❌ 往 `/usr/share/zoneinfo` 或共享 prefix 写时区数据：污染共享环境（R49），跨任务互相干扰。

## 关联条目

- **similar_to E315**：E315 记录的是 R（r-base）在 OHOS 上的 tzdb 权威契约（TZDIR 优先、内部
  zoneinfo、禁止 /etc/zoneinfo 遮蔽）。两者主题同为"OHOS 时区数据库缺口"，但 E315 是 R 运行时 +
  TZDIR 优先级问题；本条是 **Python stdlib zoneinfo 无任何数据库可用**，修复手段是 vendored PyPI
  `tzdata` 包（zoneinfo 内置回退路径），语言、机制、修复均不同。
- **similar_to E241**：E241 是"数据/规则清单型库"（含 tzdata 作为被测数据包）的打包范式；本条是把
  tzdata 作为**依赖缺口**补齐，场景不同。
