# acpi-support 0.143:零编译 shell/配置包的"验证即构建"配方模式

> 草稿(DRAFT)— 来自 acpi-support 0.143 HarmonyOS PC (aarch64) 适配的真实实践。
> 与 `.kv` 同 stem 配对。

## 问题

acpi-support 0.143 是纯 shell/配置包(20 个文件:acpid 事件配置、处理脚本、
无线状态函数库、键值常量表),**不携带任何构建系统**。照搬库模板(build 跑
make/编译器)在 CI 直接失败;build() 留空又会放过截断/损坏的源码。此外:

- 上游 tarball 权限位混杂(同为 `.sh`,644 与 755 并存);
- Debian control 的 `Build-Depends: libsystemd-dev, pkgconf` 与上游源码零关系
  (那是下游 addons 打包依赖);
- 上游无测试套件,test_package 无从"对比"。

## 模式

### 1. 验证即构建(build() 语义级校验)

```python
def build(self):
    for s in ALL_SCRIPTS:                      # 5 个处理脚本 + state-funcs
        self.run(f'"{bash}" -n "{src}/{s}"')   # bash -n 全量语法校验
    # 主配置断言关键节存在
    grep -q "Suspend/hibernate method" acpi-support
    # 每份事件配置断言必需键
    for ev in events/*: grep -q "^action=" ev
```

任何截断/损坏的源在 build 阶段报错,不会静默进入 package。

### 2. 安装布局对齐 Debian + 显式 chmod

```
etc/acpi/{*.sh(0755), acpi-support(0644)}
etc/acpi/events/*           # 7 个事件定义
usr/share/acpi-support/{key-constants, state-funcs}(0644)
licenses/COPYING
```

tarball 权限混杂,package() 必须 `os.chmod` 显式对齐 Debian rules 惯例
(`find -name "*.sh" -exec chmod a+x`;函数库 `chmod a-x`)。

### 3. 依赖按上游源码事实,不按 Debian control

上游源码不引用任何 systemd 头/库,`requirements()` 留空。Debian 的
Build-Depends 是下游打包文件(addons/、systemd unit)的需要,不是上游事实。

### 4. test_package:函数库真实执行探针

```bash
. "$PKG/usr/share/acpi-support/state-funcs"
isAnyWirelessPoweredOn >/dev/null 2>&1   # 遍历 /sys/class/net
[ $? -le 1 ]                             # 0/1 均属正常执行
```

遍历型布尔函数返回值语义上 0(有)与 1(无)都是"函数正常执行",
断言应接受 `rc∈{0,1}`;配合布局断言、`bash -n` 复验、事件键检查,
8 项断言覆盖"包可用"的完整语义。

## 覆盖判断

零编译包在待领取任务池中大量存在(脚本工具/配置包/资源包)。本条目给出
这类任务的标准配方骨架;与依赖接线类条目(如
libzippp-7.1-1.10.1-cmake-module-findlibzip-cross-ohos)无主题重叠。
