#!/bin/sh

# set -x

# self-sufficient adaptation: locate and source variables.sh next to this file
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$HERE/variables.sh"

exit_code=0
$vips im_benchmarkn || exit_code=$?
if [ $exit_code -ne 0 ]; then
	echo "im_benchmark is not available, skipping test"
	exit 0
fi

chain=1

# im_benchmark needs a labq
$vips colourspace $image $tmp/t3.v labq

for tile in 10 64 128 512; do
	# benchmark includes a dither which will vary with tile size
	$vips --vips-concurrency=1 \
		--vips-tile-width=$tile --vips-tile-height=$tile \
		im_benchmarkn $tmp/t3.v $tmp/t5.v $chain

	for cpus in 2 3 4 5 6 7 8 99; do
		echo trying cpus = $cpus, tile = $tile ...
		$vips --vips-concurrency=$cpus \
			--vips-tile-width=$tile --vips-tile-height=$tile \
			im_benchmarkn $tmp/t3.v $tmp/t7.v $chain
		$vips subtract $tmp/t5.v $tmp/t7.v $tmp/t8.v
		$vips abs $tmp/t8.v $tmp/t9.v
		max=$($vips max $tmp/t9.v)
		if _gt_zero "$max"; then
			break
		fi
	done
	if _gt_zero "$max"; then
		break
	fi
done

if _gt_zero "$max"; then
	echo error, max == $max
	exit 1
else
	echo all benchmark threading tests passed
fi

# setting VIPS_MAX_THREADS low should force a small thread limit
echo -n "checking threadset size limit ... "
exit_code=0
VIPS_MAX_THREADS=5 VIPS_CONCURRENCY=3 $vips copy "$image" "$tmp/x.v" || exit_code=$?
if [ $exit_code -ne 0 ]; then
  echo FAILED
  exit 1
fi
echo ok

