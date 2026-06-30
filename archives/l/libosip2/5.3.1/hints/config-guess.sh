#!/bin/bash
# E007/E011: 复制最新 config.guess/config.sub 以识别 HarmonyOS
# patch 命令在 HMDFS 上无法正常工作，使用直接复制替代
cp ~/usr/local/share/automake-1.16/config.guess scripts/ || exit 1
cp ~/usr/local/share/automake-1.16/config.sub scripts/ || exit 1
chmod +x scripts/config.guess scripts/config.sub
