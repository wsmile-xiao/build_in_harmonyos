#!/usr/bin/env bash
# 把发行包里按目录口径数出的 508 项交给 upstream_tests.py。
# make check 仍由配方单独调用，它是空操作，不计入 N。
set -u
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
py=""
if command -v python3 >/dev/null 2>&1; then
  py=$(command -v python3)
else
  for candidate in "$HOME/.harmonybrew/bin/python3" /usr/bin/python3; do
    if [ -x "$candidate" ]; then
      py=$candidate
      break
    fi
  done
fi
if [ -z "$py" ]; then
  echo "UPSTREAM_RESULT=NO_PYTHON3"
  exit 1
fi
exec "$py" "$here/upstream_tests.py" "$@"
