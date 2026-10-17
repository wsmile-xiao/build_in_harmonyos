# DRAFT-yazpp-1.9.2-config-script-baked-prefix

## 症状（可复现 + 稳定签名）

消费 Index Data 系制品包（yaz → yazpp 同构造传导）时：

- `yaz-config --cflags` 输出 `-I//include`（双斜杠空 prefix），
  且 libxml2 的 `-I/-L` 指向打包机的陈旧绝对路径（`~/.conan2/p/...`）；
- 下游编译报 `fatal error: 'yaz/log.h' file not found`；
- 链接/运行期报 `Error loading shared library libxml2.so.16 (needed by ...)`
  或 `xmlInitParser: symbol not found`。

## 根因与最小复现

`make install` 打包时 config 脚本把 configure 期的 `prefix` 字面量烤进正文
（实测 yaz 制品包内 `yaz-config` 第 6 行 `prefix="/"`）；conan 制品化流程在
CI 打包环境里没有真实 package_folder 可写，于是烤进 "/"，对二级依赖
（libxml2）更是烤进了打包机的陈旧 home 绝对路径。下游一切按脚本取 flags 的
消费方式（autotools `--with-yaz=DIR`、pkg-config、直接 shell 调用）全部拿到
失效路径。

最小复现：`<yaz 包>/bin/yaz-config --cflags` → 观察 `-I//include`。

## 已尝试方案（含失败）

- `yaz-config --prefix=<真实包路径> --cflags`：**实测无效**——脚本虽解析
  --prefix，但 cflags/libs 的输出计算不读运行时 prefix（沿用烤死的
  `includedir` 变量），输出原样 `-I//include`。
- 直接用脚本 + 手工补 -I/-L：可行但把修正逻辑泄漏到每次消费，不可复用。

## 最终方案（真实验证）

配方 `generate()` 里以 `self.dependencies` 的 cpp_info 派生真实路径，在**私有
build_folder** 生成修正版 `yaz-config` shim（R49：依赖注入只走私有目录，
不碰共享前缀、不改写依赖包缓存），configure 传 `--with-yaz=<shim 目录>`。
测试运行期以 `VirtualRunEnv` 注入依赖库 LD_LIBRARY_PATH。

验证：yazpp 1.9.2 真机构建——configure 原生探测 YAZ 5.37.3、编译/链接/上游
测试（src/check 2/2）/消费者测试全绿；conan-verify 8 门禁全过。

## 适用范围 / 反例 / 解除条件 / 风险

- 适用：消费"制品包内 config 脚本烤死 prefix"的一切下游（Index Data 全家：
  yaz/yazpp/yaz-python…，以及其他以 make install 产 config 脚本的包）。
- 反例：本地源码构建后直接使用（prefix 真实）无需 shim；meson/pkg-config
  场景的同签名问题按 E355 处理。
- 传导警告：**yazpp 自身安装的 yazpp-config/yazpp.pc 同样烤死 prefix=/，
  会把本陷阱传导给 yazpp 的下游**——下游应对方式相同。
- 风险：shim 输出的 flags 集合需与上游脚本对齐（新增依赖时同步维护）。

## 查重与新增价值（组合型知识）

- E355 记录了 `-I//include`/`prefix=/` 签名，但解法是 meson 平台补丁
  （patch-meson-platform），不覆盖 autotools + shell config 脚本消费场景。
- 本条目是同一签名在 **autotools/config-script 语境**下的根因定位
  （脚本烤死 prefix + 运行时覆盖无效实测）与三条接法的取舍——组分不同、
  解题路径不同，按组合型知识 create 申报。
