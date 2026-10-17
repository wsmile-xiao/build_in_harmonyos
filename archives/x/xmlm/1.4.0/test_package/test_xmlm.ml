(* test_xmlm.ml — consumer test for the packaged xmlm library (native + bytecode)
   Exercises Xmlm decode (String input) and encode (Buffer output) end to end
   and asserts the observed signals/bytes. Pure OCaml (no C stubs). *)

let checks = ref 0
let failures = ref 0

let check name cond =
  incr checks;
  if not cond then begin
    incr failures;
    Printf.printf "FAIL: %s\n" name
  end

let contains hay needle =
  let n = String.length needle and h = String.length hay in
  let rec go i = i + n <= h && (String.sub hay i n = needle || go (i + 1)) in
  n = 0 || go 0

let decode_to_lists xml =
  let i = Xmlm.make_input (`String (0, xml)) in
  let starts = ref 0 and ends = ref 0 in
  let datas = ref [] and atts = ref [] in
  let depth = ref 0 and stop = ref false in
  while not !stop do
    match Xmlm.input i with
    | `Dtd _ -> ()
    | `El_start ((_, name), at) ->
        incr starts;
        incr depth;
        atts := (name :: List.map (fun ((_, n), v) -> n ^ "=" ^ v) at) @ !atts
    | `El_end ->
        incr ends;
        decr depth;
        if !depth = 0 then stop := true
    | `Data d -> datas := d :: !datas
  done;
  (!starts, !ends, List.rev !datas, !atts, Xmlm.eoi i)

let () =
  (* ---------- decode ---------- *)
  let xml =
    "<?xml version=\"1.0\"?><config mode=\"fast\" n=\"2\">\
     <item id=\"a\">one</item><item id=\"b\">two</item></config>"
  in
  let starts, ends, datas, atts, eoi = decode_to_lists xml in
  check "decoder reached end of input" eoi;
  check "three start tags" (starts = 3);
  check "three end tags" (ends = 3);
  check "two text nodes" (List.length datas = 2);
  check "text values preserved" (datas = ["one"; "two"]);
  check "attribute mode=fast" (List.mem "mode=fast" atts);
  check "attribute id=b" (List.mem "id=b" atts);

  (* ---------- encode ---------- *)
  let b = Buffer.create 256 in
  let o = Xmlm.make_output ~decl:false (`Buffer b) in
  let tag n = (("", n), []) in
  Xmlm.output o (`Dtd None);
  Xmlm.output o (`El_start ((("", "root"), [("", "v"), "7"])));
  Xmlm.output o (`Data "hello & <world>");
  Xmlm.output o `El_end;
  let out = Buffer.contents b in
  check "encoder emits root element" (contains out "<root");
  check "encoder escapes ampersand" (contains out "&amp;");
  check "encoder does not emit raw markup chars" (not (contains out "hello & <world>"));

  (* ---------- roundtrip: encode then decode ---------- *)
  let b2 = Buffer.create 128 in
  let o2 = Xmlm.make_output ~decl:true (`Buffer b2) in
  Xmlm.output o2 (`Dtd None);
  Xmlm.output o2 (`El_start (tag "r"));
  Xmlm.output o2 (`Data "roundtrip");
  Xmlm.output o2 `El_end;
  let doc = Buffer.contents b2 in
  let _starts2, _ends2, datas2, _atts2, eoi2 = decode_to_lists doc in
  check "roundtrip data" (datas2 = ["roundtrip"]);
  check "roundtrip reached eoi" eoi2;

  Printf.printf "assertions=%d failures=%d\n" !checks !failures;
  if !failures > 0 then exit 1;
  print_endline "ALL TESTS PASSED"
