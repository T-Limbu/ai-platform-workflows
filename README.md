# squad-workflows

This repository provides reusable GitHub Actions workflows for the AI Data Squad.

## Available Workflows

### YouTube Extractor

Extracts key insights and structured breakdowns from a YouTube video using Gemini models.

**Usage:**

```yaml
jobs:
  extract-video:
    runs-on: ubuntu-latest
    steps:
      - uses: T-Limbu/squad-workflows/.github/workflows/youtube-extractor.yml@main
        with:
          video_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
          # prompt: "Custom prompt" (optional)
          # output_format: "json" or "markdown" (optional, default: "json")
          # model: "gemini-3.8-flash" (optional)
        secrets: inherit
```

**Note:** You must provide `GEMINI_API_KEY` in your secrets for the model extraction to work.

**Outputs:**
- `extracted_content`: The extracted text directly accessible as a string.
- `output_file`: Path to the generated output file (`output.json` or `output.md`).
- Additionally, an artifact named `youtube-extraction` is uploaded.
