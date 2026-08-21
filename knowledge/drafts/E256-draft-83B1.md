# E256 — CLI 工具无 --version/--help 长选项导致 L2 smoke test 失败

## 错误现象

- conan-verify L2 门禁运行 `bin/<tool> --version` 与 `--help` 均返回非 0（exit 2）
- 门禁判定 "所有二进制文件均无法运行" → L2 FAIL

## 根因

- 上游 CLI 工具（如 OpenWrt jshn）只实现 getopt 短选项（`-r -R -o -w -p -n -i`），
  对 `--version`/`--help` 落入 getopt 默认分支调用 `usage()` 并返回 exit 2

## 修复方案

- 在 `main()` 开头（getopt 循环之前）增加 GNU 长选项处理：

```c
if (argc > 1 && !strcmp(argv[1], "--version")) {
    printf("%s %s\n", progname, VERSION);
    return 0;
}
if (argc > 1 && (!strcmp(argv[1], "--help") || !strcmp(argv[1], "-h"))) {
    usage(argv[0]);
    return 0;
}
```

- 生成补丁（track-edit add + refresh-patch --auto），登记进 conandata.yml patches 段

## 先例

- libubox 2026-06-19 `patches/0001-jshn.c.patch`

## 验证

```bash
jshn --version  # → "jshn 2026-06-19", exit 0
jshn --help     # → usage, exit 0
```
