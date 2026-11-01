"""Run the full pipeline: generate -> extract -> transform -> load -> report."""
from config import OUTPUT_DIR
from data_generator import generate_sample_data
from etl import extract, transform, load
from report import build_report


def main():
    raw_data, truth = generate_sample_data()
    df = extract(raw_data)
    df = transform(df)
    load_info = load(df)

    report_text = build_report(raw_data, df, load_info, truth)
    print(report_text)

    report_path = OUTPUT_DIR / "classification_report.txt"
    report_path.write_text(report_text)
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
