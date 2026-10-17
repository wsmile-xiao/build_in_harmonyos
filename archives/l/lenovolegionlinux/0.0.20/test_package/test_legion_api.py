#!/usr/bin/env python3
"""消费者用例（R34）：真实调用被测包内的 legion_linux API。

不看文件是否存在就下结论，而是 import 包内模块并调用真实 API：

1. ``FanCurve`` / ``FanCurveEntry`` 的 YAML 序列化往返（``to_yaml`` / ``from_yaml``）
   —— 这是用户态 CLI/GUI 读写预设文件的核心路径，且不依赖 Legion 硬件；
2. ``LegionModelFacade(expect_hwmon=False)`` 构造 —— OHOS PC 上内核模块不可用时的
   入口路径，必须可构造并如实报告特性缺失，而不是抛异常；
3. sysfs 基准路径契约 —— 内核模块接口路径的唯一来源，锁死该常量可在后续上游变更时报警。

用法：test_legion_api.py <site-packages>
"""

import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2

    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "legion_linux")):
        print(f"FAIL: packaged legion_linux missing under {site}", file=sys.stderr)
        return 1
    sys.path.insert(0, site)

    # R34: 真实 import + 真实 API 调用
    from legion_linux.legion import (  # pylint: disable=import-outside-toplevel
        LEGION_SYS_BASEPATH,
        FanCurve,
        FanCurveEntry,
        LegionModelFacade,
    )

    # 1) FanCurve <-> YAML 往返
    entries = [
        FanCurveEntry(fan1_speed=1000, fan2_speed=1200,
                      cpu_lower_temp=0, cpu_upper_temp=60,
                      gpu_lower_temp=0, gpu_upper_temp=60,
                      ic_lower_temp=0, ic_upper_temp=60,
                      acceleration=3, deceleration=3),
        FanCurveEntry(fan1_speed=3000, fan2_speed=3200,
                      cpu_lower_temp=60, cpu_upper_temp=90,
                      gpu_lower_temp=60, gpu_upper_temp=90,
                      ic_lower_temp=60, ic_upper_temp=90,
                      acceleration=3, deceleration=3),
    ]
    curve = FanCurve("ohos-consumer-check", entries)
    yaml_text = curve.to_yaml()
    if "ohos-consumer-check" not in yaml_text:
        print("FAIL: FanCurve.to_yaml() dropped the curve name", file=sys.stderr)
        return 1
    restored = FanCurve.from_yaml(yaml_text)
    if restored.name != "ohos-consumer-check":
        print(f"FAIL: name round-trip broken: {restored.name!r}", file=sys.stderr)
        return 1
    if len(restored.entries) != 2:
        print(f"FAIL: entry count round-trip broken: {len(restored.entries)}",
              file=sys.stderr)
        return 1
    if int(restored.entries[1].fan1_speed) != 3000:
        print(f"FAIL: fan1_speed round-trip broken: "
              f"{restored.entries[1].fan1_speed!r}", file=sys.stderr)
        return 1

    # 2) 无 Legion 内核接口时的入口路径
    facade = LegionModelFacade(expect_hwmon=False)
    if not hasattr(facade, "fancurve_io"):
        print("FAIL: LegionModelFacade has no fancurve_io attribute", file=sys.stderr)
        return 1
    if facade.fancurve_io.exists():
        print("FAIL: fancurve reported as existing on a host without the kernel "
              "module (fabricated feature availability)", file=sys.stderr)
        return 1
    if len(facade.fan_curve.entries) != 10:
        print(f"FAIL: default fan curve should have 10 entries, got "
              f"{len(facade.fan_curve.entries)}", file=sys.stderr)
        return 1

    # 3) sysfs 基准路径契约
    expected = "/sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00"
    if LEGION_SYS_BASEPATH != expected:
        print(f"FAIL: LEGION_SYS_BASEPATH changed: {LEGION_SYS_BASEPATH!r}",
              file=sys.stderr)
        return 1

    print("OK: legion_linux consumer API checks passed "
          "(FanCurve YAML round-trip 2 entries, facade w/o hwmon, "
          "sysfs base path contract)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
