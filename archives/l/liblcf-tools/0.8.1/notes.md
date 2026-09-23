# liblcf-tools 0.8.1 适配笔记

## 软件与来源

- 软件：liblcf-tools
- 上游项目：EasyRPG liblcf
- 上游版本：0.8.1
- URL：`https://github.com/EasyRPG/liblcf/archive/refs/tags/0.8.1.tar.gz`
- SHA-256：`5ec89082d54f1a29d23fed54de70acab4375036d57828ff0fc7a88b81833d40f`
- 构建系统：CMake，C++17
- 目标：`aarch64-unknown-linux-ohos`
- 包类型：application/tool
- 当前状态：built（未上传 Conan 制品）

## 适配范围

上游源码无需修改，采用其原生 CMake 工程。配方打开
`LIBLCF_ENABLE_TOOLS` 和 `LIBLCF_WITH_XML`，构建并安装 `lcfstrings`、
`lcf2xml`；liblcf 本身作为内部静态目标参与链接，包中不发布开发库和头文件。

启用的 Conan 依赖为：

- `expat/2.8.2.1`：XML 解析（运行时为 OHOS 动态依赖，由 Conan consumer 环境提供）。
- `inih/r58`：上游 INI reader 及其测试。
- `icu4c/77`：静态 Unicode 编码转换。

OHOS 的默认 locale 编码路径如果关闭 ICU 会进入上游非 ICU 转换实现；该路径在
设备上会错误跳过 ASCII 字节。因此本包保留 ICU，并在配方中将 `ICU_ROOT` 指向
Conan 依赖，确保 `find_package(ICU COMPONENTS i18n uc data)` 使用已验证的
OHOS 静态 ICU。CMake 4.x 兼容性通过 `CMAKE_POLICY_VERSION_MINIMUM=3.16`
设置解决。

## 构建与测试

在 OHOS PC 设备上使用 `ci/conan/profiles/ohos-aarch64` 运行了 Conan 2
`conan create`，并以 `CI_PACKAGES=archives/l/liblcf-tools/0.8.1` 运行了
`zsh ci/conan/build_and_test.sh` 的定向 W3 模拟。由于该设备到 GitHub 的连接
在部分时段超时，执行验证阶段使用同一 SHA-256 的已下载官方源码归档作为本地
传输输入；提交的 `conandata.yml` 仍只保留官方 HTTPS URL 和准确校验和，CI 可
按该元数据重新下载。

配方的 `build()` 依次执行：

```text
cmake --build <build> --target tools
cmake --build <build> --target check
```

上游没有 CTest 测试注册，而是通过 `check` custom target 执行 doctest runner。
OHOS 设备结果：

- 上游 doctest：59/59 test cases，693/693 assertions，0 failed，状态 SUCCESS。
- W3 定向 CI 模拟：L0 PASS、L1 PASS、L5 PASS，JC6 单软件原子性 PASS；
  L2 对两个不提供 0 返回码的上游 usage 入口给出非阻塞 skip，功能测试仍由
  consumer 完成。
- Conan consumer：1/1，通过已安装的 `lcfstrings`、`lcf2xml` 做 usage 检查，生成
  空 LMT XML 的 XML→LCF（`.lmt`）→XML（`.emt`）round-trip，并让 `lcfstrings`
  读取生成的 LCF。
- consumer 将两个已安装 ELF 复制到隔离临时 `bin/`，再用 `llvm-objcopy` 移除
  旧签名、由 `binary-sign-tool` 自签；使用 `llvm-readelf` 确认每个副本只有一个
  `.codesign` 段后再执行，不修改 Conan package cache。另行扫描已安装包确认两个
  ELF 均为 PIE、NX、GNU_RELRO+BIND_NOW。

测试 fixture 使用显式空 LMT 结构，且通过 ICU 保持默认编码路径可用；并非把
`--help` 输出当作唯一功能测试。

## 交付文件

- `conanfile.py`
- `conandata.yml`
- `manifest.yaml`
- `notes.md`
- `test_package/conanfile.py`
- `test_package/test.sh`
- `test_package/MANIFEST.yml`
- `reports/test-report.md`（本地验证报告，报告目录按仓库规则忽略）
- 软件级 `README.md`
- 软件级 `manifest.yaml`
- `commands.json`

## 限制与未声明事项

- 未上传 Conan 制品，manifest 保持 `status: built`，commands manifest 的
  `binary` 保持 `false`。
- 未宣称上游不存在的工具测试、CTest 结果或 CI/平台发布结果。
- AtomGit PR、AI review、人工审核、测试审核、CI 和平台积分需在提交后分别以
  服务端状态确认。

## 结束

- OHOS Conan build/check/consumer：完成
- 上游测试：59/59，693/693 assertions
- consumer：1/1
- conan-verify：G0/G1/G2/G3/G4 PASS；因 verifier 对连字符包名的 cache
  路径提取限制，L2/L4/L5 按“无 cache 路径”跳过；功能与 ELF 安全检查已手工补验。
- 最终状态：built（等待 PR 与平台审核，不声明 published）
