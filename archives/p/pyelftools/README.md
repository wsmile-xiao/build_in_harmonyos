# pyelftools

Library for analyzing ELF files and DWARF debugging information — a pure
Python (no C extension) package, architecture-independent (noarch).

- 上游: https://github.com/eliben/pyelftools
- License: Unlicense (public domain)
- 适配: 纯 Python noarch（同 packaging/26.3 先例），`package()` 拷贝 `elftools/`
  到 `lib/pythonX.Y/site-packages/`，消费端经 `runenv_info` 注入 PYTHONPATH
- 运行时零第三方依赖

## 版本

| 版本 | 状态 | 上游测试 |
|------|------|----------|
| 0.33 | built | 130/130 可执行项通过（100%）；58 对比项 aarch64 平台阻断 |
