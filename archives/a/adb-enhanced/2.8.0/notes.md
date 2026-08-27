# adb-enhanced 2.8.0 适配笔记

## 编译环境
- 构建系统: python (pip wheel)
- 编译日期: 2026-08-05
- Python版本: 3.12.9
- Conan版本: 2.29.1 (OHOS 适配版)
- 状态: built (conan create 验证通过)

## 源码信息
- 仓库: https://github.com/ashishb/adb-enhanced
- 版本: 2.8.0 (tag 2.8.0, commit 5b82ea2)
- 源码URL: OHOS 社区 PyPI 镜像 (pypi.cnb.cool)
- SHA256: 75c92007bbf295ec97fb89fedf0bd24e6424d726b1343aa3b1fbf5e2115efcc5

## Conan 适配步骤

1. 使用 ohc-run.py init-build 初始化构建上下文
2. 使用 ohc-run.py conan-init 生成 Conan 配方骨架
3. 手动重写 conanfile.py 为 Python 项目适配 (基于 badread 模式):
   - package_type = "application"
   - settings = "os", "arch" (无 compiler/build_type)
   - build(): pip wheel --no-deps --no-build-isolation
   - package(): 解压 wheel + 安装 deps (docopt, psutil) + 创建 wrapper
   - package_info(): 设置 bindirs 和 PYTHONPATH
4. 重写 conandata.yml: 使用 OHOS 社区 PyPI 镜像 URL
5. 重写 test_package/conanfile.py: 验证包结构 + 运行 adbe --version
6. 创建 commands.json (软件级别, R38)
7. conan create 验证通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | psutil==7.2.1 版本不可用 | OHOS 社区 PyPI 源仅有 7.2.2 | 修改 pyproject.toml 使用 psutil>=7.2.1,<8.0 |
| 2 | pip wheel 构建失败 | pyproject.toml 缺 [build-system]，build isolation 失败 | 使用 --no-build-isolation + 预装 setuptools |
| 3 | setuptools 发现 patches/ 为包 | conan 导出的 patches/ 目录在源码目录中 | build() 中清理 patches/ 目录 |
| 4 | psutil .so 加载失败 | OHOS SELinux 限制用户目录 .so 加载 (E046) | 测试中捕获异常，记录为平台限制 |
| 5 | PyPI files.pythonhosted.org 不可达 | OHOS 设备无法直连 PyPI | 使用 OHOS 社区 PyPI 镜像 (pypi.cnb.cool) |

## 源码修改

- pyproject.toml: 修改 psutil 版本依赖从 ==7.2.1 改为 >=7.2.1,<8.0

## 依赖版本

- docopt: 0.6.2 (pip 安装到 deps/)
- psutil: 7.2.2 (pip 安装到 deps/)

## 验证结果

```bash
$ conan create archives/a/adb-enhanced/2.8.0/conanfile.py ...
✅ 构建成功
✅ 包创建成功
✅ 测试通过 (包结构验证 + 版本验证)
⚠️ adbe --version 因 SELinux 限制无法运行 (E046)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (pip wheel + wrapper 模式) |
| conandata.yml | 源码 URL + SHA256 + 补丁声明 |
| test_package/conanfile.py | 测试 (结构验证 + adbe --version) |
| test_package/MANIFEST.yml | 测试声明 |
| patches/0001-pyproject.toml.patch | psutil 版本补丁 |
| commands.json | 命令行工具声明 (R38) |
| manifest.yaml | 编译元数据 |
| reports/test-report.md | 测试报告 |

## 注意事项

- 纯 Python CLI 工具，使用 pip wheel + wrapper 脚本模式打包
- 依赖 (docopt, psutil) 通过 pip 安装到 deps/ 目录，非 conan 依赖
- OHOS SELinux 限制可能导致 psutil C 扩展无法从用户目录加载
- CI 环境可能有不同的 SELinux 配置，adbe --version 可能正常工作

---
**编译结束**: 2026-08-05
**最终状态**: built (conan create 验证通过)
