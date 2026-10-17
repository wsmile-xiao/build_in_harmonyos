# html5lib 1.1 适配笔记

## 编译环境
- **构建系统**: 纯 Python（无编译，setuptools/pyproject）
- **编译日期**: 2026-09-01
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（无源码补丁）

## 编译步骤（conan create 全流程）

```bash
conan create archives/h/html5lib/1.1 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 PyPI 官方 sdist 下载并 strip_root
（目录 html5lib-1.1）。

### 2. 打包（package()）
- 纯 Python 库（html5lib/ 包，大量 .py 模块），无编译
- build() 用 `copytree` 把源码拷到 staging（源外目录 /data/storage/el2/base/cache/）
  ——本环境 python-require 型 conan create 会静默跳过构建（webencodings 先例），
  故用 application 型
- package() 把 html5lib/ 拷到 `lib/python3.12/site-packages/`
- package_type=application（webencodings/dataproperty/pytablewriter 先例）
  + commands.json（R38）

## 依赖
- **six/1.17.0**（six>=1.9，ohpcd + main 已发布）
- **webencodings/0.6.1**（webencodings>=0.5.1，ohpcd + main 已发布）
- lxml/genshi/chardet 为 extras 可选（未装不影响核心解析）

## 上游测试（rule 4）
- 测试框架：pytest（html5lib/tests/，pytest-expect 驱动）
- 本地实测：**21532 passed / 10913 skipped / 995 xfailed**——通过率 100%
  （passed/(passed+failed+errors)，skipped/xfailed 不计分母）
- **兼容性坑**：html5lib 1.1 的旧 conftest 用 `pytest_collect_file(path,...)`
  hook 签名，新 pytest（9.x）不兼容；Python 3.12 移除 pkg_resources 且
  pytest 5.x 断言重写报 AST lineno 错误——最终用
  `pytest>=5.4.2,<6 + setuptools<81 + --assert=plain + -p pytest_expect`
  跑通（PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 避免与已装高版本插件冲突）
- 适配后：test_package R34 真实 python 加载打包的 html5lib 并
  parse 真实 HTML 校验 DOM（<p>hello</p>），1/1 = 100%

## 已知限制
- 无（纯 Python HTML5 解析库）
---

**编译结束**: 2026-09-01 23:04
**最终状态**: built
