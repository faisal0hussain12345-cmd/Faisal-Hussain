from __future__ import annotations
import argparse
from pathlib import Path
from banna.pipeline import render
from banna.openai_review import review_file

def main():
    parser=argparse.ArgumentParser(prog="BANNA",description="Photo-only AI documentary studio")
    sub=parser.add_subparsers(dest="command")
    rp=sub.add_parser("render",help="Render an approved storyboard and voice-over")
    rp.add_argument("--storyboard",type=Path,default=None)
    op=sub.add_parser("review-script",help="Opt-in editorial review using OpenAI API")
    op.add_argument("--input",type=Path,required=True)
    op.add_argument("--output",type=Path,default=Path("output/script_review.md"))
    op.add_argument("--model",default=None)
    args=parser.parse_args()
    if args.command in (None,"render"):
        print(render(getattr(args,"storyboard",None)))
    elif args.command=="review-script":
        print(f"OpenAI review saved: {review_file(args.input,args.output,args.model)}")

if __name__=="__main__":
    main()
