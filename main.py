from __future__ import annotations
import argparse
from pathlib import Path
from banna.pipeline import render
from banna.openrouter_review import review_file
from banna.gemini_text import generate_script_file


def main():
    parser = argparse.ArgumentParser(prog="BANNA", description="Zero-cost photo documentary studio")
    sub = parser.add_subparsers(dest="command")
    rp = sub.add_parser("render", help="Render an approved storyboard and voice-over")
    rp.add_argument("--storyboard", type=Path, default=None)
    draft = sub.add_parser("draft-script", help="Create a narration draft with Gemini free text tier")
    draft.add_argument("--topic", required=True)
    draft.add_argument("--audience", default="General audience")
    draft.add_argument("--language", default="English")
    draft.add_argument("--duration", type=int, default=10)
    draft.add_argument("--output", type=Path, default=Path("output/narration_draft.md"))
    review = sub.add_parser("review-script", help="Review narration using OpenRouter free models only")
    review.add_argument("--input", type=Path, required=True)
    review.add_argument("--output", type=Path, default=Path("output/script_review.md"))
    review.add_argument("--model", default=None)
    args = parser.parse_args()
    if args.command in (None, "render"):
        print(render(getattr(args, "storyboard", None)))
    elif args.command == "draft-script":
        print(f"Gemini draft saved: {generate_script_file(args.topic, args.audience, args.language, args.duration, args.output)}")
    elif args.command == "review-script":
        print(f"OpenRouter review saved: {review_file(args.input, args.output, args.model)}")


if __name__ == "__main__":
    main()
