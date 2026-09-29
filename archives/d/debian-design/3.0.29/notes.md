# debian-design 3.0.29 适配记录

- **上游形态**：Debian Design 的 blend 数据 —— `nodes/*.yml`（4 个节点的**类清单**）、
  `skel/preseed.cfg.in` 与 `skel/script.sh.in`（Template Toolkit 模板）、`Makefile`
  （`boxer compose` 组合 + `md5sum`/`sha256sum` 生成校验和 + `gpg` 签名）。
- **交付**：`share/design-blends/{nodes,skel,Makefile}` + `share/doc/debian-design/{NEWS,TODO}`
  + `licenses/copyright`；纯数据包，无编译步骤。
- **消费者用例**（rule12）：`test_package/consumer_design.py` 复现上游 `all` 目标的
  组合链路（TT 子集渲染 → content/<node>/{preseed.cfg,script.sh} → MD5SUMS/SHA256SUMS），
  并按消费方口径验收（校验和回算、preseed 指令合法、`script.sh` 过 `sh -n`）。
- **边界声明**：`boxer` 的 **class→Debian 包名**映射来自外部 `boxer` 包，不在本包内，
  故消费者用例按节点的 class 清单渲染 `pkglist`（保持类选择信息不丢），并在输出中说明。
- **本地验证**：`ohc-run.py conan-verify debian-design 3.0.29` → PASS。
