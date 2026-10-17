#!/bin/sh
# Execute every rendering path from upstream examples/test.csh without csh.
set -eu

build_dir=$1
source_dir=$2
cd "$build_dir/examples"
cp "$source_dir/examples/brainsmall.den" .
cp "$source_dir/examples/check.ppm" .

./makevolume
./rendervolume
cmp brainsmall.ppm check.ppm
echo 'volpack: raw rendering matches upstream check.ppm'

./makeoctree
./rendervolume -octree
cmp brainsmall.ppm check.ppm
echo 'volpack: octree rendering matches upstream check.ppm'

./classifyvolume
./rendervolume -classified
cmp brainsmall.ppm check.ppm
echo 'volpack: classified rendering matches upstream check.ppm'

./classifyvolume -octree
./rendervolume -classified
cmp brainsmall.ppm check.ppm
echo 'volpack: classified octree rendering matches upstream check.ppm'
echo 'volpack: upstream rendering tests 4/4 PASS'
