# cd-discid 1.0.0 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64
- Clang 15.0.4（/data/service/hnp/bin/clang，target aarch64-unknown-linux-ohos）
- Conan 2.29.1（OHOS 适配版）
- Profile: ohos-aarch64

## Verification

- `conan-verify cd-discid 1.0.0`: PASS（G0-G4 + L2/L4/L5 八道门禁全部通过）
- W3 本地 CI（finish step 5/10）: exit 0，Pass rate 100%（1/1）
  - L0: passed（结构/语法/依赖完整性检查）
  - L1: passed（test_package 真实执行）
  - L1e R34 负向测试（破坏性验证）: passed — 移走 bin/ 后测试失败，证明测试真实依赖被测包
  - L2: skipped（cd-discid 不支持 --version/--help，非阻塞）
  - L4: passed（patches clean，0 补丁）
  - L5: passed（bin/ 产物存在）
- 上游测试：上游 Makefile 仅 all/clean/install/tarball 四个目标，**无 make check 目标、无测试套件**（已实证，见 notes.md）

## test_package

test_package/test.sh 真实运行被测二进制 cd-discid，校验其运行时行为：

- 用例 1：二进制存在且可执行（PATH 定位 + -x 校验）
- 用例 2：参数过多（a b c）→ 输出 Usage: 消息且 exit 非 0
- 用例 3：设备不存在（/dev/nonexistent-cdrom）→ open 错误消息且 exit 非 0
- 用例 4：无参数 → 默认 /dev/cdrom，输出默认设备引用且 exit 非 0

- Test cases: 4
- Passed: 4
- Failed: 0
- Skipped: 0

## Result

配方已在 OpenHarmony aarch64 环境验证通过：编译成功、test_package 真实运行验证 100% 通过、W3 本地 CI exit_code=0。状态为 built（本地验证通过，未 upload）。由于上游无测试套件，测试通过率以上游无测试 + test_package 补全验证口径统计。
