# 0009: isolated saved profiles and a licensed public source snapshot

Accepted 5 November 2026 under the user's publication-hardening request.

The local research server shares one gym and only persists learned memory. A
visitor-facing copy needs independent model state, saved training progress and
duplicate-safe commands after restart. An opt-in `public-web` boundary composes
the existing Python model with opaque cookie profiles and exact Origin checks.
One SQLite database stores finite versioned full-state checkpoints and command
outcomes atomically before acknowledgement. No external account service,
background training or new neural dynamics is introduced. One worker and explicit
quotas are the operational cost; future horizontal scaling needs another design.

The full upstream history contains a walking GLB with no established public
redistribution license. Preserve that history locally and publish a separately
inventoried clean snapshot with explicit upstream lineage, existing license and
third-party notices. Do not rewrite local history or falsely license the asset.
The public initial commit consequently has no upstream Git ancestry; lineage
metadata identifies its source. Licensed procedural art remains the runtime asset.

The user explicitly declined deployment/hosting. Provide local instructions,
pinned dependencies, CI, an optional container and a static replay hosting config;
create no remote runtime resources. Repository creation/publication is authorized.
