# HD1-HD4 复判

候选：json-glib/1.10.8；代码/配方候选 tree `3a0851d2c21f152e2d1455d9379e66faab56ce1a`；USB HDC W3 r035 已 PASS_RETIRED。最终 staged tree 由同轮 Pre-PR 结果绑定，后续差异仅限本复判、验证报告和知识草稿。

| 条件 | matched | 当前证据与因果说明 |
|------|---------|--------------------|
| HD1_PRIVATE_OS_INTERFACES | false | 配方只使用公开 Conan、Meson、pkg-config 和公开 HarmonyOS 编译/签名工具接口；没有私有 OS 接口或未公开系统协议。 |
| HD2_PRIVATE_TOOLCHAIN | false | OHOS clang/sysroot、任务私有 Meson 1.11.1、pkg-config、native signer 与清单设备 SSH 均通过公开配置使用；没有私有工具链协议。 |
| HD3_COMPLEX_ARCHITECTURE | false | json-glib 是单一 GLib 集成库，适配修改集中在配方、依赖闭包和测试消费端，没有复杂架构迁移或多后端重构。 |
| HD4_LARGE_DEPENDENCY_TEST_COST | false | USB HDC W3 r035 后上游清单 17/17 PASS，真机闭包为 3/3、7/7、1/1、8/8，Windows-hosted OHOS `conan create --build=missing` RC 0；不满足大型依赖/测试成本条件。 |

结论：四项均有当前候选证据支持的否定理由，使用路径 A + 路径 B，Issue/PR 前缀为 `【知识库扩展】`，不申报路径 C。
