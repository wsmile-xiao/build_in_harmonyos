# Adapted from upstream libvips 8.18.4 test/variables.sh.in for the packaged
# OHOS libvips build.
#
# Upstream substitutes @abs_top_builddir@ / @abs_top_srcdir@ (Meson build
# tree) and points $image at test/test-suite/images/sample.jpg (290x442).
# This package has no libjpeg loader, so a PNG seed of the same geometry is
# used.  The seed is not committed to the PR (CI applies the change as a git
# patch and GitCode's pull/<n>.diff cannot carry raw binaries): the
# test_package conanfile synthesises a 290x442 black RGB PNG at build time
# with the packaged vips CLI and exports its path as TEST_IMAGE, which is what
# the geometry-dependent size assertions in test_cli.sh are written against.
# When the scripts are run by hand, set TEST_IMAGE to any 290x442 image.
#
# vips / vipsheader / vipsthumbnail are resolved from PATH: the test_package
# prepends the packaged <prefix>/bin before running the shell tests.
#
# No Python and no bc are required.  Float comparisons in the upstream tests
# go through break_threshold() which used bc; here it is replaced with an
# integer-part comparison that is exact for the near-zero differences these
# tests assert on OHOS.

# The conanfile exports the generated seed as TEST_IMAGE.  The fallback below
# only triggers when the scripts are run by hand outside the test_package.
image=${TEST_IMAGE:-sample.png}

# A private temp dir for this test process (never shared between the parallel
# Meson tests upstream, hence the $$ suffix).
base_tmp=${VIPS_UT_BASE_TMP:-${TMPDIR:-/tmp}}
tmp="$base_tmp/libvips-ut-$$"
mkdir -p "$tmp"

# Prefer the packaged CLI tools from PATH (test_package injects <prefix>/bin);
# individual tools can still be overridden through the environment.
vips=${VIPS_BIN:-vips}
vipsthumbnail=${VIPSTHUMBNAIL_BIN:-vipsthumbnail}
vipsheader=${VIPSHEADER_BIN:-vipsheader}

# we need '.' as the decimal separator
export LC_NUMERIC=C

# some distros set LC_ALL, which overrides LC_NUMERIC
unset LC_ALL

# test whether a file format (load/save operation) is supported by the built
# libvips.  'vips <op>' exits non-zero when the operation is not compiled in.
test_supported() {
	format=$1

	if $vips "$format" > /dev/null 2>&1; then
		return 0
	else
		echo "support for $format not configured, skipping test"
		return 1
	fi
}

# Return the integer part of a (possibly negative, possibly floating) number.
_float_int_part() {
	v=$1
	# strip exponent
	v=${v%%[eE]*}
	# strip decimal fraction
	v=${v%%.*}
	# strip sign
	case "$v" in
		-*) v=${v#-} ;;
	esac
	printf '%s' "${v:-0}"
}

# Shell-only "is the value > 0?" predicate (upstream piped through bc).
_gt_zero() {
	v=$1
	i=$(_float_int_part "$v")
	if [ "$i" -gt 0 ]; then
		return 0
	fi
	# integer part is 0: only a non-zero fractional part makes it positive
	case "$v" in
		-*) return 1 ;;
	esac
	frac=${v#*.}
	frac=${frac%%[eE]*}
	case "$frac" in
		*[1-9]*)
			return 0
			;;
	esac
	return 1
}

# Is the absolute difference above the threshold?  Return 0 when the upstream
# test should report an error (diff > threshold), 1 when it is within the
# threshold.  Upstream used `echo "$diff <= $threshold" | bc -l`; bc is not
# shipped on the OHOS worker, so compare integer parts.  The thresholds used by
# the vendored tests are small integers and the asserted differences are ~0,
# so the integer-part comparison is exact for the pass/fail decisions here.
break_threshold() {
	diff=$1
	threshold=$2

	d=$(_float_int_part "$diff")
	t=$(_float_int_part "$threshold")

	if [ "$d" -gt "$t" ]; then
		# integer part already above the threshold
		return 0
	fi
	if [ "$d" -lt "$t" ]; then
		return 1
	fi
	# Integer parts are equal: only a non-zero fractional part of $diff can
	# push it above the threshold.  "0.500" -> frac "500" (has a non-zero digit).
	frac=${diff#*.}
	frac=${frac%%[eE]*}
	case "$frac" in
		*[1-9]*)
			return 0
			;;
	esac
	return 1
}

# subtract two images, then test that the max absolute difference stays below a
# threshold (identical helper to upstream variables.sh).
test_difference() {
	before=$1
	after=$2
	threshold=$3

	# compare in srgb space
	$vips colourspace "$before" "$tmp/b-rgb.v" srgb
	$vips colourspace "$after" "$tmp/a-rgb.v" srgb

	$vips subtract "$tmp/b-rgb.v" "$tmp/a-rgb.v" "$tmp/difference.v"
	$vips abs "$tmp/difference.v" "$tmp/abs.v"
	dif=$($vips max "$tmp/abs.v")

	if break_threshold "$dif" "$threshold"; then
		echo "save / load difference is $dif"
		exit 1
	fi
}
