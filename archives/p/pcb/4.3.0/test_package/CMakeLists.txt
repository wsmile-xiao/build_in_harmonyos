cmake_minimum_required(VERSION 3.15)
# pcb 4.3.0 test_package —— 测试驱动为 run_pcb_tests.sh（shell），
# 计数口径（14 断言，与 conanfile.py docstring / run_pcb_tests.sh /
# MANIFEST.yml / 版本 manifest.yaml / PR 描述同步）:
#   [UP] 上游行为复现 3 场景 7 断言（bom/bom_md/IPC-D-356 导出，
#        输入+golden 取自上游 tests/，日期/版本/作者行归一化后逐字节比对）
#   [NEW] 新增错误路径/边界 7 断言（缺文件/坏输入/未知 HID/未知选项/
#        version/help/空板）
# 本文件仅作计数声明；实际执行由 test_package/conanfile.py test() 调
# run_pcb_tests.sh 完成（二进制调用, 无 cmake 构建）。
project(pcb_test NONE)
