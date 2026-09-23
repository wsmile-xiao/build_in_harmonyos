# libfuzzy2

> 基于内容触发分片哈希（CTPH）的模糊哈希库，用于识别几乎相同的文件。

ssdeep 项目的 `libfuzzy` 库：对缓冲区/文件计算模糊哈希（`fuzzy_hash_buf` /
`fuzzy_hash_filename`），并用 `fuzzy_compare` 给出 0-100 相似度。Debian
SONAME 包名为 `libfuzzy2`（对应 `libfuzzy.so.2`），本配方沿用该命名。

## 基本信息

| 项目 | 信息 |
|------|------|
| 版本 | 2.14.1（上游最新，2017-11-07） |
| 许可证 | GPL-2.0-only |
| 来源 | https://github.com/ssdeep-project/ssdeep |
| 构建系统 | autotools（发布包自带 configure） |
| 依赖 | 无运行时依赖 |
| 补丁 | 无 |

## OpenHarmony 适配要点

- 发布包自带 `configure`，无需 `autoreconf`。
- 2017 版 `config.guess` 不认识 OHOS，用
  `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos` 绕过。
- 上游 `ssdeep` CLI 硬编码 `-static`；OHOS 构建树中去掉该标志，库本身不受影响。
- 上游无自动化测试套件（`make check` 为空目标）；`test_package` 真实调用
  `fuzzy_hash_buf` / `fuzzy_hash_filename` / `fuzzy_compare` 验证。
- 实际链接库名为 `fuzzy`（`cpp_info.libs = ["fuzzy"]`）。

## 功能验证

```bash
conan create . --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 参考

- [ssdeep 官网](https://ssdeep-project.github.io/ssdeep/)
- [上游源码](https://github.com/ssdeep-project/ssdeep)
- [2.14.1 发布页](https://github.com/ssdeep-project/ssdeep/releases/tag/release-2.14.1)
