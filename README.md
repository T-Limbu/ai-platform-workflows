# ai-platform-workflows 🚀

This repository provides reusable, standardized GitHub Actions workflows for the Autonomous AI Data Squad across all squad repositories.

---

## 🏛️ Standard Reusable Workflows

### 1. Reusable CI Test Gate (`ci-test.yml`)

Standardized automated test execution, dependency caching, and quality gatekeeping across squad projects.

**Usage in caller repos (`.github/workflows/test.yml`):**

```yaml
name: Test Suite Guard

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]

jobs:
  test:
    uses: T-Limbu/ai-platform-workflows/.github/workflows/ci-test.yml@v1.0.0
    with:
      working_directory: 'frontend' # or '.'
      node_version: '20'
      install_command: 'npm ci || npm install'
      test_command: 'npm test'
```

---

### 2. Reusable Production Release & Render Deploy (`render-release.yml`)

Deterministic release pipeline enforcing test gates, production compilation, zip packaging, GitHub Release asset attachment, and direct dispatch to the Render REST API. The job polls Render (every 15 s, up to 20 minutes) and fails unless the deploy reaches `live`; the result is reported in `$GITHUB_STEP_SUMMARY`.

Callers pin this repo by **release tag** (for example `@v1.0.0`), not `@main`.

**Inputs worth knowing:**

| Input | Default | Notes |
| -- | -- | -- |
| `deploy_environment` | `production` | `production` or `qa`. Names the GitHub environment of the *calling* repo that gates the job. Qa callers pass `qa`. |
| `service_id` | required | Must match `^srv-[a-z0-9]+$`. |
| `clear_cache` | `do_not_clear` | `clear` or `do_not_clear`. |
| `commit_sha` | `''` | Ref to deploy; resolved to a full commit SHA before the Render call. |

The `install_command`, `test_command` and `build_command` inputs are shell commands by design: set them only in the caller's own workflow file.

**Owner setup:** each calling repo needs an environment named `production` (Settings → Environments) with the owner as required reviewer. Until reviewers are set the environment is unprotected and the job is not gated.

**Usage in caller repos (`.github/workflows/release.yml`):**

```yaml
name: Production Release & Version Deployment

on:
  release:
    types: [published]
  push:
    tags:
      - 'v*'
  workflow_dispatch:
    inputs:
      commit_sha:
        description: 'Commit SHA or Tag to deploy (Leave empty for latest)'
        required: false
        type: string
        default: ''
      clear_cache:
        description: 'Clear Render build cache?'
        required: true
        type: choice
        options:
          - 'do_not_clear'
          - 'clear'
        default: 'do_not_clear'

permissions:
  contents: write

jobs:
  deploy:
    uses: T-Limbu/ai-platform-workflows/.github/workflows/render-release.yml@v1.0.0
    with:
      service_id: 'srv-YOUR_RENDER_SERVICE_ID'
      working_directory: 'frontend'
      dist_directory: 'dist'
      deploy_environment: production # pass 'qa' on a qa job
      commit_sha: ${{ inputs.commit_sha || '' }}
      clear_cache: ${{ inputs.clear_cache || 'do_not_clear' }}
    secrets: inherit
```

---

### 3. YouTube Extractor (`youtube-extractor.yml`)

Extracts structured insights and breakdowns from YouTube video streams using Gemini models.

**Usage** (a reusable workflow is called at job level with `uses:`):

```yaml
jobs:
  extract-video:
    uses: T-Limbu/ai-platform-workflows/.github/workflows/youtube-extractor.yml@v1.0.0
    with:
      video_url: "https://www.youtube.com/watch?v=..."
      workflows_ref: v1.0.0 # same ref as in uses:
    secrets: inherit
```

`workflows_ref` (default `main`) selects which ref of this repo supplies `connectors/youtube/extractor.py`; pass the same tag you pinned in `uses:`. A dispatch inside this repo runs its own commit. Inputs reach the script only as environment variables, never pasted into shell source.

Requires `GEMINI_API_KEY` configured in repository secrets.

---

### 3. Reusable Layout Check (`layout-check.yml`)

Builds the app, starts it locally with a seeded login and checks every configured page at 320/360/414/768/1024/1440 px for sideways scroll, off-screen content, overlapping controls, clipped text and unreachable must-have elements (for example a hidden mobile nav). Report-only by default (`report_only: true`); set it to `false` to block merges. Module and config format: `layout-check/README.md`.
