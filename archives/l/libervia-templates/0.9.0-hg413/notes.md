# libervia-templates 0.9.0-hg413 适配笔记

## 编译环境
- 构建系统: python（hatchling 后端，纯 Python 包；无 C/C++ 编译）
- 编译日期: 2026-09-26
- 解释器: python3.12（宿主）+ jinja2/3.1.6（ohpcd 制品）
- 状态: built

## 编译步骤

本包为纯 Python + 模板数据，无 configure/make 编译。配方流程：

1. `init-build`（--url 显式传 Debian 官方 hg413 快照 orig 包；goffi 官方
   archive 接口 500、PyPI 只有 0.8.0 版本不符，故用 Debian 镜像源，R39 合规）
2. `pre-analysis`：纯 Python 包，未检测到图形/音视频/系统集成/平台特定代码
3. `conan-init` 后按 jinja2/3.1.6 先例**重写**配方（生成的 autotools 模板
   不适用）：
   - `package_type = "python-require"`
   - `requirements()`: jinja2/3.1.6
   - `package()`: 把整个 `sat_templates/`（__init__.py + VERSION + i18n/ +
     templates/ default/bulma 两套主题）拷入
     `<pkg>/lib/python3.12/site-packages/sat_templates`
   - `package_info()`: runenv/buildenv 注入 PYTHONPATH
4. `conandata.yml` 写入**真实 sha256**（本地 sha256sum 计算并复核）
5. `test_package/`：重写为消费者功能测试（12 项断言，R34 真实 API）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游官方 archive 接口不可用、PyPI 只有旧版 0.8.0 | goffi repos archive 接口返回 500；PyPI 未发布 0.9.0 系列 | 改用 Debian 官方镜像的 hg413 快照 orig 包（deb.debian.org），R39 合规 |
| 2 | conan-init 生成的是 autotools 模板（configure/make/CMakeLists.txt/test.c） | 生成器按默认构建系统猜测，不识别纯 Python 包 | 按 jinja2/3.1.6 python-require 先例完全重写 conanfile.py 与 test_package |
| 3 | 上游版本信息不一致 | `sat_templates/__init__.py.__version__="0.9.0.dev0"`（hatchling 读取）vs `sat_templates/VERSION="0.8.0"`（旧 setup.py 读取，遗留） | 以 pyproject/__init__.py 为准；配方版本号 0.9.0-hg413 对应上游 Mercurial rev 413 |
| 4 | 模板渲染需要完整 Libervia 上下文 | 模板依赖 script/C/icon/_/gettext 等全局对象与 i18n 扩展 | 测试中构造 FileSystemLoader + jinja2.ext.i18n + 注入等价全局对象，端到端渲染打包内真实模板 |

## 源码修改

无（patches 为空）。纯 Python + 模板数据，无需任何源码改动。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| jinja2 | 3.1.6 | ohpcd 已发布（W0 预检 conan download 通过） |
| markupsafe | 3.0.3 | jinja2/3.1.6 配方声明的传递依赖 |

## 验证结果

- 上游测试：**上游无测试用例（0 个）**——hg413 快照无 tests/ 目录、
  无 test_*.py、无 tox/pytest 配置（配方 build() 内真实检查后如实记录）。
- 适配后 test_package 消费者测试：**12/12 passed（100%）**
  （本地先用 fake-site 目录验证，随后 conan create 内再跑一遍）。
  覆盖：import sat_templates 校验 __version__；打包布局
  （VERSION/两套主题/i18n/settings.json 合法 JSON）；jinja2(3.1.6)
  FileSystemLoader 渲染打包内实际模板（default/bulma 主题 error/404.html
  与 error/401.html 全链渲染，断言标题/正文/bulma.min.css）；1 个负例。

```bash
# 消费者测试（12 项）——本地验证输出
libervia-templates 0.9.0.dev0 consumer tests: 12/12 passed
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | python-require 配方（jinja2/3.1.6 依赖 + site-packages 布局 + PYTHONPATH 注入） |
| conandata.yml | 源码 URL + 真实 sha256 |
| test_package/ | conanfile.py + test_libervia_templates.py（12 断言）+ MANIFEST.yml |
| manifest.yaml / notes.md / pre-analysis.md | 元数据与记录 |

纯 Python 包，无 bin/ 可执行文件，无需 commands.json（R38 不适用）。

## 注意事项

- 本包无可执行文件、无 C/C++ 产物，CI 只需 conan create + test_package 验证。
- bulma 主题 `_browser/__init__.py` 引用浏览器端全局（browser/document），
  仅被 Libervia 前端浏览器打包器使用，Python 侧不会 import，无需处理。
---

**编译结束**: 2026-09-26 21:21
**最终状态**: built
