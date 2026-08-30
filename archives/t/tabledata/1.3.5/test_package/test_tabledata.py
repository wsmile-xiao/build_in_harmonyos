#!/usr/bin/env python3
"""tabledata consumer test (R34): import tabledata + version."""
import os
import sys


def main() -> int:
    site = os.path.join(sys.argv[1], "lib", "python3")
    sys.path.insert(0, site)
    try:
        import tabledata
    except Exception as e:
        print(f"FAIL: import tabledata: {e}", file=sys.stderr)
        return 1
    # 验证真实 API：TableData 类可用（签名 TableData(table_name, headers, rows)）
    try:
        from tabledata import TableData
        td = TableData("test", headers=["a", "b"], rows=[[1, 2], [3, 4]])
        if len(td.value_matrix) != 2 or len(td.headers) != 2:
            print("FAIL: TableData basic API", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: TableData API: {e}", file=sys.stderr)
        return 1
    print(f"OK: tabledata {tabledata.__version__} imported "
          f"(pure Python library) + TableData API works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
