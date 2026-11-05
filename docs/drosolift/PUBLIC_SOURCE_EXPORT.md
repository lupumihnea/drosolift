# Fresh public source export

The local implementation checkout preserves the audited upstream history. Its
historical walking rig has no supplied public redistribution license, so that
history is not pushed to the new public repository. A fresh attributed source
snapshot retains LICENSE, NOTICE, third-party licenses and source manifests,
including the walking asset's rights/provenance record, while omitting its GLB
and legacy renders. This changes publication packaging, not model dynamics.

From the implementation checkout, choose a fresh sibling directory:

```powershell
.venv\Scripts\python.exe scripts/export_public_source.py --output ..\drosolift-public
```

The exporter runs read-only `git ls-files --cached --others --exclude-standard
-z`; it never edits the original Git configuration, index or history. It checks
that the audited upstream revision is an ancestor of implementation HEAD. Run
as the checkout owner if Git rejects its ownership. Output inside the source
checkout or an existing output directory is rejected. No remote publication,
deployment or cloud resource creation occurs in this command.

Excluded inputs include `.git`, private tool/memory/environment state, Python and
Bun installations, generated distributions, raw/processed datasets and per-run
data, databases/private-key files, packaged archives, `walking-fly.glb`, all
`docs/media` legacy renders and `docs/drosolift/evidence/p0*` baseline evidence.
The non-secret build selectors `.env.public` and `.env.replay` are retained.
Other source, official compact data, the licensed CC BY CT surface, modern
procedural-fly screenshots and actual recorded demonstrations are retained.

Before creating output, every retained file must be regular, remain within the
source root, contain no links/junctions or unsafe paths, remain below 50 MB, and
pass credential-pattern checks. The restricted asset SHA256 is rejected under
any retained filename. A GLB is accepted only at the pinned CC BY CT path with
its exact documented checksum. Credentials are never echoed in rejection text.
These checks supplement review; they are not a proof that every possible secret
encoding can be detected.

Only exported documentation/evidence copies are sanitized. JSON string values
containing absolute local filesystem paths and explicit machine/user-name fields
are replaced with visible omission markers; measured rates, counters, frame
cadence and hardware/renderer descriptions remain. Path-bearing text lines are
replaced with an explicit omission marker. Original local evidence is unchanged.
Each transformed file records its original SHA256, transformation and exported
checksum in `PUBLIC_SOURCE_MANIFEST.json`. Model/source code is not rewritten.

`UPSTREAM_LINEAGE.json` identifies the official upstream repository, pinned audit,
implementation HEAD, whether uncommitted changes were included, exclusion reason
and notice locations. The manifest lists every exported file except itself with
size/checksum, plus each excluded inventory path and reason. Source files are
reread and checked during copying, so a change during export aborts and removes
only the newly created, checked output directory. No original data is removed.

Verify before installing dependencies or generating builds:

```powershell
python scripts/export_public_source.py --verify .
```

Verification accepts an optional newly initialized `.git` directory but rejects
unmanifested files, changed checksums, missing notices and unsafe assets. A fresh
public source repository intentionally lacks the original audited ancestor;
use `--verify` there rather than attempting another upstream-history export.

Focused tests are independent of the historical GLB and private source archives:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_export_public_source
```

Six tests passed in 8.024 seconds, covering notices, fresh output/history,
inventory exclusions, checksums/lineage, size and renamed-asset rejection,
credential checks, traversal/links and non-mutating evidence sanitation.

## Clean-source build evidence, 5 November 2026

The first successful review export contained 454 manifest-listed files totaling
62,514,745 bytes, with 28 inventory exclusions and 14 sanitized documentation
copies. Its largest file was the 5,610,577-byte official soma-position cache.
The original implementation `.git` remained present. The review source was
initialized and committed locally as
`abcf7108baa533b27ccfaaf42b7b1e399552c940`, using the user-verified author and
per-command `core.autocrlf=false`, then cloned into a separate fresh directory.
All 454 manifest checksums passed again in that clone before dependency install.
The manifest SHA256 was
`51383e6dfaa2a25f9296f02aefe5b657c3fe14ef2d06e81a6674730d425304f7`.

In the clean clone, `bun install --frozen-lockfile` installed 29 packages using
Bun 1.4.4 in 21.89 seconds. `bun test` passed 67 tests / 1,632 assertions across
22 files in 4.14 seconds. Both `bun --bun run build:public` and
`bun --bun run build:replay` passed their TypeScript checks and Vite builds,
transforming 52 modules and producing each requested `index.html`. These checks
did not require the excluded walking GLB. The later final publication snapshot
also includes `.gitattributes` to preserve these byte hashes across platforms;
the earlier review clone used the explicit Git configuration and checksum proof.

Commands, counts and logs are recorded in
[`evidence/publication/clean-source-checks.json`](evidence/publication/clean-source-checks.json)
and its adjacent `clean-source-*.log` files. The final source snapshot is created
after final evidence/documentation settles; this local review commit is not a
claim of a remote push or a hosted service.
