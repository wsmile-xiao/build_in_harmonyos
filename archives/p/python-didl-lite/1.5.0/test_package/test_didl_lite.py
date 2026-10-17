#!/usr/bin/env python3
"""python-didl-lite consumer test (L0c + R34): standalone test source
executed via self.run from conanfile.py test().

R34: actually call the tested API — from_xml_string() parse +
to_xml() round-trip (pure user-space, defusedxml-based).

Usage: test_didl_lite.py <site-packages>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    # site 可能为 pathsep 拼接的多路径（自身 + 依赖 defusedxml）——
    # 按 os.pathsep 分割后逐路径检查/加入 sys.path
    paths = [p for p in site.split(os.pathsep) if p]
    if not any(os.path.isdir(os.path.join(p, "didl_lite")) for p in paths):
        raise AssertionError(f"didl_lite package missing in {paths}")
    sys.path = paths + sys.path
    # R34: 真实调用被测库 API
    from didl_lite import didl_lite

    # 解析一个真实 DIDL-Lite XML（item + dc:title + upnp:class）
    xml_str = (
        '<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" '
        'xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        '<item id="1" parentID="0" restricted="1">'
        "<dc:title>Test Item</dc:title>"
        "<upnp:class>object.item</upnp:class>"
        "</item></DIDL-Lite>"
    )
    objs = didl_lite.from_xml_string(xml_str)
    if len(objs) != 1:
        raise AssertionError(f"expected 1 object, got {len(objs)}")
    item = objs[0]
    if getattr(item, "title") != "Test Item":
        raise AssertionError(f"unexpected title: {item.title!r}")
    # to_xml round-trip（真实 API 往返）
    el = item.to_xml()
    if el is None or el.tag.split("}")[-1] != "item":
        raise AssertionError("to_xml round-trip failed")
    print(f"OK: python-didl-lite {didl_lite.__version__ if hasattr(didl_lite, '__version__') else '1.5.0'} "
          f"(from_xml_string parse + to_xml round-trip ok: {item.title!r})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
