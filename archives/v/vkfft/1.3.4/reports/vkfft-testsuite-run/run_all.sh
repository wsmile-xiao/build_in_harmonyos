#!/bin/sh
export LD_LIBRARY_PATH=/data/storage/el2/base/cache/conan-home-vkfft/p/fftw02b9874643912/p/lib:/data/storage/el2/base/cache/conan-home-vkfft/p/fftw3f08e1f8bbf1a4/p/lib
cd /data/storage/el2/base/cache/vkfft-tests/build
rm -f summary.txt
for s in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 50 51 52 100 101 1000 1001 1002 1003 1004; do
  echo "=== sample $s start $(date +%H:%M:%S) ===" >> run.log
  timeout 900 ./VkFFT_TestSuite -vkfft $s > out_s${s}.log 2>&1
  rc=$?
  echo "sample $s exit=$rc $(date +%H:%M:%S)" >> summary.txt
done
echo ALL_DONE >> summary.txt
