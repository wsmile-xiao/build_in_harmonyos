(* test_topkg.ml — consumer test for the packaged topkg library.
   Exercises Topkg.String, Topkg.R and Topkg.OS (real device syscalls:
   getcwd, directory listing, /dev/null write+read, command lookup) and
   asserts the results. Pure OCaml (no C stubs). *)

open Topkg

let checks = ref 0
let failures = ref 0

let check name cond =
  incr checks;
  if not cond then begin
    incr failures;
    Printf.printf "FAIL: %s\n" name
  end

let () =
  (* String utilities (param-style strings from the HarmonyOS device) *)
  check "is_prefix true"
    (String.is_prefix ~affix:"const" "const.product.name");
  check "is_prefix false (negative control)"
    (not (String.is_prefix ~affix:"xyz" "const.product.name"));
  check "is_suffix true"
    (String.is_suffix ~affix:".name" "const.product.name");
  (match String.cut ~sep:'.' "const.product.name" with
   | Some (a, b) ->
       check "cut left" (a = "const");
       check "cut right" (b = "product.name")
   | None -> check "cut" false);

  (* Result combinators *)
  check "R.error_msg"
    (match R.error_msg "boom" with Error (`Msg "boom") -> true | _ -> false);
  check "R.reword_error"
    (match R.reword_error (fun _ -> "reworded") (R.error_msg "boom") with
     | Error "reworded" -> true
     | _ -> false);

  (* Real OS interaction on the OHOS device *)
  (match OS.Dir.current () with
   | Error _ -> check "OS.Dir.current" false
   | Ok dir ->
       check "cwd is an existing dir" (OS.Dir.exists dir = Ok true);
       check "cwd listing succeeds"
         (match OS.Dir.contents ~dotfiles:false dir with
          | Ok _ -> true
          | Error _ -> false);
       check "null device exists" (OS.File.exists OS.File.null = Ok true);
       check "write to null device"
         (OS.File.write OS.File.null "const.product.version=6.1.0\n" = Ok ());
       check "read null device is EOF"
         (OS.File.read OS.File.null = Ok "");
       check "sh found on PATH" (OS.Cmd.exists (Cmd.v "sh") = Ok true);
       check "sh resolvable"
         (match OS.Cmd.must_exist (Cmd.v "sh") with Ok _ -> true | Error _ -> false));

  Printf.printf "assertions=%d failures=%d\n" !checks !failures;
  if !failures > 0 then exit 1;
  print_endline "ALL TESTS PASSED"
