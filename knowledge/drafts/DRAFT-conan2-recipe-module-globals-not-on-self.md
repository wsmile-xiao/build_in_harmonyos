# DRAFT-conan2-recipe-inline-source-constants-not-on-self

## 使用说明

Conan 2 配方把源码 URL/SHA256 以模块级常量内联（无 conandata.yml 的
BUILD_DIR 缺陷规避策略）时的两条铁律：① **不要**用 `self._xxx` 引用模块级
常量；② 修改内联常量后必须重传/重导出配方。本条给出正确写法、错误特征与
本机 30 秒自检命令。

## 适用范围

- 触发：真机/CI `conan create` 在 source() 阶段报
  `AttributeError: '<RecipeClass>' object has no attribute '_<name>'`，
  行号指向 `get(self, url=self._source_url, ...)` 一类调用。
- 背景：知识库既有条目（xmodem 策略）建议无补丁包把 URL/SHA 写进
  conanfile.py 以规避 CI 预下载 conandata.yml 的 BUILD_DIR 缺陷；但该策略
  的示例代码 `self._source_url` 在 Conan 2 上是错的——Conan 2 不会把模块级
  全局名映射到 self，self 上只存在类属性与方法。

## 输入输出定义

- 输入：conanfile.py 源文件。
- 自检命令（本机即可，无需真机）：
  `python -c "import ast; ast.parse(open('conanfile.py',encoding='utf-8').read())"`
  加 grep：`grep -n "self\._" conanfile.py` —— 除 Conan 官方下划线 API
  （如 `self._conan_data` 类内部属性需查证）外，任何 `self._<自定义名>`
  都是嫌疑。
- 输出：source() 改为直接引用模块级名（不带 self.）。

## 示例

错误（r1 真机实录，AttributeError）：

```python
_source_url = "https://example.org/x-1.0.tar.gz"
_source_sha256 = "…"

def source(self):
    get(self, url=self._source_url, sha256=self._source_sha256, strip_root=True)
```

正确：

```python
_source_url = "https://example.org/x-1.0.tar.gz"
_source_sha256 = "…"

def source(self):
    get(self, url=_source_url, sha256=_source_sha256, strip_root=True)
```

## 不适用 / 反例

- 类属性写法（`class X(ConanFile): _source_url = "..."`）下 `self._x`
  是合法的——本条只针对模块级常量误加 self. 的形态。
- 使用 conandata.yml 的配方走 `self.conan_data["sources"]`，与本条无关。
- 知识库指南/避坑文档中的示例代码若含 `self._source_url` 应视为待修正
  错误模板（文档 bug），不是运行环境差异。
