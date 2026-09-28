#!/usr/bin/env python3
"""debian-gis 0.0.22 test_package —— 纯数据包，无需编译。

两级验证：
  ① **完整消费者用例**（rule12 要求）：`consumer_blend.py` 只用安装后的
     prefix，按 tasksel/blends 的既有语义把 blend 解出来 —— 读
     `share/tasksel/descs/*.desc`（tasksel 输入）→ `Parent:` 建任务树 →
     `Key:` 找 `share/blends/debian-gis/tasks/<键>` → 展开（可重复的）
     `Depends:`（`\` 续行、`|` 备选、`(>= x)` 约束）与 `X-Depends:` 跨任务引用
     → 产出最终包清单（blend-tasks.txt / packages.txt）。任一 Key 解不出、
     或清单为空即失败。
  ② **适配自检**（M=13，非上游用例）：`test_blend.py` 做数据一致性断言
     （段数/文件数/字段/logo 与安装纯净性）。上游 N=0（无测试目录、无
     autopkgtest、debian/rules 只有 dh），故 N 与 M 分列申报（R51/R53）。
"""
import os
import sys

from conan import ConanFile


class BlendTestConan(ConanFile):
    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["debian-gis"].package_folder

        # ① 完整消费者用例：端到端消费安装后的 blend 数据
        consumer = os.path.join(self.source_folder, "consumer_blend.py")
        # 不传 out_dir：只在内存走完整链路并打印结果，源码树不落任何文件
        self.run(f"{sys.executable} {consumer} {package_folder}")

        # ② 适配自检（补充，不计入上游 N）
        script = os.path.join(self.source_folder, "test_blend.py")
        self.run(f"{sys.executable} {script} {package_folder}")
