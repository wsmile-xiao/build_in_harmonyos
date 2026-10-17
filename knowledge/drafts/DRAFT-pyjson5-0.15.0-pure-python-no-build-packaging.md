# DRAFT-pyjson5-0.15.0-pure-python-no-build-packaging

## 纯 Python 无编译库的 OHOS Conan 打包模式

### 问题

纯 Python 库（setuptools 打包、无 C/C++ 扩展）在 OHOS PC 上按 C/C++ 编译类配方适配
时无编译产物；框架门禁（G1 配方完整性、L1d 假测试检测）以编译类配方形态做静态检查，
直接省略 build()/export_sources() 或 CLI 参数含 true/echo/print 字面量会导致
finish conan-verify / W3 失败。

### 根因

纯 Python 库无编译产物，需按"无构建/打包族"交付；框架 G1 要求配方声明
build()/export_sources()（无编译也应提供空体 + 补丁应用调用）；L1d 用正则
`self\.run.*(echo|print|true)` 按行匹配 test_package/conanfile.py，CLI 测试表达式
与注释行中的字面量即触发误报。

### 处理方法

1. 配方：package_type=application，settings 四项，requires python/3.12.9；
   package() 中 copy json5/ → lib/python3.12/site-packages/json5/，save 生成
   bin/pyjson5 console 等价包装（shebang env python3 + 相对路径前置 site-packages
   入 sys.path，os.chmod 0o755），LICENSE → licenses/；package_id() 清空；
   runenv_info 注入 PYTHONPATH/PATH；R38 → 软件级 commands.json。
2. 门禁兼容：声明 build()（空体 + apply_conandata_patches）与 export_sources()；
   test_package self.run 行避免 echo/print/true 字面量（含注释）；
   Conan2 run() env 用 list 形式，必要时改 shell `env KEY=VAL cmd`。

### 落地

pyjson5 0.15.0 配方 archives/p/pyjson5/0.15.0/conanfile.py：conan create exit 0，
test_package CLI + 鸿蒙专项测试通过，W3/build_and_test.sh 通过，finish 通过。

### 适用范围

所有 OHOS PC 上纯 Python 库与解释型脚本 CLI 工具（只装不编）；数据/文档资源包
同理。含 C 扩展的 python 包走 build-systems.md §14（setup.py build_ext），不适用本模式。
