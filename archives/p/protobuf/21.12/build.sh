#!/data/service/hnp/bin/bash

pkgname="protobuf"
pkgver="21.12"
url=""
pkgtype="cc"
buildsystem="cmake"
depends=()
makedepends=()
source="https://github.com/protocolbuffers/protobuf/releases/download/v21.12/protobuf-all-21.12.tar.gz"
builddir="protobuf-${pkgver}"

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
    mkdir -p $builddir/ohos-build
}

config() {
    cd $builddir/ohos-build
    export CC=/data/service/hnp/bin/clang
    export CXX=/data/service/hnp/bin/clang++
    cmake -S../ \
        -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
        -DCMAKE_BUILD_TYPE=Release \
        -Dprotobuf_BUILD_TESTS=OFF \
        -Dprotobuf_BUILD_SHARED_LIBS=OFF \
        -Dprotobuf_BUILD_PROTOC_BINARIES=ON
}

build() {
    cd $builddir/ohos-build
    make --jobserver-style=pipe -j$(nproc)
}

# 调试阶段的安装函数，防止污染正式目录
test_install() {
    cd $builddir/ohos-build
    local staging_root="$TMPDIR/test-install-${pkgname}-${pkgver}"
    rm -rf "$staging_root"
    make install DESTDIR="$staging_root"
}

# 正式的安装函数
install() {
    cd $builddir/ohos-build
    make install
}

check() {
    cd $builddir/ohos-build
    echo "验证protoc编译器构建产物"
    if [[ -f protoc ]]; then
        ./protoc --version
    else
        echo "protoc编译器未找到"
    fi
}

# Main logic
ACTION=${1:-print}
case $ACTION in
    prepare)
        prepare
        ;;
    config)
        config
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
        ;;
esac