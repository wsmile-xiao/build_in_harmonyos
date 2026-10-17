#!/bin/sh
# aircrack-ng 真实功能验证：WPA2 EAPOL 握手破解
# 用例来源：上游 test/test-aircrack-ng-0001.sh（密码 12345678）
# 注：wpa2.eapol.cap 为二进制抓包固件，按仓库规范以 base64 文本
#     （wpa2.eapol.cap.b64）入库，运行时解码还原

set -e

base64 -d wpa2.eapol.cap.b64 > wpa2.eapol.cap

aircrack-ng -w password.lst -a 2 -e Harkonen -q wpa2.eapol.cap \
    | grep 'KEY FOUND! \[ 12345678 \]'

echo "aircrack-ng WPA2 handshake crack test: PASS"
