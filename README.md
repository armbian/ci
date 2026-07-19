# Armbian CI

The continuous-integration pipeline for the [Armbian Linux distribution](https://www.armbian.com/). It builds, packages, and publishes Armbian OS images and artifacts (kernels, u-boot, firmware, rootfs, board-support packages) across every release channel — **nightly, stable, community, and apps** — driving the [`armbian/build`](https://github.com/armbian/build) framework.

> Live run status across all Armbian automation is aggregated at [actions.armbian.com](https://actions.armbian.com/).

## How it works

Every build workflow is a thin **track wrapper** around one reusable pipeline, [`complete-artifact-matrix.yml`](.github/workflows/complete-artifact-matrix.yml). Each wrapper supplies only its schedule and inputs (which targets to build, where to publish); the reusable workflow does the work:

```
team_check → version_prep → matrix_prep → build-artifacts (chunks) → build-images (chunks) → publish-debs-to-repo → closing
```

- **Artifacts** (kernels, u-boot, bsp, firmware, rootfs) are content-addressed and cached in the shared OCI registry `ghcr.io/armbian/os/*`. A run only compiles what is not already in the cache.
- **Images** are assembled from those artifacts, uploaded to the mirror `incoming/` area, and the download pages are refreshed via a repository-dispatch to [`armbian/armbian.github.io`](https://github.com/armbian/armbian.github.io).
- Per-chunk build bodies live in [`build-artifacts-chunk.yml`](.github/workflows/build-artifacts-chunk.yml) and [`build-images-chunk.yml`](.github/workflows/build-images-chunk.yml), fanned out over a chunk matrix.

The framework is pinned to [`armbian/build`](https://github.com/armbian/build) (branch `main` by default, overridable per run). Build config and userpatches are kept **in this repository**, so the pipeline is self-contained and rename-proof.

## Build tracks

| Workflow | Trigger | Target list | Output |
|---|---|---|---|
| **Build All Artifacts** — [`build-all.yml`](.github/workflows/build-all.yml) | cron (every ~2 h overnight + 08:00, 14:00) | `targets-all-not-eos.yaml` | OCI artifact cache only |
| **Build All Stable Artifacts** — [`build-all-stable.yml`](.github/workflows/build-all-stable.yml) | cron (02:00 daily) | `targets-all-not-eos.yaml` | OCI artifact cache only |
| **Build Nightly Images** — [`build-nightly.yml`](.github/workflows/build-nightly.yml) | cron (22:30 daily) | `targets-release-nightly.yaml` | `nightly/` (rolling releases) |
| **Build Community Images** — [`build-community.yml`](.github/workflows/build-community.yml) | cron (Thu 23:00) | `targets-release-community-maintained.yaml` | `community/` |
| **Build Standard Support Images** — [`build-standard-support.yml`](.github/workflows/build-standard-support.yml) | manual (admin) | `targets-release-standard-support.yaml` | `stable/` |
| **Build Apps Images** — [`build-apps.yml`](.github/workflows/build-apps.yml) | manual | `targets-release-apps.yaml` | `apps/` (distribution) |

The two **Build All …** tracks only refresh the **artifact cache** (`skipImages=yes`). Every image track depends on that cache being fresh, so those must succeed first.

Target lists (`targets-release-*.yaml`) are generated from `image-info.json` by [`generate_targets.py`](https://github.com/armbian/armbian.github.io/blob/main/scripts/generate_targets.py) in `armbian.github.io`; `targets-all-not-eos.yaml` lives in [`userpatches/`](userpatches/) here.

## Versioning

Versions are driven by GitHub releases (there is no version file in the repo):

- **Stable** builds require an explicit `versionOverride` (e.g. `26.8.0`).
- **Nightly** builds take the newest `<base>-trunk.N` release and bump `N`.

## Housekeeping workflows

- **Auto-retry stalled runs** — [`auto-retry-stalled.yml`](.github/workflows/auto-retry-stalled.yml). Self-hosted runners occasionally drop mid-job and mark an otherwise-green run as failed. This watchdog re-runs **only the failed jobs** of a completed build run (up to 9 attempts); it backs off when many jobs fail at once, since that looks systemic rather than like a stall.
- **Delete Old Releases** — [`delete-old-releases.yml`](.github/workflows/delete-old-releases.yml). Prunes stale GitHub releases daily at 03:00 UTC (gated to the `armbian` organization).

## Layout

```
.github/workflows/
  complete-artifact-matrix.yml   # reusable core pipeline
  build-artifacts-chunk.yml      # reusable: one artifact chunk
  build-images-chunk.yml         # reusable: one image chunk
  build-*.yml                    # per-track wrappers (schedule + inputs)
  auto-retry-stalled.yml         # stall watchdog
  delete-old-releases.yml        # release cleanup
userpatches/                     # self-contained build config, extensions, target list
release-headers/                 # per-repository release-notes headers (os, community)
```

## Related repositories

- [`armbian/build`](https://github.com/armbian/build) — the build framework this pipeline drives.
- [`armbian/armbian.github.io`](https://github.com/armbian/armbian.github.io) — release-target generation (`generate_targets.py`) and the download-page index.
- [`armbian/os`](https://github.com/armbian/os) — the shared OCI package namespace (`ghcr.io/armbian/os/*`) these builds read and write; the automation here supersedes the legacy workflows in that repo.

## Documentation

Process and maintainer documentation: **[docs.armbian.com/Process_CI](https://docs.armbian.com/Process_CI/)**.
