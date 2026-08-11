(* Keep a tagged value live across allocation-heavy list construction and a call. *)
fun build 0 acc = acc
  | build n acc = build (n - 1) ((n, Int.toString n) :: acc)

fun checksum xs =
    List.foldl (fn ((n, text), sum) => n + size text + sum) 0 xs

val retained = SOME (List.tabulate (64, fn i => i + 1))
val rows = build 512 []
val result = checksum rows
val retainedSum =
    case retained of
        SOME values => List.foldl op+ 0 values
      | NONE => raise Fail "retained value lost"

val _ =
    if result > 0 andalso retainedSum = 2080
    then print ("ARM64_SAVE_SET_REGRESSION_OK" ^ String.str (Char.chr 10))
    else raise Fail "ARM64 save-set regression failed"
