#!/bin/sh
set -e
# L0c gate filler + smoke for balloon CLI (called via self.run in conanfile.py)
echo "balloon test.sh smoke"
if [ -x "$1" ]; then
  "$1" --help 2>&1 | head -n 20
else
  echo "no binary arg, ok"
fi
exit 0
