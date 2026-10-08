import argparse
import os
import sys
import json
import re
from google import genai
from google.genai import types
from google.genai.errors import APIError

MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]

def get_video_id(url: str) -> str:
    """Extracts the YouTube video ID from a given URL."""
    # Handle standard urls
    match = re.search(r"v=([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)
    
    # Handle short urls (youtu.be)
    match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)
    
    # Handle embed urls
    match = re.search(r"embed/([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)
        
    raise ValueError(f"Could not extract video ID from URL: {url}")

def main():
    parser = argparse.ArgumentParser(description="Extract insights from a YouTube video.")
    parser.add_argument("--url", required=True, help="YouTube video URL")
    parser.add_argument("--prompt", default="Extract all key principles, actionable techniques, and concrete rules from this video into a structured breakdown.")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--model", default="gemini-3.8-flash")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    try:
        video_id = get_video_id(args.url)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    canonical_url = f"https://www.youtube.com/watch?v={video_id}"
    
    client = genai.Client(api_key=api_key)
    video_part = types.Part.from_uri(file_uri=canonical_url, mime_type="video/mp4")
    prompt_part = types.Part.from_text(text=args.prompt)
    
    models_to_try = [args.model]
    for m in MODELS:
        if m not in models_to_try:
            models_to_try.append(m)
            
    extracted_content = None
    used_model = None

    for model in models_to_try:
        try:
            response = client.models.generate_content(
                model=model,
                contents=[video_part, prompt_part]
            )
            extracted_content = response.text
            used_model = model
            break
        except APIError as e:
            if e.code in (503, 404):
                print(f"Model {model} failed with {e.code}, trying next model...", file=sys.stderr)
                continue
            else:
                print(f"Error generating content with {model}: {e}", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"Error generating content with {model}: {e}", file=sys.stderr)
            sys.exit(1)
            
    if extracted_content is None:
        print("Error: All models failed to generate content.", file=sys.stderr)
        sys.exit(1)
        
    output_filename = "output.json" if args.format == "json" else "output.md"
    
    if args.format == "json":
        try:
            # Try to parse if it returned markdown wrapped json
            if extracted_content.startswith("```json"):
                content_to_save = extracted_content.replace("```json\\n", "").replace("```json", "").replace("```", "").strip()
                parsed = json.loads(content_to_save)
            else:
                parsed = json.loads(extracted_content)
            content_to_save = json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            # Fallback if the model didn't return valid JSON
            content_to_save = json.dumps({"raw_content": extracted_content}, indent=2)
    else:
        content_to_save = extracted_content

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(content_to_save)
        
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        # Multiline output in GitHub Actions
        delimiter = "EOF"
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"output_file={output_filename}\\n")
            f.write(f"extracted_content<<{delimiter}\\n{content_to_save}\\n{delimiter}\\n")

    print(f"Extraction successful using {used_model}. Output saved to {output_filename}")

if __name__ == "__main__":
    main()
