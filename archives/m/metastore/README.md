# metastore

`metastore` 把文件树的属主、属组、权限位、扩展属性（xattr）与（可选）mtime 存入一个独立的 metafile，
之后可随时与真实状态比对（`compare`）或把元数据回写到文件系统（`apply`）。
上游 <https://github.com/przemoc/metastore>，GPL-2.0-only，1.1.2（2018-01-06）为上游最新版本。

典型用途：补足 git / tar 不保存的元数据，或把整棵文件树打成 tarball 后确保「一切」都随包带走。

- 版本目录：`1.1.2/`（配方、补丁、消费者测试、报告）
- 交付物：`bin/metastore`
- 命令行契约见软件级 `commands.json`，适配要点见软件级 `manifest.yaml` 的 `ohos_adaptation`，
  踩坑与实测账本见版本级 `notes.md`

## 用法速查

```sh
metastore --save  --file .metadata ./tree     # 采集 ./tree 的元数据
metastore --compare --file .metadata ./tree   # 列出与存储值的差异
metastore --apply --file .metadata ./tree     # 把存储的元数据写回文件系统
metastore --dump  ./tree                      # 以可读形式打印真实元数据（调试/冲突合并辅助）
metastore --version
```

常用选项：`-m/--mtime`（把 mtime 纳入比较/回写）、`-f/--file`（metafile 路径，默认 `./.metadata`）、
`-e/--empty-dirs`（配合 `--apply` 重建缺失的空目录）、`-E/--remove-empty-dirs`（清理多出的空目录）、
`-g/--git`（连 `.git` 目录一并处理）、`-v/-q`（增减详细度）。
