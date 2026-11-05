# Third-party notices

The Apache License 2.0 in [`LICENSE`](LICENSE) applies to FlyBrain Lab's
original source code, documentation, and project-produced media unless a file
states otherwise. It does not replace the licenses or permissions below.

## MaleCNS v1.0 connectome

FlyBrain Lab uses official MaleCNS v1.0 annotations, connection weights,
neurotransmitter predictions, and derived anatomical soma positions under the
source's CC-BY terms. The raw datasets are not committed. Source URLs and exact
SHA-256 checksums are pinned in
[`data/malecns/v1.0/source-manifest.json`](data/malecns/v1.0/source-manifest.json).

The bounded `frontend/web/public/assets/selected-skeletons.json` contains
official MaleCNS v1.0 SWCs for eight bodies: 10702, 10783, 11177, 36800, 63316,
67052, 80841 and 201965, converted to JSON with
all source parent links retained. The official download guide's license link
specifies [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit:
MaleCNS / FlyEM (HHMI Janelia), University of Cambridge, MRC Laboratory of
Molecular Biology and Google Research. Source URLs, checksums, native units,
display transform and reproduction are recorded in
[`docs/drosolift/MORPHOLOGY.md`](docs/drosolift/MORPHOLOGY.md).

## Drosophila CT surface

The visual body in `frontend/web/src/assets/fly/drosophila.glb` is derived from
*Behaviour and Reproduction of Drosophila Melanogaster Exposed to 3.5 GHz
Radio-Frequency Electromagnetic Fields - Underlying data* by Orestis Katsamenis,
Pieterjan De Boose, Herman Wijnen, and Arno Thielens. Source: Zenodo record
[14838021](https://zenodo.org/records/14838021), DOI
[10.5281/zenodo.14838021](https://doi.org/10.5281/zenodo.14838021). It is licensed
under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Modifications
and checksums are documented in
[`frontend/web/src/assets/fly/ATTRIBUTION.md`](frontend/web/src/assets/fly/ATTRIBUTION.md)
and the adjacent source manifest.

## Authored walking-fly asset

`frontend/web/src/assets/fly/walking-fly.glb` was imported from the user's local
`fly-escape` project with explicit reuse permission. No standalone public
redistribution license was supplied for that asset, so it is not offered under
Apache-2.0. Its source revision, checksum, transformations, used animation
clips, and limitations are recorded in
[`frontend/web/src/assets/fly/walking-source.json`](frontend/web/src/assets/fly/walking-source.json).

The DrosoLift production application does not load or bundle that GLB. It uses
the original procedural geometry in `frontend/web/src/procedural-fly.ts`, a new
Apache-2.0 project contribution. Its illustrative proportions, materials and
animation clips are authored; it is not the MaleCNS specimen. Reproduction,
rights and display limitations are documented in
[`docs/drosolift/ASSETS.md`](docs/drosolift/ASSETS.md).

The separate public source snapshot also omits that GLB and its legacy rendered
media. Its preserved provenance record documents the historical import; it does
not grant redistribution rights. Complete upstream history is retained in the
original local implementation checkout. The public snapshot records its audited
upstream revision and source lineage without publishing the restricted blob.

## Three.js runtime

The compiled DrosoLift browser includes Three.js and its official addons under
the MIT License, Copyright © 2010-2026 three.js authors. The complete copyright,
permission grant and disclaimer are preserved in
[`licenses/three-MIT.txt`](licenses/three-MIT.txt) and included in the portable
conference package. TypeScript, Bun and Vite are build tools, not copied runtime
packages in that static distribution.
