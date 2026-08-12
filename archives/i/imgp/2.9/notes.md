# imgp 2.9 适配笔记

## 编译环境
- 构建系统: custom（pip install 安装 Python 包）
- 编译日期: 2026-07-27
- 编译器: N/A（纯 Python 脚本，无需编译）
- 状态: built

## 编译步骤

1. pip install --force-reinstall --prefix=$HOME/usr/local pillow（安装预编译 OHOS aarch64 wheel）
2. pip install setuptools==75.8.0（从社区 PyPI 源安装，替代裸下载 files.pythonhosted.org 的 tarball——后者在 CI 网络超时）
3. cd <source_dir> && pip install --no-build-isolation --no-deps .（安装 imgp）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | OHOS 无系统 CA 证书包 | 设置 SSL_CERT_FILE=/etc/ssl/certs/cacert.pem |
| 2 | pip install . 找不到 imgp.py | setup.py 需复制 imgp → imgp.py 但 pip 临时构建目录不含该文件 | build() 中先执行 shutil.copy 创建 imgp.py 再运行 pip install |
| 3 | ~/.local/ 目录 noexec 无法加载 .so | OHOS HMDFS 文件系统限制 | 使用 --prefix=$HOME/usr/local/ 安装 pillow |
| 4 | 裸下载 files.pythonhosted.org 的 setuptools tarball 在 CI 网络超时（TimeoutError at ~9%） | urllib 直连 files.pythonhosted.org CDN 在 CI 网络不可达 | 改用 pip install setuptools==75.8.0 从社区 PyPI 源安装（已验证 pip download 成功） |

## 源码修改

- `patches/0001-fix-setup-pkg-resources.patch` — 修复 setup.py 中 setuptools/pkg_resources 导入兼容性

## 依赖版本

- pillow 12.3.0（预编译 OHOS aarch64 wheel，从社区 PyPI 源安装）
- setuptools 75.8.0（从社区 PyPI 源 pip 安装，已验证可用）
- Python 3.12.9（系统预装）
- libjpeg.so.62, libtiff.so.6, libpng16.so.16, libz.so.1 等（pillow 运行时依赖，从系统库目录打包）

## 验证结果

- 编译状态：通过（本机 CI 流水线 conan create 全流程通过，exit=0）
- 新增测试用例通过率：3/3（test_import / test_cli / test_image_processing 全部通过）

```bash
imgp --help                              # PASS: 输出完整帮助文档
imgp -x 50x50 test.png                   # PASS: 图片缩放成功（100x100 → 50x50）
```

> 注：imgp 无 `--version` 选项（上游不提供），版本验证通过 test_package 的模块导入检查（`imgp._VERSION_`）完成。

## CI 修复记录

- **问题（2026-08-10）**：CI conan-build-test 失败，test_package 阶段 `import PIL` → dlopen `PIL/_imaging*.so` 报 `Permission denied`（本机验证通过但 CI 失败）。
- **根因**：HMDFS 上 usr/local 下 pip 安装的 `.so` 权限固定为 770（owner/group rwx，others 无权限），且 `chmod`/`install -m 755` 均无法修改（E046 平台限制）。本机进程在 file_manager 组（gid 1006）故可读；CI 沙箱进程非组员，dlopen 被拒。
- **修复**：`test_package/test.py` 在 `import PIL` 前调用 `_stash_pil_to_writable_dir()`，把 PIL 包复制到 `tempfile.mkdtemp()`（沙箱进程可写目录），复制产物的组属沙箱进程 → 可读可 dlopen；同时把该临时目录注入 `PYTHONPATH`（供 imgp CLI 子进程）与 `LD_LIBRARY_PATH`（PIL .so 的 libtiff 等依赖）。
- **验证**：本机完整 CI 流水线重跑 exit=0，conan create passed，3/3 测试通过。

## 交付物

无打包产物，imgp 作为 Python CLI 工具通过 pip install 安装到 bin/ 目录。

## 注意事项

- 上游 auto-completion/zsh/_imgp 和 imgp.1 手册中有 -z/-p 等选项名与源码不匹配的遗留问题，已修复
- auto-completion/fish/imgp.fish 中 -l P 应改为 -s P（fish shell 短选项语法）
- SSL_CERT_FILE 需指向 OHOS CA bundle 路径才能正常进行 HTTPS 下载
---

**编译结束**: 2026-07-27
**最终状态**: built
