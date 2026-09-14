# draft-magic-db-load-path-fallback

libmagic 运行时 magic 数据库四路加载路径在 Conan 包部署下仅 MAGIC 环境变量回退可用——
CWD 相对路径/编译期默认路径/显式路径均不可靠，消费者必须随包部署与链接 libmagic 严格
同版本的 magic.mgc 并以 runenv 注入 MAGIC。

## 症状

以 Conan 包消费 libmagic（file/x.y.z）的应用在目标机上运行时，文件分类静默失效：

```
Could not load file magic database file 'magic', using default database
Warning: using regular magic file `//share/misc/magic'
... found 0 files          # 镜像中明明含有可识别文件
```

无崩溃、无退出码异常（以 dares 为例，除 autosave 路径外恒 exit 0），核心功能
（文件类型识别/抢救）整体失效而非边缘告警。

## 根因：四路加载路径矩阵（逐一实证）

libmagic `magic_load` 按四路顺序定位数据库；「Conan 前缀隔离部署 + OHOS 无系统级
/share/misc」下前三路全部失效：

| 路 | 机制 | 实测结果（2026-09-11 设备对照实验） |
|---|---|---|
| 1 | 消费者硬编码相对路径（dares `MAGIC_FILE "magic"`，只查 CWD） | 放入上游自带老式 magic → 解析告警超限 load 返回 -1 → `found 0 files`；放入编译版 magic.mgc → `apprentice_map` 拒绝映射、按源格式重解析二进制亦失败 → 仍 `Could not load` + `found 0 files`（**显式路径加载必然失败**） |
| 2 | 编译期默认路径（libmagic 构建机包前缀） | 预编译 redistrib 后打开 `//share/misc/magic` 失效 → `found 0 files` |
| 3 | 上游随源码分发的 magic/magic.mime（file-3.x 时代语法，11058 行） | libmagic 5.48.1 下告警超限 load -1，分类整体失效 |
| 4 | `magic_load(cookie, NULL)` 回退链读 `MAGIC` 环境变量 | `MAGIC=<file/5.48.1 包内 magic.mgc>` → `found 1 files`、真实分类 "ASCII text"、`.asc` 落盘 ✅ **唯一可用** |

机理归类：非业务库 quirk——锚定 libmagic `magic_load` 实现顺序 + Conan 部署语义，
与具体消费者无关；dares 0.6.5（仓内首个 `-lmagic` 消费者）仅为本 run 案例括注。

## 修复（rec：copy-dep-magic-mgc-plus-runenv-magic）

消费者 conan recipe 两步：

1. `package()` 从 file/x.y.z 依赖包复制编译版数据库到本包（数据与链接的 libmagic
   **严格同版本**——继承 E546 的版本绑定不变量，避免跨版本 mgc 格式问题）：

```python
copy(self, "magic.mgc",
     src=os.path.join(self.dependencies["file"].package_folder, "share", "misc"),
     dst=os.path.join(self.package_folder, "share", "dares"))
```

2. `package_info()` 经 runenv 注入 `MAGIC`，命中路 4 回退链，任意 CWD 皆可分类：

```python
self.runenv_info.define_path(
    "MAGIC", os.path.join(self.package_folder, "share", "dares", "magic.mgc"))
```

## 回退（fallback：regen-source-magic-consumer-cwd）

以 file 包源格式 magic 重新生成**本 libmagic 版本可解析**的源格式数据库，放入消费者
进程 CWD 名为 `magic`（喂给路 1）。诚实权衡：这只是掩盖消费者「数据在 CWD」的上游
假设而非修复它；源格式解析随版本漂移脆弱（告警超限即整体失败）。仅适用于无法注入
环境的宿主场景，不替代 rec 方案。

## 禁止

- **禁止打包上游随源码分发的 file-3.x 时代 magic/magic.mime**：libmagic 5.48.1 下
  加载必失败，且把回退路径指向必失败文件，比不打包更难排查（存在看似合法的数据库文件）。
- **禁止把设备/包绝对路径写进源码 MAGIC_FILE 等编译期常量**：违反移植规范，补丁不可
  复现、路径随环境漂移；Conan 包路径必须经依赖包路径探测 + runenv 注入解决。

## 自包含复现探针（verification_cmd，开新 shell 可跑）

前置：仓库根目录（含 `archives/d/dares/0.6.5` 与 `ci/conan/profiles/ohos-aarch64`），
conan 可用；conan home 非默认时从 create 日志 "Package folder" 行取包路径。

```sh
conan create archives/d/dares/0.6.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build='dares/*'
DARES_PKG=$(ls -d ~/.conan2/p/b/dares*/p | head -1)
FILE_PKG=$(ls -d ~/.conan2/p/file*/p | head -1)
W=$(mktemp -d) && cd "$W" && printf 'dares smoke test\n%.0s' {1..640} > image.img

# 探针1（失败面·路2 编译期默认路径）：无 MAGIC、无 CWD magic
env -u MAGIC "$DARES_PKG/bin/dares" -a -i image.img -s out1 -l l1.log
grep 'found 0 files' l1.log          # 且日志见 //share/misc/magic 告警

# 探针2（机理面·路1 显式路径）：CWD 放编译版 mgc，显式路径加载仍失败
cp "$FILE_PKG/share/misc/magic.mgc" ./magic
env -u MAGIC "$DARES_PKG/bin/dares" -a -i image.img -s out2 -l l2.log
grep 'found 0 files' l2.log          # 且见 "Could not load ... 'magic'"

# 探针3（修复面·路4 MAGIC env 回退）：真实分类 + 抢救落盘
MAGIC="$DARES_PKG/share/dares/magic.mgc" "$DARES_PKG/bin/dares" -a -i image.img -s out3 -l l3.log
grep 'found 1 files' l3.log && ls out3/*.asc
```

## 适用范围

- 任何以 Conan 包静态消费 libmagic（file/x.y.z）且运行时需要文件类型分类的 OHOS 应用
  （`package_type=application` 的 `-lmagic` 消费者尤甚）；
- 更广的同类问题：「静态链接依赖的运行时数据资源闭合」——tzdata、glibc locale、
  ASN.1 表、字体配置等带编译期资源路径/数据数据库的静态依赖同理。

## 实证记录与诚实边界

- 来源 run：oh-device-porting-v2 `dares-0.6.5`（2026-09-11）；修复落地后权威 CI 一次
  PASS（L0-L5 全过，R34 负向测试确认 test 真实依赖被测二进制）。
- 诚实边界：本条为 L1 单库首例；阻塞面证据是设备对照实验矩阵 + 上文自包含探针，**不是
  CI 失败日志**（修复先行，CI 未见过失败态）。promote 前建议实跑探针 1/2 复现失败面。
- dares 退出码语义（autosave exit(1)、其余恒 0）属库内 quirk，记录于
  `archives/d/dares/0.6.5/notes.md`，不在本条展开。

## 相关

- **E499**（Conan 共享包消费者需显式传递运行时 libdirs）：思想同族——运行时闭包需
  生产者显式传播；对象不同：E499 是 .so 搜索路径（NEEDED 闭包），本条是数据资源文件
  （数据闭包）。
- **E464**（MyGUI 无头测试资源注册缺失致自旋）：资源缺失致运行期功能失效形态同族；
  对象是引擎内部资源注册而非依赖库数据数据库。
- **E546**（libmagic/file 5.48 构建期数据生成器，草稿）：处理构建期 mgc 如何生成
  （FILE_COMPILE 角色区分）；本条处理运行期消费者侧部署，阶段/机理/方案三重不重叠，
  互补——本条 rec 继承其「数据与解析器版本绑定」不变量。
- **principles：P009**（P-RUNTIME-002，运行时闭包完整性：RPATH 覆盖所有 NEEDED 库），
  语义同族推广到数据资源；最终挂钩取舍由知识库主编终裁。
