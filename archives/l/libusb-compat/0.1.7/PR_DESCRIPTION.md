## PR 信息
- **三方库名称**：libusb-compat
- **上游版本**：0.1.7
- **上游仓库地址**：https://sourceforge.net/projects/libusb/files/libusb-compat-0.1/libusb-compat-0.1.7/ （上游仅发布于 SourceForge，无 Git 仓库）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent
---
## 测试用例对比
### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游不包含任何测试框架或测试目录 |
| 集成测试 | 0 | 同上 |
| 其他测试 | 0 | 上游仅提供 examples/lsusb.c、examples/testlibusb.c 两个示例程序，非正式测试 |
| **合计** | **0** | 整个库仅 1 个源文件（libusb/core.c），无测试基础设施 |
### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无测试，未新增单元测试框架 |
| 集成测试 | 0 | 不变 | |
| 消费者 smoke test | 3 | +3（补全） | test_package 中 3 个断言：init/enumeration API、strerror 非空、输出格式验证 |
| **合计** | **3** | **+3** | |
---
## 上游测试用例修改说明
### 是否存在对上游测试用例的修改？
- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游无任何测试用例，不存在修改。
---
## 补全测试用例说明
### 上游是否存在无测试用例，适配后补全的情况？
- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为核心兼容层 API 补全 3 个消费者断言（smoke test）
> - **补全原因**：上游库仅包含 1 个源文件（libusb/core.c），无测试框架、无测试目录、无 CI 配置，完全依赖底层 libusb-1.0 的正确性
> - **新增测试文件清单**：
>   1. `archives/l/libusb-compat/0.1.7/test_package/test_libusb_compat.c` — 验证 usb_init()、usb_find_busses()、usb_find_devices()、usb_strerror() 四个核心 API 的链接和基本执行
>   2. `archives/l/libusb-compat/0.1.7/test_package/conanfile.py` — 测试消费者 Conan 配方，含 OHOS 二进制签名支持
>   3. `archives/l/libusb-compat/0.1.7/test_package/MANIFEST.yml` — CI 测试声明
---
## 验证结果
- 编译状态：通过
- 上游测试用例通过率：0/0（N/A，上游无测试用例）
- 新增测试用例通过率：3/3（100%）

**真机 OHOS aarch64 验证日志**：
```
libusb-compat smoke passed: init ok, busses=0, devices=0, first_bus=(none), strerror="Permission denied"
```
---
## 补充说明
- **构建系统特殊处理**：上游仅提供 autotools，因 HarmonyOS HMDFS hmmac 强制访问控制阻断 mktemp 等临时文件操作，在 conanfile.py 的 `source()` 方法中通过 `save()` + `replace_in_file()` 创建 CMakeLists.txt，不使用 patch
- **依赖**：libusb/1.0.27（已适配并在真机验证通过，87.5% 上游测试通过率）
- **安装命名**：库安装为 `libusb.so`（非 `libusb-compat.so`），pkg-config 名 `libusb`，符合上游惯例
- **issue**：待补
