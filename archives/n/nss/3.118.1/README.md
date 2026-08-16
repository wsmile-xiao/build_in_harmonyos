# nss 3.118.1

Mozilla Network Security Services（NSS）— 网络安全服务库，提供密码学、TLS/SSL、S/MIME 支持。

## HarmonyOS PC (aarch64) 适配

- **构建系统**: make（NSS coreconf 体系）
- **依赖**: nspr/4.37
- **状态**: published
- **适配要点**: 新增 coreconf/HarmonyOS.mk（clang 工具链 + OHOS 宏）；arch.mk/config.mk 增加 HarmonyOS 平台识别；DIRS 裁剪跳过 cmd 工具

## 使用

```python
# conanfile.py
from conan import ConanFile

class FooConan(ConanFile):
    def requirements(self):
        self.requires("nss/3.118.1")
```

## 测试

```bash
conan create . --user=ohpcd --channel=stable --build=missing
# L1 test_package: NSS_GetVersion() 版本断言 + 库链接/加载
```
