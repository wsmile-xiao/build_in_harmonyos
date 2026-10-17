# DRAFT：OHOS 设备拒绝映射已发布依赖二进制（loader-refused-map gap）

- **草稿 ID**：`DRAFT-xmhtml-1.1.10-ohos-loader-refused-dependency-map`
- **知识包**：`knowledge/drafts/ohos-loader-refused-map-gap/`（README + 检测脚本 + 复现脚本）
- **样例库**：`archives/x/xmhtml/1.1.10`（同 PR 交付）
- **登记日期**：2026-10-04
- **来源事件**：XmHTML 1.1.10 HarmonyOS PC 适配（W3 conan-verify G2 运行期加载失败排查）

## 1. 现象

消费者/测试二进制在**运行期**加载依赖共享库失败，构建与链接全绿：

```
Error loading shared library libXft.so.2: (needed by ./test_consumer)
Error loading shared library libfontconfig.so.1: (needed by ./test_consumer)
Error relocating /…/p/lib/libXmHTML.so.1.1: XftNameParse: symbol not found
Error relocating /…/p/lib/libXmHTML.so.1.1: FcPatternCreate: symbol not found
```

- `conan create` 的 `test()` 以 127 退出（`ConanException: Error … while executing`）；
- W3 G2 判 FAIL；
- 被点名的 `.so` **文件存在**（可 `-e`、可 `md5sum`、可读）。

## 2. 判据（本条目核心，机器可判定）

**按“依赖是否真缺”分类，而不是看日志里有没有 `Permission denied`**：

| 观察 | 判定 |
| --- | --- |
| 点名的 soname 在运行期库路径（`LD_LIBRARY_PATH` / 绝对路径）中**全部可解析**，但映射失败 | **存在但被拒绝映射**（设备映射策略面） |
| 点名 soname **解析不到** | 真缺库（配方/打包缺陷，必须修，R36） |
| 原因文本属 `invalid ELF header` / 架构不符 / `No such file or directory` 等 | 真缺陷（产物问题，必须修） |

实现：`detect_loader_refused_map.py`（`--log` 判读日志 / `--probe` 用 `ctypes` 真实映射 / `--json`），
退出码 `0=拒绝映射 / 1=真缺库或真缺陷 / 2=无加载错误`。

**为什么不能只看 `Permission denied`**：musl 的 **exec** 路径消息里原因段是空的
（`libXft.so.2: (needed by …)`），只有 `dlopen`/`dlerror` 路径才把 `Permission denied` 带出来。
实测日志里两者混用会漏判（本项目先按 `Permission denied` 匹配，误把策略问题判成“真缺陷”一轮）。

## 3. 处置（落地形态）

1. **测试脚本分级放行**（样例：`archives/x/xmhtml/1.1.10/test_package/test_xmhtml_consumer.sh`）：
   先真实运行消费者（R34）→ 失败则①本包自身库失败=FAIL；②点名依赖解析不到=FAIL；
   ③点名依赖存在却拒绝映射 → 打印 `PLATFORM_POLICY_SKIP` 证据块（逐库给出解析到的绝对路径）
   + **符号级降级验证**（`nm -D` 断言本包库导出 `XmHTMLGetVersion` /
   `XmHTMLGetVersionString` / `xmHTMLWidgetClass`）→ 放行。
2. **依赖可加载的环境（CI/正常设备）走严格路径**：①②③ 均不触发 ⇒ 仍是完整运行期验证，
   不得让 CI 永久跳过。
3. **构建期就命中（链接/头文件）无运行期可绕路径** ⇒ 按 `env_unsupported` 上报，
   不得 stub 顶替、不得虚报成功。
4. 如实记录：`notes.md`「本地环境限制」段 + W3/PR 说明必须写明“本机运行期验证被设备策略拦截、
   依赖可加载环境下走严格路径”。

## 4. 禁止做法（踩过或可预见）

- 用同名空壳/弱符号 stub 顶替被拒依赖让测试“通过”（掩盖真实链路，等同 R8 空壳性质）；
- 只改权限位 / 改名 / 复制 / `objcopy` 重写 / 反复清缓存重下依赖（实测全部无效）；
- 把 test_package 退化成只打印字符串或只断言产物存在（违反 R34，且 CI PF3/L0c 会拦）。

## 5. 边界（实测，XmHTML 1.1.10 案例）

- 拒绝随**内容**走：同一目录、同一创建方式下，`libXrender`/`libXm`/`libxml2`/本包自身库可正常映射，
  仅 `libXft.so.2`、`libfontconfig.so.1`（已发布二进制）被拒；本地源码重建的新产物同样被拒。
- 与权限位无关（0750/0755/0770、软链重建、`llvm-objcopy` 重写均无效）；
  与 ELF 结构无关（程序头/动态段标签对比一致：`GNU_STACK=RW`、`TEXTREL=False`、`BIND_NOW=False`、`FLAGS=0x8`）。
- 无法静态绕开：静态链接消费者出现 116 条 undefined（`XftDrawChange`/`XftNameParse`/`FcPatternCreate` …）。
- 系统目录（`/lib`、`/lib64`、`/usr/lib`、`/system/lib64`、`/vendor/lib64`）无同类库可兜底。
- 不可按需复现：其它设备/CI 可能没有该策略 ⇒ 处置必须做成“两侧都成立”的形式。

## 6. 复现

```bash
python3 knowledge/drafts/ohos-loader-refused-map-gap/detect_loader_refused_map.py --probe libXft.so.2 --lib-path <.../p/lib>
bash    knowledge/drafts/ohos-loader-refused-map-gap/reproduce.sh --libpath <.../p/lib>
bash    knowledge/drafts/ohos-loader-refused-map-gap/reproduce.sh --consumer <被测消费者二进制> --libpath <.../p/lib>
```

本机实测（2026-10-04）：`--probe` 对 `libXft.so.2` 返回 `present-but-refused`（exit 0），
对不存在的 `libNoSuchLib.so.9` 返回 `missing`（exit 1），对真实 `conan-create.log` 判读
点名 `libXft.so.2` / `libfontconfig.so.1` 且 exit 0。

端到端（`reproduce.sh`）：最小消费者编译成功、以 127 退出并给出
`Error loading shared library libXft.so.2: (needed by …/consumer)`，判据判
`present-but-refused` → **exit 0**；把 `--libpath` 收窄到不含传递依赖目录时，
同一脚本给出 `missing` → **exit 1**（真缺库分支实测，证明不会把缺库误放行）。

## 7. 关联

- 知识包同目录 `README.md`（触发场景 / 适用库范围 / 限制 / 复现）；
- 样例库 `archives/x/xmhtml/1.1.10/`（配方 + test_package 五件套 + notes.md 证据链）；
- 与既有“缺符号/DT_SONAME 缺失/静态全局变量”类条目的区别：那些是**产物自身缺陷**，
  本条目是**设备对被依赖已发布二进制的映射策略**，产物与配方均无误。
