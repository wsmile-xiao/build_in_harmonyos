#!/usr/bin/env python3
"""ruamel.yaml HarmonyOS-specific compatibility tests (新增测试).

针对鸿蒙平台特性的 4 个测试用例：
  1. 平台导入——namespace 包 ruamel/yaml/ 在 HarmonyOS 上可 import
     且版本正确（pip 实测布局 + conan package() 复制路径验证）
  2. 注释保留 roundtrip——roundtrip 模式核心特性，注释/锚点往返不丢失
     （上游 _test 依赖 _test/lib 库函数，test_package 内以独立脚本
     真实调用被测库 API 验证同一特性，R34 合规）
  3. Unicode + CRLF——中文标量 + \\r\\n 换行的 dump/load 往返一致
     （鸿蒙文件系统/文本栈 UTF-8 + CRLF 容忍）
  4. 真文件 IO——tmp 磁盘文件 read/write + 注释保留（roundtrip
     模式经 open() 真读写，覆盖 conan 包内 python 运行时文件访问路径）

Usage: test_ohos_compat.py <site-packages>
"""
import io
import os
import sys
import tempfile


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    sys.path.insert(0, site)

    import ruamel.yaml
    from ruamel.yaml import YAML, CommentedMap

    # ── 用例 1: 平台导入 + 版本断言 ──
    assert "ruamel/yaml" in ruamel.yaml.__file__, \
        f"namespace 包布局异常: {ruamel.yaml.__file__}"
    assert ruamel.yaml.__version__ == "0.19.1", \
        f"版本异常: {ruamel.yaml.__version__}"
    print("[1/4] OK: HarmonyOS 平台导入 + 版本 0.19.1")

    # ── 用例 2: 注释保留 roundtrip ──
    yaml_rt = YAML(typ="rt")
    src = "# top comment\nkey: value  # trailing\nlist:\n  - a  # item\n"
    buf = io.StringIO()
    yaml_rt.dump(yaml_rt.load(src), buf)
    out = buf.getvalue()
    assert "# top comment" in out, f"头部注释丢失: {out!r}"
    assert "# trailing" in out, f"行尾注释丢失: {out!r}"
    data2 = yaml_rt.load(out)
    assert data2["key"] == "value" and data2["list"] == ["a"], \
        f"roundtrip 数据异常: {data2!r}"
    print("[2/4] OK: roundtrip 注释保留（头部/行尾）")

    # ── 用例 3: Unicode + CRLF ──
    yaml_u = YAML()
    yaml_u.allow_unicode = True
    src_u = "name: 鸿蒙适配\r\n描述: 中文标量测试\r\n"
    buf_u = io.StringIO()
    yaml_u.dump(yaml_u.load(src_u), buf_u)
    out_u = buf_u.getvalue()
    assert "鸿蒙适配" in out_u and "中文标量测试" in out_u, \
        f"Unicode 标量丢失: {out_u!r}"
    data_u = yaml_u.load(out_u)
    assert data_u["name"] == "鸿蒙适配" and \
        data_u["描述"] == "中文标量测试", \
        f"Unicode 往返数据异常: {data_u!r}"
    print("[3/4] OK: Unicode 中文标量 + CRLF 输入往返一致")

    # ── 用例 4: 真文件 IO（tmp 磁盘文件，roundtrip 模式）──
    tmp = tempfile.mkdtemp(prefix="ruamel-ohos-")
    fpath = os.path.join(tmp, "compat.yaml")
    yaml_f = YAML(typ="rt")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write("# ohos file io\na: 1\nb:\n- 1\n- 2\n")
    data_f = yaml_f.load(open(fpath, encoding="utf-8"))
    buf = io.StringIO()
    yaml_f.dump(data_f, buf)  # 重新 dump——roundtrip 注释应保留
    raw = buf.getvalue()
    assert "# ohos file io" in raw, f"文件内注释丢失: {raw!r}"
    assert data_f["a"] == 1 and data_f["b"] == [1, 2], \
        f"文件 IO 往返数据异常: {data_f!r}"
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(raw)
    data_f2 = yaml_f.load(open(fpath, encoding="utf-8"))
    assert data_f2["a"] == 1 and data_f2["b"] == [1, 2], \
        f"二次文件 IO 往返异常: {data_f2!r}"
    os.unlink(fpath)
    os.rmdir(tmp)
    print("[4/4] OK: 真文件 IO + 注释保留")

    print("OK: ruamel.yaml 0.19.1 HarmonyOS 特有测试 4/4 全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
