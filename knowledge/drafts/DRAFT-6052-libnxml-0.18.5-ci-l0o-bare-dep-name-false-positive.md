# DRAFT-6052-libnxml-0.18.5-ci-l0o-bare-dep-name-false-positive — CI L0o 门禁把 Conan 依赖访问 `self.dependencies["curl"]` 误判为外部 curl 命令调用

- 触发事件：libnxml 0.18.5 适配，scoped CI 的 L0o 检查报 conanfile.py 有 curl 命令调用
- 路径：Path B（知识库扩展）
- 编号：DRAFT-6052

## 现象

conanfile.py 的 generate() 中构建期读取 curl 依赖 cpp_info 的写法：

```python
curl = self.dependencies["curl"]
```

被 CI L0o 门禁（禁止配方用 subprocess/os.system 调外部 curl/wget 下载）命中报错。

## 根因

L0o 正则按**带引号的裸名字面量**匹配：`"curl"` / `'curl'` / `"wget"` / `'wget'`
（另匹配 subprocess/os.system 行内出现的 curl/wget）。Conan 2 的依赖访问 API
`self.dependencies["<名字>"]` 恰好要求传**裸依赖名**（不带版本），于是纯 API
数据访问被当成命令行调用误报。对照：`self.requires("curl/8.15.0")` 带版本
不触发；`self.dependencies["curl/8.15.0"]` 带完整 ref 也不触发。

## 可复用处置

1. 先反证确属误报：配方内 0 处 subprocess/os.system/命令行 curl 下载，
   源码获取只走 tools.files.get（conandata.yml sha256 校验）。
2. 不修改 CI 脚本、不用混淆命名规避。改用 Conan 2 文档化 API + 完整 ref：

   ```python
   curl = self.dependencies.direct_host["curl/8.15.0"]
   ```

   `direct_host` 是 direct+host 上下文过滤器（Conan 2.29 dependencies.py），
   `__getitem__` 支持带版本的完整引用；语义不变、可读性不降。
3. 仅直接 host 依赖可用 direct_host；build 上下文工具依赖走
   `self.dependencies.build(...)` 同样支持完整 ref。

## 判定要点

- 与 DRAFT-conan-downloader-xgzip-content-encoding 区分：那条是**真实需要**
  下载器替代方案（不让配方调 curl 的合规改法）；本条是**本就无命令调用**
  的 API 访问被正则误伤。
- 配方确有 `subprocess.run(["curl", ...])` 之类真实调用时不是误报，必须改掉。
- 佐证先例：HTGrep 配方 `self.requires("curl/8.15.0")` 正常通过 L0o。

## 实证

- libnxml-0.18.5：三处 `self.dependencies["curl"]`（generate 的 curl 变量、
  LDFLAGS 的 curl_lib、test() 的 curl_lib）改为
  `self.dependencies.direct_host["curl/8.15.0"]` 后，L0o 正则预检 0 命中，
  conan create 全链（上游测试 3/3 + test_package）CREATE=0 通过。
