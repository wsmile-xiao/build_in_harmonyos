#!/data/service/hnp/bin/bash
# vpc-sim.sh — minimal bash re-implementation of the upstream vpcd
# test simulator (t/simulators/vpcd.c, stdin/stdout mode) for use as a
# powermand coprocess device (device "t" "vpc" "bash vpc-sim.sh |&").
#
# Implements exactly the protocol subset the vpc.dev specification and
# the R34 smoke suite exercise: login/logoff, stat N/*, on/off N/range/*.
# The plug state lives in this process only (16 plugs, all OFF at start).
#
# NOTE: the shebang above matches the porting-machine/CI bash; the
# wrapper in test.sh invokes it as "bash vpc-sim.sh" so the shebang is
# advisory only.
seq=0
plug=()
for i in {0..15}; do plug[$i]=OFF; done

ok() {  # vpcd "goto ok" trailer: seq OK + next prompt (seq increments per command)
    echo "$seq OK"
    seq=$((seq+1))
    printf '%d vpc> ' "$seq"
}

# expand a powermand %s substitution: hostlist-compressed plug list like
# "[0-3]", "0", "0,3", or "0-3" -> space separated plug numbers.
# (upstream vpcd does this with the hostlist library; sscanf "on %s")
expand_plugs() {
    local a=$1
    a=${a#[}; a=${a%]}
    local out="" p
    for p in ${a//,/ }; do
        case "$p" in
            [0-9]*-[0-9]*)
                local lo=${p%-*} hi=${p#*-} i
                for ((i=lo; i<=hi; i++)); do out="$out $i"; done
                ;;
            *)
                out="$out $p"
                ;;
        esac
    done
    echo "$out"
}

while IFS= read -r line; do
    [ -z "$line" ] && continue
    case "$line" in
        logoff)
            echo "$seq OK"
            exit 0
            ;;
        login)
            ok
            ;;
        "stat *")
            for i in {0..15}; do echo "plug $i: ${plug[$i]}"; done
            ok
            ;;
        stat\ *)
            i=${line#stat }
            case "$i" in *[!0-9]*|"") echo "$seq BADVAL: $i" ;;
                        *) echo "plug $i: ${plug[$i]:-ERROR}" ;;
            esac
            ok
            ;;
        on\ *|off\ *)
            cmd=${line%% *}; arg=${line#* }
            if [ "$arg" = "*" ]; then
                for i in {0..15}; do
                    plug[$i]=$( [ "$cmd" = on ] && echo ON || echo OFF )
                    echo "$i: OK"
                done
            else
                for p in $(expand_plugs "$arg"); do
                    plug[$p]=$( [ "$cmd" = on ] && echo ON || echo OFF )
                    echo "$p: OK"
                done
            fi
            ok
            ;;
        *)
            # beacon/temp/reset/spew and anything else the smoke suite
            # does not exercise: generic OK so powermand never wedges.
            ok
            ;;
    esac
done
exit 0
