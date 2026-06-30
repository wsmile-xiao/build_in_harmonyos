#!/bin/bash
# dfu-programmer 预处理

export TMPDIR=/data/storage/el2/base/cache
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
export LDFLAGS="-L$HOME/usr/local/lib $LDFLAGS"
export CPPFLAGS="-I$HOME/usr/local/include $CPPFLAGS"

[ -f bootstrap.sh ] && ./bootstrap.sh
