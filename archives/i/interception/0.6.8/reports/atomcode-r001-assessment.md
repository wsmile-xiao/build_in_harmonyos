# Actual AtomCode report assessment

Reviewed PR #13933 HEAD 789e3e85ac1b175465cc53947306577a5be06f0b. Actual invocation RC0; stdout SHA-256 be1d0a3c50e87b15cf492594ac207b10db08b5661f5a844ff06e04f1d5b664b9. Static inspection is not CI, platform Review or submission PASS.

- D1: the software-level manifest prematurely said published while the verified version is built. Corrected to built and the current evidence date. Submission alone never means publication; publication still requires a post-merge release receipt.
- D2: false for the new paired draft. The actual knowledge engine resolves doc_file against the parent of knowledge/graph, i.e. knowledge/, in scripts/ohc/engine.py. Therefore drafts/E2026100504-draft-2301_80739235.md resolves correctly. The report's suggested knowledge/ prefix would incorrectly double that directory. The old legacy DRAFT had precisely that doubled-prefix problem; corrected that legacy field instead.
- D3 provenance: anchored the new pair to immutable HEAD 789e3e85..., which actually contains its production parser consumer and Harmony test. This is the tested code baseline, not a self-referential demand that the draft name its own future commit. Clarified the legacy verification description as historical and separately stated the verified current 7+1 results.
- D3 domain: false. Current authoritative PR/API is AtomGit. Retain the verified AtomGit URL, not the report's inferred obsolete domain.
- O3: false causal claim. Child processes inherit Python's os.environ absent an explicitly replacing env; assigning TMPDIR is not a process-local no-op. Do not make an unrelated toolchain change.
- Other observations are nonblocking; do not expand dependencies or revise frozen runtime inputs to address suggestions without an actual defect.

The runtime conanfile, conandata, patches and test_package inputs are unchanged from native r001 and formal r001. Only metadata/provenance was corrected; validate those exact input hashes before reusing their evidence. Current-HEAD platform CI is still pending and no submission is claimed. The complete original report, including false findings, is retained in the task root and will be posted for independent verification.
