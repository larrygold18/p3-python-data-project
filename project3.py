"""
Project 3: Python Data Project
Fetch from the web -> Process with Python collections -> Write CSV, Excel, JSON, Text
Logging via utils_logger.py

Run:
    python project3.py
"""

from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from statistics import mean
from typing import List, Dict, Any

import requests
from openpyxl import Workbook

# Logging helper (copy this file from the example repo into your project root)
from utils_logger import get_logger  # type: ignore

# -----------------------
# Config
# -----------------------
RAW_DIR = os.path.join("data", "raw")
PROC_DIR = os.path.join("data", "processed")
LOG_DIR = "logs"
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROC_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

LOGGER = get_logger(name="project3", log_file=os.path.join(LOG_DIR, "project3.log"))

# Web sources (small, public)
CSV_URL = "https://people.sc.fsu.edu/~jburkardt/data/csv/airtravel.csv"
JSON_URL = "https://jsonplaceholder.typicode.com/posts"
TEXT_URL = "https://raw.githubusercontent.com/psf/requests/main/README.md"

# Output files
CSV_OUT = os.path.join(PROC_DIR, "airtravel_yearly_totals.csv")
XLSX_OUT = os.path.join(PROC_DIR, "summary.xlsx")
JSON_OUT = os.path.join(PROC_DIR, "posts_summary.json")
TEXT_OUT = os.path.join(PROC_DIR, "text_report.txt")


# -----------------------
# Helpers
# -----------------------
def fetch_to_bytes(url: str, timeout: int = 30) -> bytes:
    LOGGER.info(f"Fetching: {url}")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.content


def save_raw(content: bytes, filename: str) -> str:
    path = os.path.join(RAW_DIR, filename)
    with open(path, "wb") as f:
        f.write(content)
    LOGGER.info(f"Saved raw: {path}")
    return path


def read_csv_bytes(content: bytes) -> List[Dict[str, str]]:
    txt = content.decode("utf-8", errors="replace").splitlines()
    reader = csv.DictReader(txt)
    return list(reader)


def tokenize(text: str) -> List[str]:
    # words only, lowercase
    return re.findall(r"[a-zA-Z']+", text.lower())


# -----------------------
# Processing functions
# -----------------------
def process_airtravel(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, int | float]]:
    """
    Input: rows like [{'Month':'JAN','1958':'340','1959':'360','1960':'417'}, ...]
    Output: per-year totals and averages.
    """
    years = [y for y in rows[0].keys() if y.lower() != "month"]
    per_year_values: Dict[str, List[int]] = defaultdict(list)

    for row in rows:
        for y in years:
            val = row.get(y, "").strip()
            if val.isdigit():
                per_year_values[y].append(int(val))

    summary: Dict[str, Dict[str, int | float]] = {}
    for y, vals in per_year_values.items():
        summary[y] = {
            "months_counted": len(vals),
            "total_passengers": sum(vals),
            "avg_per_month": round(mean(vals), 2) if vals else 0.0,
        }
    LOGGER.info(f"Airtravel summary: {summary}")
    return summary


def process_posts(posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Count posts per userId and top words across all titles + bodies.
    """
    per_user = Counter([p.get("userId") for p in posts])
    all_text = " ".join([(p.get("title", "") + " " + p.get("body", "")) for p in posts])
    words = tokenize(all_text)
    # filter short words
    words = [w for w in words if len(w) > 3]
    top_words = Counter(words).most_common(15)

    summary = {
        "post_count": len(posts),
        "posts_per_user": dict(per_user),
        "top_words": [{"word": w, "count": c} for w, c in top_words],
    }
    LOGGER.info(f"Posts summary prepared with {summary['post_count']} posts.")
    return summary


def process_text_report(text: str) -> Dict[str, Any]:
    """
    Basic text metrics: char count, word count, top words.
    """
    chars = len(text)
    words = tokenize(text)
    word_count = len(words)
    top_words = Counter([w for w in words if len(w) > 4]).most_common(20)

    return {
        "characters": chars,
        "word_count": word_count,
        "top_words": top_words,
    }


# -----------------------
# Writers
# -----------------------
def write_csv_yearly_totals(summary: Dict[str, Dict[str, int | float]], path: str) -> None:
    fieldnames = ["year", "months_counted", "total_passengers", "avg_per_month"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for year, stats in summary.items():
            writer.writerow({"year": year, **stats})
    LOGGER.info(f"Wrote CSV: {path}")


def write_excel(summary: Dict[str, Dict[str, int | float]], path: str) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "AirTravel Summary"
    ws.append(["Year", "Months Counted", "Total Passengers", "Avg Per Month"])
    for year, stats in sorted(summary.items()):
        ws.append([year, stats["months_counted"], stats["total_passengers"], stats["avg_per_month"]])

    # A second sheet with a simple “ranking” by total passengers
    ws2 = wb.create_sheet("Totals Ranking")
    ws2.append(["Year", "Total Passengers"])
    for year, stats in sorted(summary.items(), key=lambda kv: kv[1]["total_passengers"], reverse=True):
        ws2.append([year, stats["total_passengers"]])

    wb.save(path)
    LOGGER.info(f"Wrote Excel: {path}")


def write_json(data: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    LOGGER.info(f"Wrote JSON: {path}")


def write_text_report(metrics: Dict[str, Any], path: str, source_name: str) -> None:
    lines = [
        f"Text Report for: {source_name}",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "-" * 60,
        f"Characters: {metrics['characters']}",
        f"Word Count: {metrics['word_count']}",
        "",
        "Top Words (min length 5):",
    ]
    for w, c in metrics["top_words"]:
        lines.append(f"  {w:<20} {c}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    LOGGER.info(f"Wrote Text: {path}")


# -----------------------
# main()
# -----------------------
def main() -> None:
    LOGGER.info("=== Project 3 start ===")

    # 1) Fetch and persist RAW files
    csv_bytes = fetch_to_bytes(CSV_URL)
    json_bytes = fetch_to_bytes(JSON_URL)
    text_bytes = fetch_to_bytes(TEXT_URL)

    save_raw(csv_bytes, "airtravel.csv")
    save_raw(json_bytes, "posts.json")
    save_raw(text_bytes, "requests_readme.txt")

    # 2) Process
    rows = read_csv_bytes(csv_bytes)
    air_summary = process_airtravel(rows)

    posts_data = json.loads(json_bytes.decode("utf-8", errors="replace"))
    posts_summary = process_posts(posts_data)

    text_str = text_bytes.decode("utf-8", errors="replace")
    text_metrics = process_text_report(text_str)

    # 3) Write processed outputs
    write_csv_yearly_totals(air_summary, CSV_OUT)
    write_excel(air_summary, XLSX_OUT)
    write_json(posts_summary, JSON_OUT)
    write_text_report(text_metrics, TEXT_OUT, source_name="psf/requests README")

    LOGGER.info("=== Project 3 complete ===")
    print("Done. See: data/raw, data/processed, and logs/project3.log")


if __name__ == "__main__":
    main()
