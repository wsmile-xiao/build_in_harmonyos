# libmorton 0.2.12 packaging 说明

- 包类型: header-library（无编译产物，仅 include/libmorton/ 8 个头文件）
- 状态: built（本地验证通过，未执行远端发布/上传）
- 打包产物: 无二进制（header-only 库不需要 release/debug tarball）
- 验证依据:
  - conan-verify 全门禁 PASS（G1/G2/G3/G4/L2/L4/L5）
  - 上游 libmorton-test 12/12 正确性检查通过（OHOS aarch64）
  - test_package 消费者测试 23 断言通过
- 发布前置（合入 main 后由 CI 执行）: conan upload + sign
