#!/bin/sh
# test_package consumer test for exifprobe 2.0.1.
# Generates a minimal JPEG carrying a real EXIF APP1/TIFF segment
# (Make tag = "OHOS-TEST"), then runs the *installed* `exifprobe`
# binary and checks its observable output. This verifies that a
# consumer can invoke the tool through its public CLI on OHOS and
# get correct metadata extraction results.
export PATH="$PATH:/system/bin"

echo "--- exifprobe consumer verification ---"

# 1. Generate the test JPEG (239 bytes, EXIF Make=OHOS-TEST) via octal escapes.
JPEG_HEX="\377\330\377\341\000\054\105\170\151\146\000\000\111\111\052\000\010\000\000\000\001\000\017\001\002\000\012\000\000\000\032\000\000\000\000\000\000\000\117\110\117\123\055\124\105\123\124\000\377\333\000\103\000\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\010\377\300\000\013\010\000\010\000\010\001\001\021\000\377\304\000\037\000\000\001\005\001\001\001\001\001\001\000\000\000\000\000\000\000\000\001\002\003\004\005\006\007\010\011\012\013\377\332\000\010\001\001\000\000\077\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\377\331"
TEST_JPG="$PWD/test-exif.jpg"
printf "%b" "$JPEG_HEX" > "$TEST_JPG"
[ -f "$TEST_JPG" ] || { echo "FAIL: cannot write $TEST_JPG"; exit 1; }
echo "PASS 0: test JPEG written ($(wc -c < "$TEST_JPG") bytes)"

# 2. Version probe via public CLI.
ver=$(exifprobe -V 2>&1)
case "$ver" in
  *2.0.1*) echo "PASS 1: version -> $(echo "$ver" | head -1)" ;;
  *) echo "FAIL: version expected 2.0.1 got [$ver]"; exit 1 ;;
esac

# 3. Real EXIF parse: -L list mode must show Make tag with OHOS-TEST value.
out=$(exifprobe -L "$TEST_JPG" 2>&1)
rc=$?
[ $rc -eq 0 ] || { echo "FAIL: exifprobe -L exit=$rc output=[$out]"; exit 1; }
echo "PASS 2: exifprobe -L exit=0"
echo "$out" | grep -q "OHOS-TEST" || { echo "FAIL: Make tag value not found; output=[$out]"; exit 1; }
echo "PASS 3: Make tag parsed -> OHOS-TEST"
echo "$out" | grep -qi "jpeg" || { echo "FAIL: JPEG type not reported; output=[$out]"; exit 1; }
echo "PASS 4: File Type JPEG recognized"

# 4. Structure mode: verify EXIF/TIFF/APP1 structure walk works.
out2=$(exifprobe "$TEST_JPG" 2>&1)
rc2=$?
[ $rc2 -eq 0 ] || { echo "FAIL: exifprobe structure mode exit=$rc2"; exit 1; }
echo "$out2" | grep -q "<JPEG_APP1>" || { echo "FAIL: APP1 segment not found; output=[$out2]"; exit 1; }
echo "PASS 5: APP1/Exif structure walk"

echo "test exifprobe 2.0.1: 6/6 functional checks PASS"
exit 0
