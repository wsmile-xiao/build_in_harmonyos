# tgt 1.0.85 packaging

tgt 1.0.85 的产物发布**走 Conan 体系**（ARCHIVE-SPEC v3.0），本目录不含手工预编译 tar.gz：

- 正式发布路径：
  ```bash
  conan create archives/t/tgt/1.0.85 \
      -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
      --user=ohpcd --channel=stable
  conan upload tgt/1.0.85@ohpcd/stable -r=ohpcd
  ```
- 若需要本地打包验证产物（`tgt-1.0.85-ohos-aarch64.tar.gz`），由 CI 侧生成，被 `.gitignore`
  的 `packaging/` 规则忽略，**不入库**（全仓 77 个 `packaging/` 目录中 0 个含 tar.gz）。
- 本包的产物清单（`conan create` 的 `package()` 实测，共 6 个文件）：
  `bin/tgtd`、`bin/tgtadm`、`bin/tgtimg`、`bin/tgt-admin`、`bin/tgt-setup-lun`、`licenses/LICENSE`。

> 备注：`knowledge/ARCHIVE-SPEC.md` 已将 `packaging/` 与 `.staging-verified` 标注为**废弃**
> （"Conan 自带隔离验证"）。本文件仅用于说明发布路径，不替代 Conan 配方。
