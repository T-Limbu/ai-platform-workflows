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
    uses: T-Limbu/ai-platform-workflows/.github/workflows/ci-test.yml@main
    with:
      working_directory: 'frontend' # or '.'
      node_version: '20'
      install_command: 'npm ci || npm install'
      test_command: 'npm test'
```

---

### 2. Reusable Production Release & Render Deploy (`render-release.yml`)

Deterministic release pipeline enforcing test gates, production compilation, zip packaging, GitHub Release asset attachment, and direct dispatch to the Render REST API with `$GITHUB_STEP_SUMMARY` audit reporting.

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
    uses: T-Limbu/ai-platform-workflows/.github/workflows/render-release.yml@main
    with:
      service_id: 'srv-YOUR_RENDER_SERVICE_ID'
      working_directory: 'frontend'
      dist_directory: 'dist'
      commit_sha: ${{ inputs.commit_sha || '' }}
      clear_cache: ${{ inputs.clear_cache || 'do_not_clear' }}
    secrets: inherit
```

---

### 3. YouTube Extractor (`youtube-extractor.yml`)

Extracts structured insights and breakdowns from YouTube video streams using Gemini models.

**Usage:**

```yaml
jobs:
  extract-video:
    runs-on: ubuntu-latest
    steps:
      - uses: T-Limbu/ai-platform-workflows/.github/workflows/youtube-extractor.yml@main
        with:
          video_url: "https://www.youtube.com/watch?v=..."
        secrets: inherit
```

Requires `GEMINI_API_KEY` configured in repository secrets.
