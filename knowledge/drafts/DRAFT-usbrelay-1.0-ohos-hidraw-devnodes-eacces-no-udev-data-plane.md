# DRAFT — OHOS：/dev/hidraw* 节点存在但 open 必然 EACCES，且无 udev 可放权——HID 数据面包的诚实收口模板

- **草稿 ID**：`DRAFT-usbrelay-1.0-ohos-hidraw-devnodes-eacces-no-udev-data-plane`
- **来源**：usbrelay 1.0（任务 11563，分支 `feat/usbrelay-1.0`，HarmonyOS PC 真机）
- **状态**：DRAFT，待人工审核 promote

## 一句话

鸿蒙真机上 hidraw **子系统与节点都在**（`/dev/hidraw0/1` 存在），但用户态
`open(O_RDWR)` 稳定 **EACCES**，且 Linux 生态的标准放权手段（udev 规则
`KERNEL=="hidraw*", MODE=...`）在 OHOS **整体不存在**——任何以 /dev/hidraw 为
数据面的包（继电器板、LED/DMX 控制器、厂商 HID 工具……）都会撞到同一堵墙。
本条给出三层归因顺序、探针读数字段与"编译/链接/API 可调用 + 枚举恒 0 如实
收口"的验证模板。

## 可复现症状（真机逐字，2026-09-24）

```text
/dev/hidraw0 open=-1 errno=13(Permission denied)
/dev/hidraw1 open=-1 errno=13(Permission denied)
/dev/hidraw2 open=-1 errno=2(No such file or directory)
```

配套旁证：本机 SDK `linux/hidraw.h` 无 `HIDIOCGRAWUNIQ` 宏（编译期即与桌面
Linux 有差异；探针只用 `HIDIOCGRAWNAME` 一类老宏）。

## 三层归因（缺一层就会误判）

1. **内核层**：`/dev/hidraw0/1` 真实存在 ⇒ 不是"OHOS 没有 hidraw"；
   `hidraw2=ENOENT` 划清边界（节点存在性 ≠ 全局能力）。
2. **权限层**：普通用户 `open` 即 EACCES——失败签名在 open()，**不是**枚举/协议层。
3. **放权机制层**：上游安装文档的放权路径是 udev 规则；OHOS 无 udev 守护与
   规则通道 ⇒ "装个 .rules 就能用"在鸿蒙不可移植，用户态没有合规修法
   （禁止 chmod/chown 他人设备节点，禁止按 root 演示当验证）。

后果：hidapi/直接 ioctl 的**调用链可通**（`hid_enumerate` 等不崩溃、返回空），
一切"以设备在场为前提"的功能在 CI/归档环境**不可验证**——这是平台权限模型事实，
不是包缺陷。

## 收口模板（推荐做法）

- 照常交付编译/链接/打包；消费者断言写成：
  `enumerate(...)>=0 且与 count 一致（实测 0）`、`find_board(未命中)==NULL`、
  `operate(坏路径)<0`、`shutdown() 不崩`——把"枚举恒 0"从缺陷伪装变成**断言对象**；
- `manifest.compatibility` 与 PR 正文如实写"设备控制功能面不可在 OHOS 验证 +
  三层原因"，不声称驱动成功；
- 后端可选时（hidapi libusb ↔ hidraw）公共 API 等价，`make HIDAPI=libusb`
  命令行即可覆盖上游 `=` 赋值切到已发布制品——但**切后端只解决链接面**，
  权限面照旧 EACCES，两个问题勿混谈。

## 已尝试方案（含禁止项）

| 尝试 | 结果/判定 |
|------|-----------|
| `open("/dev/hidraw0", O_RDWR)`（SSH 用户态） | ❌ EACCES（探针逐字，本条症状源） |
| chmod/chown /dev/hidraw* 放行 | **禁止**——设备节点非本窗资产，多窗口共用机器上越权改动不可接受且不可复现于 CI |
| root 环境演示"能枚举" | **禁止**——环境特权演示，评审按虚假申报打回 |
| 断言 `enumerate()>0`（依赖真实板卡） | **禁止**——CI 随机红 + 谎报可验证性 |
| 切 libusb 后端链已发布 hidapi/0.15.0 | ✅ 链接面通过（本包用法），权限面限制不变 |
| 枚举恒 0 收口 + 5 组行为断言 | ✅ 消费者 5/5（本包交付形态） |

## 适用范围 / 反例 / 风险

- **适用**：/dev/hidraw*、hidapi-hidraw 后端、`KERNEL=="hidraw*"` udev 放权类包；
  探针实测到"节点存在 + open EACCES"本签名才配此草稿（空走会被打回）。
- **反例 1**：节点整体不存在（纯 ENOENT）= 内核无 CONFIG_HIDRAW，另一条签名，
  勿混用本收口话术。
- **反例 2**：E237（特权 daemon 运行期降级族）——本签名非 daemon、失败在
  open 层、根因含"放权机制平台性缺席"，`similar_to: E237` 互指但不合并。
- **与 E008 的关系（draft-review 预审点名，score 0.30）**：E008 记录的是
  SELinux 用户域对**管道/终端/套接字等非普通文件**的 fstat()/lseek() 返 EACCES
  ——与本条同属 SELinux 策略家族、很可能共享"用户域未授权设备访问"的策略根源，
  但验证面完全不同：E008=文件操作**元数据面**（stat 类调用）；本条=**char device
  数据面 open(O_RDWR) + udev 放权通道平台性缺席 + hidapi 枚举恒 0 收口方法论**
  （探针读数、断言模板、三条禁止项均为 E008 无记载的新内容）。两条目互补共存、
  互相 similar_to 指认，合并任何一侧都会丢掉对面的操作面签名与修法。
- **风险**：低。模板只界定"验证面话术"，不改任何上游逻辑；未来 OHOS 若提供
  HID 用户态授权机制，本条自然降级为历史记录（解除条件：open 不再 EACCES）。

## 查重与新增价值

- 四范围（2026-09-24）：`knowledge/graph/index.tsv` 全 766 行 `hidraw` **0 命中**
  （派单轮已量化：uinput/input_event//dev/input/gpio/i2c/termios/thermal/nvme/
  inotify 等 27 个内核接口面全 0——OHOS 设备数据面知识系统性空白，本条是第一块）；
  `经验文档/适配经验汇总.md`、`适配检查清单.md`、`B草稿库/` 均无 hidraw/EACCES
  放权主题；E237 为 daemon 降级族不同签名（上节已论证）。
- draft-review：随 PR 提交后补跑并回填建议与差异论证。
- 新增价值：给出"三层归因顺序 + 逐字探针读数 + 诚实收口断言模板 + 三条禁止项"，
  让后续 27 个内核接口面族包有第一套可复制的数据面处理范式，而不是各自在
  "谎报可用/越权改权限/随机红灯"之间三选一。

## 关联

- 同 PR 实证包：`archives/u/usbrelay/1.0`（notes.md 问题表 003 + 探针段）
- 同 PR 关联 Issue：见 PR 正文回填
- 相关既有族：E237（互指）、libusb 后端切换手法（notes 001 行，附带修正
  "make 命令行不能覆盖 `=` 赋值"的旧误判——实测可覆盖，`override` 指令才屏蔽）
