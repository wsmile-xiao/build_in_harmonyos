(* test_ohos_e2e.ml — HarmonyOS-specific end-to-end consumer case for xmlm.
   Performs real file I/O on the OHOS device filesystem: writes an XML
   configuration file, streams it back with Xmlm from a Channel, asserts the
   decoded signals, re-encodes the document to a second file and re-parses it
   (roundtrip), all through the packaged xmlm library. *)

let checks = ref 0
let failures = ref 0

let check name cond =
  incr checks;
  if not cond then begin
    incr failures;
    Printf.printf "FAIL: %s\n" name
  end

type node =
  | Element of string * Xmlm.attribute list * node list
  | Data of string

let rec parse_node i =
  match Xmlm.input i with
  | `El_start ((_, name), atts) ->
      let rec children acc =
        match Xmlm.peek i with
        | `El_end -> ignore (Xmlm.input i); List.rev acc
        | _ -> children (parse_node i :: acc)
      in
      Element (name, atts, children [])
  | `Data d -> Data d
  | `Dtd _ | `El_end -> failwith "unexpected signal"

let rec find name = function
  | [] -> None
  | Element (n, atts, kids) :: rest ->
      if n = name then Some (atts, kids) else find name (rest @ kids)
  | Data _ :: rest -> find name rest

let attr k atts = try Some (List.assoc ("", k) atts) with Not_found -> None

let () =
  let path1 = "xmlm_ohos_e2e_source.xml" in
  let path2 = "xmlm_ohos_e2e_roundtrip.xml" in
  let xml =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n\
     <params>\n\
     \  <product name=\"HarmonyOS PC\" version=\"6.1.0\" api=\"23\"/>\n\
     \  <sdk path=\"/storage/Users/currentUser\"/>\n\
     \  <note>PC &amp; device</note>\n\
     </params>\n"
  in
  let oc = open_out_bin path1 in
  output_string oc xml;
  close_out oc;
  check "file written" (Sys.file_exists path1 && (Unix.stat path1).Unix.st_size > 0);

  (* stream + parse from a real channel *)
  let ic = open_in_bin path1 in
  let i = Xmlm.make_input (`Channel ic) in
  let rec top acc =
    if Xmlm.eoi i then List.rev acc
    else
      match Xmlm.input i with
      | `Dtd _ -> top acc
      | `El_start (("", "params"), _) ->
          let rec kids acc' =
            match Xmlm.peek i with
            | `El_end -> ignore (Xmlm.input i); List.rev acc'
            | _ -> kids (parse_node i :: acc')
          in
          let result = Element ("params", [], kids []) in
          if Xmlm.eoi i then [result] else top (result :: acc)
      | `Data _ | `El_start _ -> top acc
      | `El_end -> top acc
  in
  let root = top [] in
  close_in ic;
  let params = match find "params" root with Some (a, k) -> Some (a, k) | None -> None in
  (match params with
   | Some (_a, kids) ->
       (match find "product" kids with
        | Some (atts, _) ->
            check "product name attr" (attr "name" atts = Some "HarmonyOS PC");
            check "product version attr" (attr "version" atts = Some "6.1.0");
            check "product api attr" (attr "api" atts = Some "23")
        | None -> check "product element present" false);
       (match find "sdk" kids with
        | Some (atts, _) ->
            check "sdk path attr" (attr "path" atts = Some "/storage/Users/currentUser")
        | None -> check "sdk element present" false);
       (match find "note" kids with
        | Some (_atts, [Data d]) -> check "text entity decoded" (d = "PC & device")
        | _ -> check "note text present" false)
   | None -> check "params element present" false);

  (* re-encode the parsed tree to a second file, then re-parse it *)
  let oc2 = open_out_bin path2 in
  let o = Xmlm.make_output ~decl:true (`Channel oc2) in
  let rec emit = function
    | Data d -> Xmlm.output o (`Data d)
    | Element (n, atts, kids) ->
        Xmlm.output o (`El_start (("", n), atts));
        List.iter emit kids;
        Xmlm.output o `El_end
  in
  Xmlm.output o (`Dtd None);
  List.iter emit root;
  close_out oc2;
  check "roundtrip file written" ((Unix.stat path2).Unix.st_size > 0);
  let ic2 = open_in_bin path2 in
  let i2 = Xmlm.make_input (`Channel ic2) in
  let rec count depth starts =
    match Xmlm.input i2 with
    | `Dtd _ -> count depth starts
    | `El_start _ -> count (depth + 1) (starts + 1)
    | `Data _ -> count depth starts
    | `El_end -> if depth = 1 then starts else count (depth - 1) starts
  in
  let elements = count 0 0 in
  close_in ic2;
  check "roundtrip element count" (elements = 4);
  Sys.remove path1;
  Sys.remove path2;
  check "temp files removed" (not (Sys.file_exists path1) && not (Sys.file_exists path2));

  Printf.printf "assertions=%d failures=%d\n" !checks !failures;
  if !failures > 0 then exit 1;
  print_endline "ALL OHOS E2E PASSED"
