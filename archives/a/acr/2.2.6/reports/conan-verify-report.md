# acr 2.2.6 Conan 验证记录

## 环境与结果

| 项目 | 配置 | 结果 |
|---|---|---|
| 静态配方检查 | Python 3.12，YAML + `static_recipe_check.py` | 通过，0 warning |
| Conan Release | Linux x86_64，GCC 14，Conan 2.30 | 通过 |
| Conan Debug | Linux x86_64，GCC 14，Conan 2.30 | 通过 |
| Conan OHOS | OHOS 6.0 armv8，Clang 15，Conan 2.29.1 | 通过 |
| PC 模拟器 | HarmonyOS PC，HDC `127.0.0.1:5555` | 7/7 断言通过 |

## OHOS 包标识

```text
acr/2.2.6@ohpcd/stable
package_id=6b129b068851896169fae42d399fa922d239ce8a
```

## 验证要点

- 源码下载的 SHA-256 与 `conandata.yml` 一致。
- 5 个补丁按顺序干净应用。
- Linux 每次构建都在一次性源码副本中运行 12 个 triplet 与 18 个 examples。
- triplet 验证同时检查退出码和 `FAIL` 文本，防止假通过。
- `test_package` 验证已打包的 `acr`，不是直接调用源码树脚本。
- OHOS 跨构建不伪报运行；实际运行由 PC 模拟器脚本完成。
- 缺失输入必须返回非零，作为故障注入验证。
