# undertime

Pick a meeting time across multiple timezones: `undertime` prints an aligned
table of simultaneous local times for every selected zone, taking daylight
savings and future date shifts into account.

The tool is a pure Python 3 console script (upstream `setup.cfg`
`[options] scripts`), so there is no native compilation step.

> 注：上游第二个脚本 `moonphases`（月相计算）依赖 `ephem`（C 扩展），
> 在本平台 CI 沙箱（HNP python/AppSpawn）中无法 dlopen 用户空间 C 扩展，
> 故不随本包发布（详见版本目录 notes.md）。

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| 4.3.1   | built  | Pure Python 3 (setuptools + setuptools_scm); version injected via `SETUPTOOLS_SCM_PRETEND_VERSION`; dateparser（依赖 regex C 扩展）在 CI 不可用，补丁回退到 python-dateutil；上游 pytest 套件在 build() 中执行 |
