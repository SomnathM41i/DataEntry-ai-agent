"""
main.py — CLI entry point
Usage: python main.py --file biodata.pdf --key gsk_...
"""
import sys, argparse
from config.settings import load_config
from core.processor import process_file

def main():
    parser = argparse.ArgumentParser(description="Matrimony AI Agent CLI")
    parser.add_argument("--file",   required=True, help="File to process")
    parser.add_argument("--pages",  help="Page range e.g. 1-10")
    parser.add_argument("--key",    help="Groq API key")
    args   = parser.parse_args()
    config = load_config(api_key=args.key)
    if not config["api_key"]:
        print("ERROR: No Groq API key. Use --key or set GROQ_API_KEY in .env")
        sys.exit(1)
    process_file(args.file, config, args.pages)

if __name__ == "__main__":
    main()
