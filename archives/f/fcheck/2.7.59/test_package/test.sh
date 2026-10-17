#!/usr/bin/env sh
set -eu

fcheck=${1:?fcheck launcher path is required}
work=${2:-$(pwd)}
watched="$work/watched"
db="$work/fcheck.dbf"
cfg="$work/fcheck-test.cfg"
package_root=$(cd "$(dirname "$fcheck")/.." && pwd)
default_cfg="$package_root/share/fcheck/fcheck.cfg"
default_work="$work/default-config"

mkdir -p "$watched"
printf '%s\n' 'fcheck smoke test' > "$watched/watched.txt"

{
  printf 'Directory = %s/\n' "$watched"
  printf 'DataBase = %s\n' "$db"
  printf '%s\n' 'TimeZone = UTC'
  printf '\n'
} > "$cfg"

perl "$fcheck" -acf "$cfg"
test -s "$db"
perl "$fcheck" -af "$cfg"

mkdir -p "$default_work"
printf '%s\n' 'fcheck default config smoke test' > "$default_work/default.txt"
(
  cd "$default_work"
  perl "$fcheck" -acf "$default_cfg"
  test -s fcheck.dbf
  perl "$fcheck"
)
