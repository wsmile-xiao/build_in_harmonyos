// RUN: llc -mtriple=aarch64-unknown-linux-ohos %s -o - | FileCheck %s

define i64 @add(i64 %a, i64 %b) {
entry:
  %s = add i64 %a, i64 %b
  ret i64 %s
}

; CHECK-LABEL: add:
; CHECK: add x0, x0, x1
; CHECK: ret
