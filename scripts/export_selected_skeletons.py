"""Rebuild the bounded official MaleCNS SWC cache, preserving native atlas axes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

SELECTED = {
    10783: "b702c072f0a2ae0ce5531e14a4b7e197f8d13b39ac864ad7fa2c601d129e0d50",
    11177: "df374c15104b8ed60c454a1f4f21d352da0ed2c21d4a33055d89c391d068ae16",
    36800: "d2cffd75c247833252b3f9ce71f59827bfe9fff3d032a70e13d8f166b8cfcdd1",
    63316: "ecfac3f0cedfdf5a7a7b50f01194ec0df97c065f48d10c02f887764bbd635075",
    201965: "56efbce74bbde158d5e037ebe837fc3a1449d209a889cfe5278934474247e7c2",
    80841: "92b82db8cd96d23eb81299b42a0af1dadc56faafc23f2b7f960f2669c868f396",
    10702: "1dd54734c3e9edd9cb5bca7a1dd76d2d4539a5c8b44e47dabdeb36e2a3466f97",
    67052: "f83d5c4c6dd69922fc6cd9d20e9947f305bb4abbb4fd477c92ff93822ceafb2c",
}
SOURCE = "https://storage.googleapis.com/flyem-male-cns/v1.0/segmentation/skeletons-malecns/skeletons-swc/"


def build(root: Path) -> dict:
    """Use the exact overview normalization; do not fit each skeleton separately."""
    manifest = json.loads((root / "data/malecns/v1.0/source-manifest.json").read_text())
    source = manifest["sources"]["annotations"]
    raw = root / "data/raw/malecns/v1.0"
    annotation = raw / source["url"].rsplit("/", 1)[-1]
    if hashlib.sha256(annotation.read_bytes()).hexdigest() != source["sha256"]:
        raise ValueError("Official annotations checksum mismatch")
    table = pd.read_feather(annotation, columns=["bodyId", "superclass", "somaLocation"])
    coordinates = []
    for row in table.to_dict("records"):
        superclass = row["superclass"]
        point = row["somaLocation"]
        if not isinstance(superclass, str) or not superclass or "tbc" in superclass.lower():
            continue
        if not isinstance(point, (list, tuple, np.ndarray)):
            continue
        point = np.asarray(point, dtype=float)
        if point.shape == (3,) and np.isfinite(point).all():
            coordinates.append(point)
    positions = np.asarray(coordinates)
    center = (positions.min(axis=0) + positions.max(axis=0)) / 2
    scale = 2 / float(np.ptp(positions, axis=0).max())
    runtime = json.loads((root / "data/circuits/gym-v1-runtime.json").read_text())
    runtime_ids = {edge[key] for edge in runtime["edges"] for key in ("body_pre", "body_post")}
    skeletons = []
    for body_id, digest in SELECTED.items():
        if body_id not in runtime_ids:
            raise ValueError("Selected morphology is not in the compact runtime")
        content = (raw / f"skeletons/{body_id}.swc").read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError(f"Skeleton checksum mismatch: {body_id}")
        nodes = []
        for line in content.decode().splitlines():
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) != 7:
                raise ValueError("Malformed SWC")
            node = [int(fields[0]), int(fields[1]), *map(float, fields[2:6]), int(fields[6])]
            if not all(np.isfinite(value) for value in node):
                raise ValueError("Nonfinite SWC")
            nodes.append(node)
        if len(nodes) > 20_000:
            raise ValueError("Selected morphology exceeds display budget")
        ids = {node[0] for node in nodes}
        if len(ids) != len(nodes) or any(node[6] != -1 and node[6] not in ids for node in nodes):
            raise ValueError("Broken SWC parent links")
        skeletons.append({"body_id":body_id,"url":f"{SOURCE}{body_id}.swc","sha256":digest,
                          "source_bytes":len(content),"nodes":nodes})
    return {"schema":1,"dataset":manifest["dataset"],"license":"CC-BY-4.0",
            "license_url":"https://creativecommons.org/licenses/by/4.0/",
            "credit":"MaleCNS / FlyEM (HHMI Janelia), University of Cambridge, MRC LMB and Google Research",
            "coordinate_units_nm":8,"annotation_source":source,
            "transform":{"center":center.tolist(),"scale":scale,"display_y_sign":-1},
            "changes":"SWC columns preserved; source comments omitted; exact parent connectivity retained; no skeleton simplification",
            "skeletons":skeletons}


if __name__ == "__main__":
    project = Path(__file__).resolve().parents[1]
    cache = build(project)
    destination = project / "frontend/web/public/assets/selected-skeletons.json"
    destination.write_text(json.dumps(cache, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Saved {destination.stat().st_size} bytes; " + ", ".join(
        f'{s["body_id"]}: {len(s["nodes"])} nodes' for s in cache["skeletons"]))
