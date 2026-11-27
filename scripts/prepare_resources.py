"""Convert documented hourly weather CSVs or export explicit synthetic resources."""
import argparse
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.data_loader import demo_dataset, parse_resource_data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    origin = parser.add_mutually_exclusive_group(required=True)
    origin.add_argument("--input", type=Path)
    origin.add_argument("--demo", choices=["lakshadweep", "brest"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source")
    kind = parser.add_mutually_exclusive_group()
    kind.add_argument("--synthetic", action="store_true")
    kind.add_argument("--measured", action="store_true")
    args = parser.parse_args()
    if args.demo:
        dataset = demo_dataset(args.demo)
    else:
        if not args.source or not (args.synthetic or args.measured):
            parser.error("CSV input requires --source and one of --synthetic/--measured")
        with args.input.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            if not reader.fieldnames or "timestamp" not in reader.fieldnames:
                parser.error("CSV requires timestamp and weather columns")
            rows = list(reader)
        fields = [field for field in reader.fieldnames if field != "timestamp"]
        try:
            data = {"timestamps": [row["timestamp"] for row in rows],
                    "weather": {field: [float(row[field]) for row in rows] for field in fields},
                    "provenance": {"source": args.source, "synthetic": args.synthetic}}
            dataset = parse_resource_data(data)
        except (ValueError, TypeError, KeyError) as exc:
            parser.error(str(exc))
    payload = {"timestamps": list(dataset["timestamps"]),
               "capacity_factors": {name: values.tolist() for name, values in dataset["capacity_factors"].items()},
               "provenance": {"source": dataset["source"], "synthetic": dataset["synthetic"]}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output:
        json.dump(payload, output, allow_nan=False, separators=(",", ":"))
    print(f"Wrote {len(payload['timestamps'])} hourly rows to {args.output}; synthetic={dataset['synthetic']}")


if __name__ == "__main__":
    main()
