# libxcb 1.17.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-05
- 编译器: clang/clang++
- 状态: built
- Conan 引用: libxcb/1.17.0（recipe revision `743324d2a2de2fb19f392d4e4b9095a5`）

## 编译步骤

1. `conan create archives/l/libxcb/1.17.0 --version=1.17.0`（CI / 本地唯一构建入口）
2. 配方 `generate()`：AutotoolsToolchain；追加 `--build/--host=aarch64-unknown-linux-gnu`；禁用 docs/xmlto/fop/xsltproc/selinuxtest；shared 构建
3. 修补 Conan 生成的 `xcb-proto.pc`，补回 `xcbincludedir` / `pythondir`，并设置 `PYTHONPATH` 以便 `c_client.py` 生成协议代码
4. OHOS：`configure` 内 `umask 077→022`，shebang 替换为 `/data/service/hnp/bin/bash`
5. `autotools.configure()` → `make` → `make check` → `install`；`package()` 修正 `.la` 的 `libdir`
6. `test_package`：在 ohos.toolchain.cmake 下将 `CMAKE_FIND_ROOT_PATH_MODE_PACKAGE` 设为 `BOTH`，链接并运行 6 项 API 烟囱断言

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | 旧版 config.guess | 补充 `--build/--host=aarch64-unknown-linux-gnu` |
| 2 | configure / config.status 失败 | HMDFS + umask 077 | `replace_in_file` 改为 umask 022（E002） |
| 3 | `/bin/bash` 不存在 | OHOS 路径差异 | shebang 替换为 `/data/service/hnp/bin/bash` |
| 4 | configure 找不到 xcb 协议 XML | Conan `xcb-proto.pc` 缺变量 | generate() 补 `xcbincludedir`/`pythondir` + PYTHONPATH |
| 5 | `tests/check_all` 未构建 | libcheck 未发布到 ohpcd/stable | MANIFEST.yml 豁免；仅跑 `check-pc-requires` |
| 6 | test_package 找不到 libxcb-config.cmake | ohos.toolchain.cmake 强制 `CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY` | CMakeLists.txt 覆写为 `BOTH` |
| 7 | 下游需 Xtrans 头 | libxcb 1.17.0 configure 不再 PKG_CHECK_MODULES(xtrans) | `requires("xtrans/1.4.0", transitive_headers=True)` |

## 依赖版本

- xcb-proto/1.17.0
- libxau/1.0.11
- libxdmcp/1.1.5
- xorgproto/2025.1
- xtrans/1.4.0（transitive_headers；CI 制品仓裸 ref，勿写 @ohpcd/stable）

## 验证结果

```bash
# 上游
make check
# PASS: check-pc-requires  (# TOTAL: 1 / # PASS: 1)
# check_all: 豁免（HAVE_CHECK=no，见 test_package/MANIFEST.yml）

# 消费者
conan create archives/l/libxcb/1.17.0 --version=1.17.0
# test_package 输出: libxcb api smoke ok  (6/6)
```

## 注意事项

- `check/0.15.2` 发布到 ohpcd/stable 后，取消 `conanfile.py` 中 `self.tool_requires("check/0.15.2")` 注释即可恢复 7 个上游单元测试。
- xtrans 选用已预编译的 1.4.0；若需切到 1.6.0，先 `conan create archives/x/xtrans/1.6.0` 再更新 requires。

---

**编译结束**: 2026-08-05
**最终状态**: built
