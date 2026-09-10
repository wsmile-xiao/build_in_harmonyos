## PR 信息
- **三方库名称**：bsdsfv
- **上游版本**：1.18
- **上游仓库地址**：https://downloads.sourceforge.net/project/bsdsfv/bsdsfv/1.18/bsdsfv-1.18.tar.gz
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无测试套件（单文件 C 项目，Makefile 仅 all/install/clean/indent/tarball 目标，无 check/test 目标） |
| 集成测试 | 0 | - |
| 其他测试 | 0 | - |
| **合计** | **0** | |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | - |
| 集成测试 | 0 | - | - |
| 鸿蒙特有测试 | 6 | 新增 | test_package/test.sh：版本(-v)、创建SFV(-c -a)、校验(-T 全OK)、篡改检测(-T 1bad)、缺失检测(-T 1missing) 共 5 场景 6 断言 |
| **合计** | **6** | **+6** | |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游未提供任何测试套件（Makefile 无 check/test 目标），本次仅新增独立测试脚本，未修改上游测试用例。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为核心功能新增 SFV 创建/校验/篡改检测/缺失统计功能闭环测试（5 场景 6 断言）
> - **补全原因**：上游仅单文件 C 实现，无正式测试框架
> - **新增测试文件清单**：
>   1. `test_package/test.sh` — 版本检查 + SFV 创建（-c -a）+ 完整校验（-T 全 OK）+ 篡改检测（-T 1 bad）+ 缺失检测（-T 1 missing）

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（100%）
- 新增测试用例通过率：6/6（100%）

---

## 补充说明

- **源码来源**：官方 SourceForge 项目（downloads.sourceforge.net 实测 2026-09-05 可下载，13,301 字节真实 tarball，sha256=577245da123d1ea95266c1628e66a6cf87b8046e1a902ddd408671baecf88495 与配方声明一致）；tarball 内 bsdsfv.c `$Revision: 1.18$` 确认版本
- **源码修改（补丁 0001-bsdsfv.c.patch，2 处可移植性修复）**：
  1. `char ch` → `int ch`：getopt() 返回 int，aarch64 char 无符号导致 EOF(-1) 转 255，`ch != -1` 恒真触发 usage 死循环
  2. `int crc` → `unsigned int crc`：CRC32 高位为 1 时 sscanf(%X) 读入有符号 int 变负，与 64 位 unsigned long 比较符号扩展误判 BAD
- **依赖**：无外部依赖（纯单文件 C，仅 libc/musl）
- **验证命令与结果**：
  ```bash
  # conan create 干净构建（G1-G4 + L2/L4/L5 全门禁通过）
  conan create archives/b/bsdsfv/1.18 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

  # 功能闭环测试（test_package/test.sh，全部通过）
  bsdsfv -v                        # BSDSFV for UNiX, $Revision: 1.18 $
  bsdsfv -c -a check.sfv a.txt b.txt   # CRC 输出正确
  bsdsfv -T check.sfv              # 2 OK - 0 bad - 0 missing
  # 篡改后: -T → 1 bad；删除后: -T → 1 missing；-m → missing 统计正确
  ```
- **W3 本地 CI 模拟**：通过（exit=0）
- **W4 独立审计**：通过（P0=0，P1=0）
