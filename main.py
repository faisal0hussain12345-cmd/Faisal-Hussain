from __future__ import annotations
import argparse
from pathlib import Path
from banna.pipeline import render

def main():
    parser=argparse.ArgumentParser(prog="BANNA",description="Photo-only AI documentary renderer")
    parser.add_argument("command",choices=["render"],nargs="?",default="render")
    parser.add_argument("--storyboard",type=Path,default=None)
    args=parser.parse_args()
    result=render(args.storyboard)
    print(result)

if __name__=="__main__":
    main()
