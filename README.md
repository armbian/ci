<h3 align="center">
  <a href="#"><img src="https://raw.githubusercontent.com/armbian/.github/master/profile/logosmall.png" alt="Armbian logo"></a>
  <br><br>
</h3>

# Armbian CI

Central home for Armbian's build automation: the reusable GitHub Actions pipeline that produces Armbian artifacts and images, plus the `userpatches/` and release-notes headers those builds consume.

## Purpose of this repository

This repo drives the "build all the things" side of Armbian releases. It contains:

- **Reusable pipeline workflows** that clone [`armbian/build`](https://github.com/armbian/build), run `compile.sh` across a large per-board matrix, and publish the resulting artifacts to OCI (`ghcr.io/armbian/os/*`) and images to GitHub Releases.
- **Thin "track" wrappers** (nightly, stable, community, apps, standard-support) that call the reusable pipeline on schedules or on manual dispatch.
- **Userpatches** (`userpatches/`) — configs, image customization, and optional extensions that the build framework picks up during a run.
- **Release header generators** (`release-headers/`) — small scripts that emit the HTML body used when the release is created.
- **Operational workflows** — a watchdog that auto-retries jobs killed by self-hosted runner stalls, and a housekeeping job that prunes old releases.

## Repository layout

```
.
├── .github/
│   ├── actionlint.yaml
│   ├── dependabot.yml
│   └── workflows/
│       ├── auto-retry-stalled.yml           # watchdog: re-run failed jobs of a stalled run
│       ├── build-all.yml                    # track: Build All Artifacts
│       ├── build-all-stable.yml             # track: Build All Stable Artifacts
│       ├── build-apps.yml                   # track: Build Apps Images
│       ├── build-community.yml              # track: Build Community Images
│       ├── build-nightly.yml                # track: Build Nightly Images
│       ├── build-standard-support.yml       # track: Build Standard Support (admin)
│       ├── complete-artifact-matrix.yml     # THE reusable pipeline
│       ├── build-artifacts-chunk.yml        # reusable: one chunk of artifacts
│       ├── build-images-chunk.yml           # reusable: one chunk of images
│       └── delete-old-releases.yml          # housekeeping: prune old releases
├── userpatches/
│   ├── config-armbian-apps.conf
│   ├── config-armbian-cloud.conf
│   ├── config-armbian-community.conf
│   ├── config-armbian-images.conf
│   ├── customize-image.sh
│   ├── targets-all-not-eos.yaml
│   └── extensions/
│       ├── docker-ce.sh
│       ├── ha.sh
│       ├── kali.sh
│       ├── omv.sh
│       └── openhab.sh
├── release-headers/
│   ├── community.sh
│   └── os.sh
└── README.md
```

## How the pipeline is organised

The pipeline is written **once** in `complete-artifact-matrix.yml`. Each per-track workflow is a thin wrapper that calls it via `uses:` with track-specific inputs (target repository, target path, team, targets file, defaults for the manual-dispatch menu).

Flow inside the reusable pipeline:

```
team_check
   └─> version_prep          # resolves version, creates the GitHub Release up front
        └─> matrix_prep      # runs `compile.sh gha-matrix` -> chunked JSON matrices
             ├─> build-artifacts-chunk.yml  (matrixed, one job per chunk)
             └─> build-images-chunk.yml    (matrixed, one job per chunk)
                  └─> publish / closing
```

The per-chunk build bodies live in `build-artifacts-chunk.yml` and `build-images-chunk.yml` — each is written once and fanned out over a chunk matrix by the orchestrator.

## Tracks (callers of the reusable pipeline)

| Workflow | Trigger | Release repo | Target path | Ref | Targets file |
|---|---|---|---|---|---|
| `build-nightly.yml` — Build Nightly Images | `cron: 30 22 * * *` + manual | `os` | `nightly/` | `nightly` | `targets-release-nightly.yaml` |
| `build-all.yml` — Build All Artifacts | `cron: 0 20-23/2,0-4/2 * * *`, `0 8,14 * * *` + manual | `os` | `cron/` | `all` | `targets-all-not-eos.yaml` |
| `build-all-stable.yml` — Build All Stable Artifacts | `cron: 0 2 * * *` + manual | `os` | `stable/` | `all` | `targets-all-not-eos.yaml` |
| `build-standard-support.yml` — Build Standard Support (admin) | manual | `os` | `stable/` | `stable` | `targets-release-standard-support.yaml` |
| `build-community.yml` — Build Community Images | `cron: 0 23 * * THU` + manual | `community` | `community/` | `stable` | `targets-release-community-maintained.yaml` |
| `build-apps.yml` — Build Apps Images | manual | `distribution` | `apps/` | `stable` | `targets-release-apps.yaml` |

Common manual-dispatch inputs on the tracks that expose them:

- `skipImages` — build images or artifacts only.
- `checkOci` — reuse existing artifacts already in OCI, or rebuild everything.
- `extraParamsAllBuilds` — extra `KEY=value` passed to every `compile.sh` invocation (e.g. `DEBUG=yes`).
- `branch` — framework build branch to check out from `armbian/build` (default `main`).
- `targetsFilterInclude` — matrix filter, e.g. `BOARD:odroidhc4,BOARD:odroidn2`.
- `nightlybuild` — nightly vs. stable semantics.
- `versionOverride` — force a specific version string.

`build-all.yml` and `build-nightly.yml` intentionally expose only a couple of inputs; everything else falls back to the per-track defaults declared inside the wrapper, so a manual run matches a scheduled run.

## Versioning

Versioning is driven entirely by GitHub releases on the target repository — there is no version file in this repo:

- **Stable** builds require `versionOverride` (e.g. `26.8.0`).
- **Nightly** builds pick the newest `<base>-trunk.N` release in the target repo and bump `N`; `versionOverride` can seed a new base series.

The release is created empty up front by `version_prep`, and the image jobs attach assets to that tag.

## Userpatches

The `userpatches/` directory is checked out inside every build and copied into the framework's `userpatches/` folder before `compile.sh` runs. It contains:

- `config-armbian-images.conf`, `config-armbian-community.conf`, `config-armbian-apps.conf`, `config-armbian-cloud.conf` — per-config build settings (selected via each track's `prepare_config`).
- `customize-image.sh` — image customization hook.
- `targets-all-not-eos.yaml` — targets list used by the "all" tracks (release-specific target lists are fetched at build time from [`armbian/armbian.github.io`](https://github.com/armbian/armbian.github.io) `data` branch).
- `extensions/` — optional build extensions: `docker-ce.sh`, `ha.sh`, `kali.sh`, `omv.sh`, `openhab.sh`.

## Release headers

`release-headers/os.sh` and `release-headers/community.sh` generate the HTML body attached to newly-created releases. `version_prep` picks the one matching the track's `release_repository`; if none matches, an empty body is used.

## Operational workflows

### `auto-retry-stalled.yml` — self-healing against runner stalls

Self-hosted runners occasionally drop mid-job (the build itself is green, but a later step like log upload dies), which marks the whole run failed. This watchdog listens for `workflow_run: completed` on the build tracks and, if the run failed:

- Counts failed jobs in the latest attempt.
- If `run_attempt < 10` **and** `failed <= MAX_FAILED_TO_RETRY` (default `30`), calls `gh run rerun --failed` to restart only the failed jobs.
- Otherwise leaves the run red and emits a warning — that shape of failure looks systemic, not a stall.

It also has a `workflow_dispatch` entry with a `run_id` input (and `ignore_threshold`) so an operator can force a re-run of a specific run's failed jobs.

Note: the build chunks are `fail-fast: false`, so good jobs finish and upload artifacts even while a few stall. The watchdog therefore waits for the run to finish rather than cancelling it.

### `delete-old-releases.yml` — release housekeeping

Runs daily at 03:00 UTC (and on manual dispatch). Only runs when the repo owner is `armbian`. For both full releases and pre-releases, it keeps the newest 3 (sorted by `created_at`) and deletes the rest via the GitHub API.

## Build execution details

Per-chunk jobs (`build-artifacts-chunk.yml`, `build-images-chunk.yml`):

- Run with `fail-fast: false` so a single unstable board does not sink its neighbours.
- Timeouts: 65 min for artifact chunks (60 min build + OCI push), 75 min for image chunks (45 min build + sign/torrent/upload).
- Retry the actual `compile.sh` invocation up to `BUILD_ATTEMPTS` (default `3`) times to ride out transient network/runner flakes, replacing an older external watchdog.
- Look up per-runner metadata from `https://github.armbian.com/servers/github-runners.jq` and export `APT_PROXY_ADDR`, `GHCR_MIRROR_ADDRESS`, `CCACHE_REMOTE_STORAGE`, `GITPROXY_ADDRESS` when the runner advertises them. Any ambient `http_proxy`/`https_proxy` from the runner host is neutralised first; a configured apt proxy is probed before use and dropped if unreachable.
- Log in to `ghcr.io` and push artifacts to `ghcr.io/armbian/os/*`. This requires a PAT with `write:packages` on `armbian/os`; the workflow uses `ACCESS_TOKEN` and falls back to `GITHUB_TOKEN` when unset.
- Image chunks also pull release-target YAML files from the `data` branch of `armbian/armbian.github.io`.

## Secrets

Used by the reusable pipeline / chunk workflows (declared as `secrets: inherit` on the callers):

- `ACCESS_TOKEN` — cross-repo PAT (write to `armbian/os` etc., `write:packages` on GHCR). Optional; falls back to `GITHUB_TOKEN` for read/limited paths.
- `ORG_MEMBERS` — used by `armbian/actions/team-check` to gate who can trigger a run.
- `KEY_UPLOAD`, `KNOWN_HOSTS_ARMBIAN_UPLOAD` — required by image chunks to publish images.
- `GPG_KEY1`, `GPG_PASSPHRASE1` — optional, for signing.

## Related repositories

- [`armbian/build`](https://github.com/armbian/build) — the build framework (`compile.sh`) this pipeline drives.
- [`armbian/os`](https://github.com/armbian/os), [`armbian/community`](https://github.com/armbian/community), [`armbian/distribution`](https://github.com/armbian/distribution) — release repositories where images and artifact metadata land.
- [`armbian/actions`](https://github.com/armbian/actions) — shared composite actions (`runner-clean`, `team-check`, …) used by the workflows here.
- [`armbian/armbian.github.io`](https://github.com/armbian/armbian.github.io) — hosts the release-target YAML files (`data` branch).

## Further reading

- Armbian documentation: <https://docs.armbian.com>
- Project home: <https://www.armbian.com>
