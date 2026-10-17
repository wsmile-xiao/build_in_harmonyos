# oflib 0git20070620 测试报告

## 测试口径

- 上游正式测试：0（源码清点确认无自动化测试入口）。
- 上游示例：3 个，仅作为示例清点，不计入正式测试通过率。
- 适配测试：4 个运行场景，共 37 个实断言，其中 1 个为 HarmonyOS PC 特有场景。

## 验证命令

```sh
conan create archives/o/oflib/0git20070620 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=oflib/0git20070620
```

## 验证结果

| 层级 | 结果 |
|------|------|
| HarmonyOS PC AArch64 共享库构建 | 通过 |
| Conan 打包与 CMakeDeps 消费 | 通过 |
| uint32 场景 | 6/6 |
| uint64 场景 | 5/5 |
| 合成设备树场景 | 21/21 |
| HarmonyOS PC 特有场景 | 5/5 |
| 新增测试合计 | 37/37（100%） |
