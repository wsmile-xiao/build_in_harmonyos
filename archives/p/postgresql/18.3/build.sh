#!/data/service/hnp/bin/bash

pkgname=postgresql
pkgver=18.3
buildsystem="autotools"
depends=("icu" "tzdb")
makedepends=()
source="https://ftp.postgresql.org/pub/source/v18.3/postgresql-18.3.tar.bz2"
builddir=$pkgname-$pkgver
ARCH=${ARCH:-aarch64}

download_and_extract() {
    local url=$source
    local filename=$(basename $url)

    # 检查压缩包是否存在
    if [[ -f $filename ]]; then
        echo "$filename压缩包已存在，跳过下载: $filename"
    else
        echo "$filename不存在，下载源码: $url"
        curl -L -o $filename $url
    fi

    # 解压,hmdfs 不支持硬链接，忽略硬链接错误
    echo "解压: $filename"
    tar -xf $filename 2>/dev/null
}

prepare() {
    download_and_extract

    # 应用鸿蒙适配补丁
    patch -d $builddir -p1 < postgresql_harmony.patch

    # 优先考虑外部目录构建，不支持时才考虑原地构建
    mkdir -p $builddir/$ARCH-build

    # 修复config.sub/config.guess无法识别HarmonyOS
    cp -f "$HOME/usr/local/share/config/config.sub" "$builddir/config/config.sub"
    cp -f "$HOME/usr/local/share/config/config.guess" "$builddir/config/config.guess"

    # 修复 hmdfs 上 umask 077 导致临时目录不可写的问题
    if [[ -d $builddir ]]; then
        find "$builddir" -name "configure" -type f -exec sed -i 's|umask 077|umask 067|g' {} \;
    fi
}

build() {
    cd $builddir/$ARCH-build
    # 鸿蒙系统/tmp只读，设置TMPDIR为可写目录
    export TMPDIR=$HOME/tmp
    mkdir -p $TMPDIR
    ../configure --prefix=$DEFAULT_PREFIX \
        --without-icu \
        --without-readline \
        --without-zlib \
        --without-openssl
    make -j$(nproc)
}

test_install() {
    cd $builddir/$ARCH-build

    # 测试安装：安装到临时目录验证安装流程，不清理用于归档
    local staging_root="$TMPDIR/test-install-${pkgname}-${pkgver}"
    rm -rf "$staging_root"
    echo "测试安装到: $staging_root"

    # Autotools使用DESTDIR方式
    make DESTDIR="$staging_root" install

    # 验证安装产物
    echo "验证安装产物..."
    local bin_count=$(find $staging_root/$DEFAULT_PREFIX/bin -type f 2>/dev/null | wc -l)
    local lib_count=$(find $staging_root/$DEFAULT_PREFIX/lib -name "*.so" -o -name "*.a" 2>/dev/null | wc -l)

    echo "安装二进制数量: $bin_count"
    echo "安装库数量: $lib_count"
}

install() {
    cd $builddir/$ARCH-build
    make install
}

check() {
    cd $builddir/$ARCH-build
    make check
}

# Main logic
ACTION=${1:-build}
case $ACTION in
    prepare)
        prepare
        ;;
    build)
        build
        ;;
    test_install)
        test_install
        ;;
    install)
        install
        ;;
    check)
        check
        ;;
    *)
        echo "Unknown action: $ACTION"
        exit 1
        ;;
esac
