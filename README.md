<h2 align="center">
  <a href=#><img src="https://raw.githubusercontent.com/armbian/.github/master/profile/logosmall.png" alt="Armbian logo"></a>
  <br><br>
</h2>

# Armbian CI

## Purpose of This Repository

Central home for Armbian's build automation: the reusable GitHub Actions pipeline that produces Armbian artifacts and images across nightly, stable, community and apps tracks, plus the `userpatches/` and release-notes headers those builds consume.

## What's inside

- **A reusable pipeline** (`complete-artifact-matrix.yml`) that clones [`armbian/build`](https://github.com/armbian/build), runs `compile.sh` across a per-board matrix, and publishes artifacts to OCI (`ghcr.io/armbian/os/*`) and images to GitHub Releases.
- **Thin per-track wrappers** — nightly, all, all-stable, standard-support, community, apps, base-files — that call the reusable pipeline on schedules or on manual dispatch with track-specific inputs.
- **Chunk workers** — `build-artifacts-chunk.yml` and `build-images-chunk.yml` — each is the per-chunk build body, written once and fanned out over a chunk matrix by the orchestrator.
- **Userpatches** (`userpatches/`) — configs, image customization, and optional extensions the build framework picks up during a run.
- **Release header generators** (`release-headers/`) — small shell scripts that emit the HTML body used when a release is created.
- **Operational workflows** — a watchdog that auto-retries jobs killed by self-hosted runner stalls, housekeeping that prunes old releases, and PR maintenance (labels, review listening).

For an overview of workflow runs on this repo, see the Armbian CI dashboard:

**CI overview:** <https://actions.armbian.com/?repo=ci>

## Repository layout

```
.
├── .github/
│   ├── actionlint.yaml
│   ├── dependabot.yml
│   ├── labeler.yml
│   ├── labels.yml
│   └── workflows/                       # reusable pipeline, track callers, ops
├── userpatches/
│   ├── config-armbian-apps.conf
│   ├── config-armbian-cloud.conf
│   ├── config-armbian-community.conf
│   ├── config-armbian-images.conf
│   ├── customize-image.sh
│   ├── targets-all-not-eos.yaml
│   ├── targets-base-files.yaml
│   └── extensions/
│       ├── docker-ce.sh
│       ├── ha.sh
│       ├── kali.sh
│       ├── omv.sh
│       └── openhab.sh
├── release-headers/
│   ├── community.sh
│   └── os.sh
├── tools/
│   └── update-workflow-board-lists.py
└── README.md
```

## How the pipeline is organised

The pipeline is written **once** in `.github/workflows/complete-artifact-matrix.yml`. Each per-track workflow is a thin wrapper that calls it via `uses:` with track-specific inputs (target repository, target path, team, targets file, defaults for the manual-dispatch menu).

Flow inside the reusable pipeline:

```
team_check
   └─> version_prep          # resolves version, creates the GitHub Release up front
        └─> matrix_prep      # runs `compile.sh gha-matrix` -> chunked JSON matrices
             ├─> build-artifacts-chunk.yml   (matrixed, one job per chunk)
             └─> build-images-chunk.yml     (matrixed, one job per chunk)
                  └─> publish / closing
```

## Tracks (callers of the reusable pipeline)

| Workflow | Trigger | Release repo | Target path | Ref | Targets file |
|---|---|---|---|---|---|
| `build-nightly.yml` — Build Nightly Images | daily `30 22 * * *` + manual | `os` | `nightly/` | `nightly` | `targets-release-nightly.yaml` |
| `build-all.yml` — Build All Artifacts | `0 20-23/2,0-4/2 * * *`, `0 8,14 * * *` + manual | `os` | `cron/` | `all` | `targets-all-not-eos.yaml` |
| `build-all-stable.yml` — Build All Stable Artifacts | weekly `0 18 * * 1` + manual | `os` | `stable/` | `all` | `targets-all-not-eos.yaml` |
| `build-standard-support.yml` — Build Standard Support (admin) | manual | `os` | `images/` | `stable` | `targets-release-standard-support.yaml` |
| `build-community.yml` — Build Community Images | weekly `0 23 * * THU` + manual | `community` | `community/` | `stable` | `targets-release-community-maintained.yaml` |
| `build-apps.yml` — Build Apps Images | manual | `distribution` | `apps/` | `stable` | `targets-release-apps.yaml` |
| `build-base-files.yml` — Build Base Files | daily `0 4 * * *` + manual | `os` | `base-files/` | `all` | `targets-base-files.yaml` |

Common manual-dispatch inputs exposed by the tracks that surface them:

- `branch` — framework build branch to check out from `armbian/build` (default `main`).
- `forceDockerPull` — pull latest Docker image (default `yes` for manual runs) or use cached.
- `targetsFilterInclude` — matrix filter, e.g. `BOARD:odroidhc4,BOARD:odroidn2`.
- `versionOverride` — force a specific version string.
- `extraParamsAllBuilds` (base-files) — extra `KEY=value` passed to every `compile.sh` invocation (e.g. `DEBUG=yes`).
- `board` / `maintainer` (standard-support) — build a single board or all boards of a given maintainer.

## Versioning

Versioning is driven entirely by GitHub releases on the target repository — there is no version file in this repo:

- **Stable** builds reuse the latest `X.Y.Z` release as-is; `versionOverride` cuts a new version. The weekly `build-all-stable` opts into `stable_bump: yes`, which bumps `X.Y.Z -> X.Y.(Z+1)`.
- **Nightly** builds pick the newest `<base>-trunk.N` release in the target repo and bump `N`; `versionOverride` can seed a new base series.
- A `-trunk.N` counter can be shared across a leader repo and peer repos (`trunk_peer_repositories`) so numbering stays monotonic across e.g. `armbian/ci` and `armbian/community`.

The release is created empty up front by `version_prep`, and the image jobs attach assets to that tag.

## Userpatches

The `userpatches/` directory is checked out inside every build and copied into the framework's `userpatches/` folder before `compile.sh` runs. It contains:

- `config-armbian-images.conf`, `config-armbian-community.conf`, `config-armbian-apps.conf`, `config-armbian-cloud.conf` — per-config build settings (selected via each track's `prepare_config`).
- `customize-image.sh` — image customization hook.
- `targets-all-not-eos.yaml`, `targets-base-files.yaml` — targets lists (release-specific targets are additionally fetched at build time from [`armbian/armbian.github.io`](https://github.com/armbian/armbian.github.io) `data` branch).
- `extensions/` — optional build extensions: `docker-ce.sh`, `ha.sh`, `kali.sh`, `omv.sh`, `openhab.sh`.

## Release headers

`release-headers/os.sh` and `release-headers/community.sh` generate the HTML body attached to newly-created releases. `version_prep` picks the one matching the track's `release_repository`; if none matches, an empty body is used.

## Operational workflows

- **Auto-retry stalled runs.** Listens for `workflow_run: completed` on the build tracks and, if the run failed, re-runs only the failed jobs via `gh run rerun --failed`, guarded by an attempt budget and a majority-green threshold. A `workflow_dispatch` entry with `run_id` (and `ignore_threshold`) lets an operator force a re-run of a specific run.
- **Delete old releases.** Runs daily at 03:00 UTC; only runs when the repo owner is `armbian`. Keeps the newest 3 stable (`X.Y.Z`) and 3 trunk (`X.Y.Z-trunk.N`) releases sorted by parsed version, prunes the rest.
- **PR maintenance.** Auto-labels PRs by size, category, and quarter; removes `Ready to merge` on new commits; adds it back on committer approval; syncs `.github/labels.yml` to actual repo labels.

## Tooling

`tools/update-workflow-board-lists.py` regenerates the `board` and `maintainer` choice lists in `build-standard-support.yml` between the `>>> board-options` / `>>> maintainer-options` sentinel comments — do not edit those lists by hand.

## Built with

- **YAML** — GitHub Actions workflows in `.github/workflows/`, Dependabot, actionlint and labeler configs.
- **Bash** — steps inside those workflows (via `run:`), release-header generators, `customize-image.sh`, and the extensions in `userpatches/extensions/`.
- **Python 3** — `tools/update-workflow-board-lists.py`.
- **Shell tools invoked by the pipeline**: `gh` (GitHub CLI), `jq`, `curl`, `rsync`, `mktorrent`, plus the `armbian/build` framework's `compile.sh`.
- **Shared actions**: [`armbian/actions`](https://github.com/armbian/actions) (`runner-clean`, `team-check`) and standard actions such as `actions/checkout`, `actions/labeler`, `docker/login-action`.

## Related repositories

- [`armbian/build`](https://github.com/armbian/build) — the build framework this repo drives.
- [`armbian/armbian.github.io`](https://github.com/armbian/armbian.github.io) — release-target YAML consumed at build time (`data` branch).
- [`armbian/actions`](https://github.com/armbian/actions) — shared composite/JS actions used by these workflows.

## Links

- Documentation: <https://docs.armbian.com>
- Project website: <https://www.armbian.com>
- CI overview for this repo: <https://actions.armbian.com/?repo=ci>
