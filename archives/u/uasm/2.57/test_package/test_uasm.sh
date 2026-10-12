#!/bin/sh
# UASM consumer / OHOS portability checks against the installed binary.
# Usage: test_uasm.sh <uasm> <workdir>
set -euo pipefail
U="$1"
W="$2"
mkdir -p "$W"
cd "$W"

pass=0
fail=0
ok() { pass=$((pass + 1)); }
bad() { fail=$((fail + 1)); echo "FAIL $1"; }

# 1) version banner
"$U" > banner.txt 2>&1 || true
if grep -q "UASM v2.57" banner.txt; then ok; else bad version; fi

# 2) plain MASM assembly -> flat binary
cat > plain.asm <<'EOF'
    .386
    .model flat
    .code
    mov eax, 1
    mov ebx, 2
end
EOF
"$U" -q -bin plain.asm >/dev/null 2>&1
printf '\270\001\000\000\000\273\002\000\000\000' > plain.exp
if cmp -s plain.BIN plain.exp; then ok; else bad plain-bin; fi

# 3) LP64 fix: 32-bit SHR semantics for a negative value
cat > shr.asm <<'EOF'
    .386
    .model flat
    .code
row = -1
    mov eax, row SHR 4
end
EOF
"$U" -q -bin shr.asm >/dev/null 2>&1
printf '\270\377\377\377\017' > shr.exp
if cmp -s shr.BIN shr.exp; then ok; else bad shr-lp64; fi

# 4) CodeGenV2 AVX/VEX encoding (must not be miscompiled)
cat > vex.asm <<'EOF'
    .x64
    .model flat
    .code
    vpmaskmovd xmm6,xmm4,OWORD PTR [rcx]
    vpsrlvq xmm2,xmm6,xmm4
end
EOF
"$U" -q -bin vex.asm >/dev/null 2>&1
printf '\304\342\131\214\061\304\342\311\105\324' > vex.exp
if cmp -s vex.BIN vex.exp; then ok; else bad vex-encoding; fi

# 5) ELF64 relocatable object is produced (verify magic + 64-bit class)
cat > obj.asm <<'EOF'
    .x64
    .model flat
    .code
    public main
main proc
    xor eax, eax
    ret
main endp
end
EOF
"$U" -q -elf64 obj.asm >/dev/null 2>&1
head -c 5 obj.o > obj.magic
printf '\177ELF\002' > elf.exp
if cmp -s obj.magic elf.exp; then ok; else bad elf64-object; fi

# 6) invalid instruction is reported (diagnostics work)
printf '    .386\n    .model flat\n    .code\n    this_is_not_an_instruction eax, ebx\nend\n' > bad.asm
"$U" -q -bin bad.asm >/dev/null 2>&1 || true
if [ -s bad.err ]; then ok; else bad error-report; fi

echo "UASM_CONSUMER_PASS=$pass FAIL=$fail"
[ "$fail" -eq 0 ]
