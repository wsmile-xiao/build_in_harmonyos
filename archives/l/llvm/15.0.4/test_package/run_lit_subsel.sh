#!/bin/sh
# LLVM 15.0.4 lit 入口封装 —— run_lit_subsel.sh（动态路径版，不入库）
# 包装 llvm-lit：把源码 llvm/test 映射到本目录动态 lit.cfg.py，跑 lit 子集。
set -u

PY="${PYTHON:-python3}"

# 动态解析源码根：优先 LLVM_SRC_ROOT 环境变量，否则 conan cache path llvm/15.0.4 的 dirname + /s
SRC="${LLVM_SRC_ROOT:-}"
if [ -z "$SRC" ]; then
  CONAN_PATH="$(conan cache path llvm/15.0.4 2>/dev/null | tail -1)"
  [ -n "$CONAN_PATH" ] && SRC="$(dirname "$CONAN_PATH")/s"
fi
if [ -z "$SRC" ] || [ ! -d "$SRC" ]; then
  echo "error: cannot resolve LLVM source root (set LLVM_SRC_ROOT or ensure conan cache has llvm/15.0.4)" >&2
  exit 1
fi
# 将已解析的源码根导出为 LLVM_SRC_ROOT：lit.site.cfg.py 内 exec 的动态
# test_package/lit.cfg.py（_discover_src_root）依赖该环境变量解析 SRC；
# 保留 LLVM_LIT_SRC 供 wrapper 使用。
export LLVM_SRC_ROOT="$SRC"

# 动态 lit 配置：脚本所在目录的 lit.cfg.py（其内部动态解析 SRC/PKG/SUITE）
CFG="$(cd "$(dirname "$0")" && pwd)/lit.cfg.py"
if [ ! -f "$CFG" ]; then
  echo "error: dynamic lit config not found: $CFG" >&2
  exit 1
fi

# 动态 TEST_PATH：优先显式运行时环境变量 LLVM_LIT_TEST_PATH；缺失时基于已解析 SRC
# 选择实际存在的 LLVM lit 测试子集目录（CodeGen/AArch64 → Transforms/InstSimplify 回退）。
# 不得硬编码机器绝对路径——测试路径一律基于 SRC 或环境变量构造。
TEST_PATH="${LLVM_LIT_TEST_PATH:-}"
if [ -z "$TEST_PATH" ]; then
  for sub in "llvm/test/CodeGen/AArch64" "llvm/test/Transforms/InstSimplify"; do
    if [ -d "$SRC/$sub" ]; then
      TEST_PATH="$SRC/$sub"
      break
    fi
  done
fi
if [ -z "$TEST_PATH" ] || [ ! -d "$TEST_PATH" ]; then
  echo "error: TEST_PATH missing or not a directory (set LLVM_LIT_TEST_PATH or ensure SRC contains an LLVM lit test subset)" >&2
  exit 1
fi

# wrapper 输出到受控 TMPDIR 动态工作目录；TMPDIR 缺失/不可写/mktemp 失败均明确失败，不回退系统临时目录或当前目录
if [ -z "${TMPDIR:-}" ] || [ ! -d "$TMPDIR" ] || [ ! -w "$TMPDIR" ]; then
  echo "error: TMPDIR missing, not a directory, or not writable (TMPDIR=${TMPDIR:-unset})" >&2
  exit 1
fi
ENTRY="$(mktemp -d "$TMPDIR/llvm-lit-entry.XXXXXX" 2>/dev/null)"
if [ -z "$ENTRY" ] || [ ! -d "$ENTRY" ]; then
  echo "error: cannot create lit wrapper workdir under TMPDIR ($TMPDIR)" >&2
  exit 1
fi

export LLVM_LIT_SRC="$SRC"
export LLVM_LIT_CFG="$CFG"
export LLVM_LIT_ENTRY="$ENTRY"

# 生成 lit.site.cfg.py：先执行动态 test_package/lit.cfg.py（注入 site 属性 +
# lit.llvm.initialize + llvm_config 绑定），再链式加载上游 llvm/test/lit.cfg.py，
# 保证 llvm_config 在上游配置读取前已构造。
cat > "$ENTRY/lit.site.cfg.py" <<'PYEOF'
import os
_cfg = os.environ["LLVM_LIT_CFG"]
with open(_cfg, encoding="utf-8") as _f:
    exec(compile(_f.read(), _cfg, "exec"), globals())
lit_config.load_config(config, os.path.join(os.environ["LLVM_LIT_SRC"], "llvm", "test", "lit.cfg.py"))
PYEOF

cat > "$ENTRY/llvm-lit-wrapper.py" <<'PYEOF'
import os, sys
import multiprocessing
# OHOS 上默认 spawn 对 Python 子进程 exec 报 Operation not permitted；
# fork 在平台可用列表内且不重新 exec 解释器，须在创建任何 multiprocessing.Pool
# （lit/run.py 无条件创建）之前设置，lit.main() 即使用 fork 启动方式。
multiprocessing.set_start_method("fork")
SRC = os.environ["LLVM_LIT_SRC"]
ENTRY = os.environ["LLVM_LIT_ENTRY"]
sys.path.insert(0, os.path.join(SRC, "llvm", "utils", "lit"))
from lit.main import main
config_map = {}
# lit discovery 的 getTestSuite 以「配置文件路径」为 cfgpath 并做
# realpath + normcase 后查 config_map（lit/discovery.py）。键必须与
# 上游 lit.cfg.py 配置文件路径一致，site 配置重定向才会命中。
config_map[os.path.normcase(os.path.realpath(os.path.join(SRC, "llvm", "test", "lit.cfg.py")))] = os.path.join(ENTRY, "lit.site.cfg.py")
builtin_parameters = {"build_mode": "Release"}
builtin_parameters["config_map"] = config_map
sys.exit(main(builtin_parameters))
PYEOF

if [ ! -f "$ENTRY/lit.site.cfg.py" ] || [ ! -f "$ENTRY/llvm-lit-wrapper.py" ]; then
  echo "error: failed to create lit site config or wrapper under $ENTRY" >&2
  exit 1
fi

exec "$PY" "$ENTRY/llvm-lit-wrapper.py" "$TEST_PATH" "$@"
