# DRAFT-libxmlb-meson-installed-tests-bindir：conan MesonToolchain remaps libexecdir to the conan bindir, so GNOME installed-tests (binaries + data) are installed under bin/installed-tests instead of libexec/installed-tests

> Status: **Draft**（待审核 promote）| severity: `2` | category: `conan, meson, packaging, gnome` | Updated: ?
> 对应: `knowledge/drafts/DRAFT-libxmlb-meson-installed-tests-bindir.kv`

---

## 触发面

- trigger_tool: `meson|conan|install`
- phase: `packaging`

**匹配关键词**：installed-tests, libexecdir, bindir, MesonToolchain, meson install, gnome, glib, destdir, rmdir, install_dir

## 错误签名（error_signature）

```text
bin/installed-tests|libexecdir.*bindir|installed_test_bindir|expected.*libexec/installed-tests
```

## 根因（root_cause）

Conan's MesonToolchain (_get_default_dirs) maps the meson libexecdir to cpp.package.bindirs ("bin") to keep the conan package layout flat. GNOME projects (glib, libxmlb, ...) install their installed-tests suite via installed_test_bindir = join_paths(libexecdir, 'installed-tests', ...) so the test executable and its data files land in <pkg>/bin/installed-tests/<project>/ rather than libexec/installed-tests/<project>/. Recipes that rmdir the legacy libexec path after install silently keep the junk in bin/, and the unsigned (rpath-rewritten by meson install) test binary then ships inside the package.

## 影响范围（affected_scope）

Any meson package declaring installed-tests (or any tool installed into libexecdir) on conan 2.2x: the artifact path differs from the upstream/Debian convention. Verified instance: libxmlb 0.3.19 (archives/l/libxmlb/0.3.19).

## 推荐方案（rec_approach: `rmdir-bin-installed-tests`）

After meson.install(), remove the installed-tests tree from ALL remapped locations: bin/installed-tests (conan dir mapping), plus libexec/installed-tests and share/installed-tests as belt-and-braces (conan rmdir tolerates missing paths). The suite has already run in build() via `meson test` on the OHOS target, so dropping the installed copy matches the glib packaging convention.

## 修复命令（rec_command）

```text
rmdir(self, os.path.join(self.package_folder, "bin", "installed-tests")); rmdir(self, os.path.join(self.package_folder, "share", "installed-tests")); rmdir(self, os.path.join(self.package_folder, "libexec", "installed-tests"))
```

## 兜底方案（fallback_approach: `keep-and-sign`）

If the installed-tests suite must ship (distro-style installed-test harness), keep bin/installed-tests but extend the ELF re-sign glob to `bin/**/*` so the rpath-rewritten test binary is re-signed (an unsigned meson-install copy fails OHOS loader validation).

## 验证方式（verification_cmd）

```text
conan create archives/l/libxmlb/0.3.19 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 && ls <pkg>/bin/installed-tests
```

## 关联

- **相似**：E090

---

*本文件由 `knowledge/drafts/DRAFT-libxmlb-meson-installed-tests-bindir.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
