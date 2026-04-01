"""Pre-download the NLI model at build time so cold starts are instant."""

import argparse
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default="/models")
    parser.add_argument(
        "--model-name",
        default="facebook/bart-large-mnli",
        help="HuggingFace model ID for zero-shot NLI",
    )
    args = parser.parse_args()

    os.makedirs(args.model_dir, exist_ok=True)
    os.environ["TRANSFORMERS_CACHE"] = args.model_dir
    os.environ["HF_HOME"] = args.model_dir

    print(f"Downloading {args.model_name} → {args.model_dir}")

    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        args.model_name, cache_dir=args.model_dir
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name, cache_dir=args.model_dir
    )

    print(f"Model cached. Size: {sum(p.numel() for p in model.parameters()) / 1e6:.0f}M params")
    print("Done.")


if __name__ == "__main__":
    main()