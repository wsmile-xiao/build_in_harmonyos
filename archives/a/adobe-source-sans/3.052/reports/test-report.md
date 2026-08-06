# Test Report — adobe-source-sans 3.052

## 1. 上游测试统计

| 项目 | 数量 |
|------|------|
| 上游自动化测试（test 文件/目标/用例） | 0 |
| 上游测试文件数 | 0 |
| 上游测试目标数 | 0 |
| 上游测试用例数 | 0 |
| 上游断言数 | 0 |

**依据**：上游 tag `3.052R` 归档（source-sans-3.052R.tar.gz）仅含字体发布物
（TTF/OTF/VF/WOFF/WOFF2 + LICENSE.md + README.md + package.json + css），
**无 test/tests 目录、无测试框架引用、无 CI test job**。纯字体数据包，发布物即字体文件，
上游自动化测试数量为 0（不是"通过 0 个测试"，而是"无自动化测试存在"）。

## 2. 适配后测试（Conan L1 test_package 烟雾测试）

| 项目 | 数量 |
|------|------|
| test() 方法 | 1 |
| 断言总数 | 45 |
| 通过 | 45 |
| 失败 | 0 |
| 通过率 | 100% |

**断言构成**：
- 14 个 TTF 文件存在（SourceSans3-Black/BlackIt/Bold/BoldIt/ExtraLight/ExtraLightIt/It/
  Light/LightIt/Medium/MediumIt/Regular/Semibold/SemiboldIt.ttf）
- 14 个 TTF 文件非空
- 14 个 TTF 文件 TTF magic（0x00010000）校验
- LICENSE.md 存在
- LICENSE.md 非空
- 目录内 TTF 文件数 == 14

## 3. 平台 smoke test（conan create + test_package 实跑）

```text
✅ All 14 font files + LICENSE.md verified in <pkg>/share/fonts/SourceSans3
```

- **执行**：`conan create archives/a/adobe-source-sans/3.052 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing --user=ohpcd --channel=stable`
- **结果**：退出码 0，字体文件安装到 `share/fonts/SourceSans3/`，14 个 TTF + LICENSE.md 全部验证通过
- **日志**：`reports/conan-create.log`

## 4. 结论

- 上游测试：0（无自动化测试）
- 适配后新增测试：1 个 test() 方法、45 个断言，100% 通过
- 平台 smoke test：通过（conan create 退出码 0，test_package 断言全过）
