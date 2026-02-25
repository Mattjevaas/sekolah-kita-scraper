import argparse
import csv
import json
import math
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import urllib.error
import urllib.request


API_BASE = "https://sekolah.data.kemendikdasmen.go.id"
CARI_ENDPOINT = f"{API_BASE}/v1/sekolah-service/sekolah/cari-sekolah"
DETAIL_ENDPOINT = f"{API_BASE}/v1/sekolah-service/sekolah/full-detail"
SAFE_METADATA_WORKERS_MAX = 2
SAFE_DETAIL_WORKERS_MAX = 4

# Rate limiting constants (seconds)
MIN_DELAY = 0.5
MAX_DELAY = 1.5
DISABLE_RATE_LIMIT = False
ALLOWED_BENTUK_PENDIDIKAN = "KB,MAK,PAUDQ,RA,SPKTK,SPKPG,SPS,TK,TKLB,TPA"

# Global lock for thread-safe printing
print_lock = threading.Lock()


import re

def build_timestamped_output(base_dir: Path, kabupaten_kota: str = "") -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if kabupaten_kota:
        # Sanitize: lowercase, replace non-alphanumeric with underscore
        safe_name = re.sub(r"[^a-z0-9]+", "_", kabupaten_kota.lower()).strip("_")
        filename = f"sekolah_kita_{safe_name}_{ts}.csv"
    else:
        filename = f"sekolah_kita_{ts}.csv"
    return base_dir / filename


def prompt_int(prompt: str, default: int, min_value: int = 1, max_value: Optional[int] = None) -> int:
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            print(f"Please enter an integer value.")
            continue
        if value < min_value:
            print(f"Please enter a value >= {min_value}.")
            continue
        if max_value is not None and value > max_value:
            print(f"Please enter a value <= {max_value}.")
            continue
        return value


def prompt_optional_int(prompt: str, default: Optional[int]) -> Optional[int]:
    label = f"[{default}]" if default is not None else "[blank for all]"
    while True:
        raw = input(f"{prompt} {label}: ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("Please enter an integer or leave blank.")
            continue
        if value <= 0:
            print("Please enter a value > 0 or leave blank.")
            continue
        return value


def prompt_bool(prompt: str, default: bool) -> bool:
    default_str = "y" if default else "n"
    while True:
        raw = input(f"{prompt} [y/n] (default {default_str}): ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("Please answer with y or n.")


def prompt_str(prompt: str, default: str = "") -> str:
    default_label = f" [{default}]" if default else ""
    raw = input(f"{prompt}{default_label}: ").strip()
    if not raw:
        return default
    return raw


def post_json(url: str, payload: Dict[str, Any], retries: int = 3, backoff: float = 2.0) -> Dict[str, Any]:
    # Rate limit delay
    if not DISABLE_RATE_LIMIT:
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    attempt = 0
    last_err: Optional[BaseException] = None
    while attempt < retries:
        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("Accept", "application/json")
            # User-Agent to avoid blocking
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
            return json.loads(body)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_err = exc
            attempt += 1
            if attempt >= retries:
                break
            # Exponential backoff with jitter
            wait_time = (backoff * attempt) + random.uniform(0.5, 1.5)
            with print_lock:
                print(f"[Warn] POST {url} failed (attempt {attempt}/{retries}): {exc}. Retrying in {wait_time:.2f}s...", file=sys.stderr)
            time.sleep(wait_time)
    if last_err:
        raise last_err
    raise RuntimeError("Unknown error in post_json")


def get_json(url: str, retries: int = 3, backoff: float = 2.0) -> Dict[str, Any]:
    # Rate limit delay
    if not DISABLE_RATE_LIMIT:
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    attempt = 0
    last_err: Optional[BaseException] = None
    while attempt < retries:
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("Accept", "application/json")
            # User-Agent to avoid blocking
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
            return json.loads(body)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_err = exc
            attempt += 1
            if attempt >= retries:
                break
            # Exponential backoff with jitter
            wait_time = (backoff * attempt) + random.uniform(0.5, 1.5)
            with print_lock:
                print(f"[Warn] GET {url} failed (attempt {attempt}/{retries}): {exc}. Retrying in {wait_time:.2f}s...", file=sys.stderr)
            time.sleep(wait_time)
    if last_err:
        raise last_err
    raise RuntimeError("Unknown error in get_json")


def fetch_page(page: int, size: int, kabupaten_kota: str = "") -> Dict[str, Any]:
    payload = {
        "page": page,
        "size": size,
        "keyword": "",
        "kabupaten_kota": kabupaten_kota,
        "bentuk_pendidikan": ALLOWED_BENTUK_PENDIDIKAN,
        "status_sekolah": "",
    }
    return post_json(CARI_ENDPOINT, payload)


def collect_pages(
    page_size: int,
    max_pages: Optional[int],
    workers: int,
    kabupaten_kota: str = "",
) -> Tuple[List[Dict[str, Any]], int]:
    # If page_size is <= 0, fetch total count first and use that as page_size
    if page_size <= 0:
        print("Fetching metadata to determine total count...", file=sys.stderr)
        try:
            meta = fetch_page(0, 1, kabupaten_kota)
            total_found = int(meta.get("total", 0))
            if total_found > 0:
                page_size = total_found
                print(f"Auto-detected total records: {total_found}. Setting page size to {total_found}.", file=sys.stderr)
            else:
                # Fallback if total is 0 or missing
                page_size = 1000
                print("Could not determine total. Defaulting page size to 1000.", file=sys.stderr)
        except Exception as exc:
            print(f"Error fetching metadata: {exc}. Defaulting page size to 1000.", file=sys.stderr)
            page_size = 1000

    # Page index starts at 0 for this API
    first = fetch_page(0, page_size, kabupaten_kota)
    total = int(first.get("total", len(first.get("data", []) or [])))
    if total <= 0:
        return [], 0
    total_pages = int(math.ceil(total / float(page_size)))
    if max_pages is not None and max_pages > 0:
        total_pages = min(total_pages, max_pages)
    pages_data: Dict[int, List[Dict[str, Any]]] = {}
    pages_data[0] = list(first.get("data") or [])
    failed_pages: List[int] = []
    
    print(f"Total pages to fetch: {total_pages}", file=sys.stderr)
    completed_count = 1
    
    if total_pages > 1:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(fetch_page, page, page_size, kabupaten_kota): page
                for page in range(1, total_pages)
            }
            for future in as_completed(futures):
                completed_count += 1
                page = futures[future]
                try:
                    result = future.result()
                    items = list(result.get("data") or [])
                    pages_data[page] = items
                except BaseException as exc:
                    with print_lock:
                        print(f"\nFailed to fetch page {page}: {exc}", file=sys.stderr)
                    failed_pages.append(page)
                
                # Progress indicator
                if completed_count % 5 == 0 or completed_count == total_pages:
                    with print_lock:
                        print(f"Pages processed: {completed_count}/{total_pages} ({completed_count/total_pages*100:.1f}%)", end="\r", file=sys.stderr)
    
    # Clear progress line
    print(file=sys.stderr)
    
    if failed_pages:
        for page in sorted(set(failed_pages)):
            attempt = 0
            while attempt < 3:
                attempt += 1
                try:
                    result = fetch_page(page, page_size, kabupaten_kota)
                    items = list(result.get("data") or [])
                    pages_data[page] = items
                    break
                except BaseException as exc:
                    if attempt >= 3:
                        print(f"Permanent failure for page {page}: {exc}", file=sys.stderr)
                    else:
                        time.sleep(attempt)
    all_items: List[Dict[str, Any]] = []
    for page in sorted(pages_data.keys()):
        all_items.extend(pages_data[page])
    return all_items, total


def fetch_phone(sekolah_id: str) -> Optional[str]:
    url = f"{DETAIL_ENDPOINT}/{sekolah_id}"
    try:
        data = get_json(url)
    except BaseException as exc:
        print(f"Failed to fetch detail for {sekolah_id}: {exc}", file=sys.stderr)
        return None
    detail = data.get("data") or {}
    sekolah_list = detail.get("sekolah") if isinstance(detail, dict) else None
    if not sekolah_list or not isinstance(sekolah_list, list):
        return None
    first = sekolah_list[0] or {}
    phone = first.get("nomor_telepon")
    if phone is None:
        return None
    text = str(phone).strip()
    return text or None


def enrich_with_phones(
    items: Iterable[Dict[str, Any]],
    workers: int,
) -> Dict[str, Optional[str]]:
    ids = [row.get("sekolah_id") for row in items if row.get("sekolah_id")]
    phones: Dict[str, Optional[str]] = {}
    if not ids:
        return phones
        
    total_items = len(ids)
    processed_count = 0
    print(f"Fetching details for {total_items} schools...", file=sys.stderr)
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_phone, sekolah_id): sekolah_id for sekolah_id in ids}
        for future in as_completed(futures):
            processed_count += 1
            sekolah_id = futures[future]
            try:
                phone = future.result()
            except BaseException as exc:
                with print_lock:
                    print(f"\nFailed to get phone for {sekolah_id}: {exc}", file=sys.stderr)
                phone = None
            phones[sekolah_id] = phone
            
            # Progress indicator
            if processed_count % 10 == 0 or processed_count == total_items:
                with print_lock:
                    print(f"Details processed: {processed_count}/{total_items} ({processed_count/total_items*100:.1f}%)", end="\r", file=sys.stderr)
    
    # Clear progress line
    print(file=sys.stderr)
    
    return phones


def write_csv(
    rows: Iterable[Dict[str, Any]],
    phones: Dict[str, Optional[str]],
    output_path: str,
) -> None:
    fieldnames = ["school_name", "address", "city", "province", "phone"]
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            sekolah_id = row.get("sekolah_id")
            writer.writerow(
                {
                    "school_name": row.get("nama") or "",
                    "address": row.get("alamat_jalan") or "",
                    "city": row.get("kabupaten") or "",
                    "province": row.get("provinsi") or "",
                    "phone": phones.get(sekolah_id) or "",
                }
            )


def run_scrape(
    output_path: str,
    page_size: int,
    max_pages: Optional[int],
    metadata_workers: int,
    detail_workers: int,
    skip_phone: bool,
    kabupaten_kota: str = "",
) -> None:
    try:
        items, total = collect_pages(
            page_size=page_size,
            max_pages=max_pages,
            workers=max(1, metadata_workers),
            kabupaten_kota=kabupaten_kota,
        )
    except BaseException as exc:
        print(f"Failed to list schools: {exc}", file=sys.stderr)
        sys.exit(1)
    if not items:
        print("No school data returned from API.", file=sys.stderr)
        sys.exit(1)
    print(f"Fetched metadata for {len(items)} schools (reported total {total}).", file=sys.stderr)
    phones: Dict[str, Optional[str]] = {}
    if not skip_phone:
        try:
            phones = enrich_with_phones(items, workers=max(1, detail_workers))
        except BaseException as exc:
            print(f"Failed while fetching phone numbers: {exc}", file=sys.stderr)
    try:
        write_csv(items, phones, output_path)
    except BaseException as exc:
        print(f"Failed to write CSV: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Wrote CSV to {output_path}", file=sys.stderr)


def get_kabupaten_suggestions(keyword: str) -> List[str]:
    print(f"Searching for regions matching '{keyword}'...", file=sys.stderr)
    try:
        # We need to construct the payload manually because fetch_page doesn't support keyword
        payload = {
            "page": 1,
            "size": 100,
            "keyword": keyword,
            "kabupaten_kota": "",
            "bentuk_pendidikan": "",
            "status_sekolah": "",
        }
        result = post_json(CARI_ENDPOINT, payload)
        items = result.get("data") or []
        
        # Extract unique kabupaten
        unique_kab = set()
        for item in items:
            kab = item.get("kabupaten")
            if kab:
                unique_kab.add(kab)
        
        return sorted(list(unique_kab))
    except Exception as exc:
        print(f"Failed to fetch suggestions: {exc}", file=sys.stderr)
        return []


def select_kabupaten_kota() -> str:
    print("--- Region Filter ---")
    while True:
        keyword = prompt_str("Enter Kabupaten/Kota name to search (leave blank to skip)")
        if not keyword:
            return ""
        
        suggestions = get_kabupaten_suggestions(keyword)
        if not suggestions:
            print("No regions found matching that keyword. Try again.")
            continue
            
        print(f"\nFound {len(suggestions)} regions:")
        for idx, name in enumerate(suggestions, 1):
            print(f"  {idx}. {name}")
        print(f"  0. Search again")
        print(f"  B. Back / Skip")
        
        choice = prompt_str("Select a number")
        if choice.lower() in ("b", "back", "skip"):
            return ""
        
        try:
            idx = int(choice)
            if idx == 0:
                continue
            if 1 <= idx <= len(suggestions):
                selected = suggestions[idx - 1]
                print(f"Selected: {selected}")
                return selected
            print("Invalid number.")
        except ValueError:
            print("Invalid input.")


def run_tui(args: argparse.Namespace) -> None:
    global DISABLE_RATE_LIMIT
    
    if getattr(sys, 'frozen', False):
        # Running as compiled executable: save in the same directory as the .exe
        script_dir = Path(sys.executable).resolve().parent
    else:
        # Running as script: save in the script's directory
        script_dir = Path(__file__).resolve().parent

    print("Sekolah Kita scraper (interactive mode)")
    print()
    
    kabupaten_kota = select_kabupaten_kota()
    print()
    
    # Try to detect total records to offer as default page size
    default_page_size = args.page_size if args.page_size > 0 else 1000
    if args.page_size <= 0:
        try:
            print("Checking total records...", file=sys.stderr)
            meta = fetch_page(0, 1, kabupaten_kota=kabupaten_kota)
            total_found = int(meta.get("total", 0))
            if total_found > 0:
                default_page_size = total_found
        except Exception as exc:
            print(f"Failed to check total records: {exc}", file=sys.stderr)

    page_size = prompt_int("Page size (schools per API page)", default_page_size)
    max_pages = prompt_optional_int("Max pages to fetch", args.max_pages)
    metadata_workers = prompt_int(
        "Metadata workers (concurrent page requests)",
        args.metadata_workers,
        min_value=1,
        max_value=SAFE_METADATA_WORKERS_MAX,
    )
    detail_workers = prompt_int(
        "Detail workers (concurrent phone requests)",
        args.detail_workers,
        min_value=1,
        max_value=SAFE_DETAIL_WORKERS_MAX,
    )
    fetch_phones = prompt_bool("Fetch phone numbers from detail endpoint?", not args.skip_phone)
    DISABLE_RATE_LIMIT = prompt_bool("Disable rate limiting? (Faster but higher risk)", DISABLE_RATE_LIMIT)
    output_path = build_timestamped_output(script_dir, kabupaten_kota=kabupaten_kota)
    print()
    print(f"Output CSV will be created at:")
    print(f"  {output_path}")
    print()
    if not prompt_bool("Start scraping now?", True):
        print("Cancelled.")
        return
    run_scrape(
        output_path=str(output_path),
        page_size=page_size,
        max_pages=max_pages,
        metadata_workers=metadata_workers,
        detail_workers=detail_workers,
        skip_phone=not fetch_phones,
        kabupaten_kota=kabupaten_kota,
    )
    input("\nPress Enter to exit...")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape school data from sekolah.data.kemendikdasmen.go.id to CSV."
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output CSV file path. If omitted, a timestamped name is used.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=0,
        help="Number of schools per API page. Default (0) fetches all reported data in one page.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional maximum number of pages to fetch.",
    )
    parser.add_argument(
        "--metadata-workers",
        type=int,
        default=SAFE_METADATA_WORKERS_MAX,
        help="Number of concurrent workers for listing pages (capped to a safe maximum).",
    )
    parser.add_argument(
        "--detail-workers",
        type=int,
        default=SAFE_DETAIL_WORKERS_MAX,
        help="Number of concurrent workers for detail requests (capped to a safe maximum).",
    )
    parser.add_argument(
        "--skip-phone",
        action="store_true",
        help="Skip fetching phone numbers (faster, fewer requests).",
    )
    parser.add_argument(
        "--kabupaten-kota",
        type=str,
        default="",
        help="Filter by Kabupaten/Kota name (exact match).",
    )
    parser.add_argument(
        "--no-rate-limit",
        action="store_true",
        help="Disable rate limiting (faster, but higher risk of blocking).",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Run in interactive TUI mode.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    global DISABLE_RATE_LIMIT
    
    # If no arguments provided (running from double-click or simple command), default to TUI
    if argv is None and len(sys.argv) == 1:
        argv = ["--tui"]
        
    args = parse_args(argv)
    if args.no_rate_limit:
        DISABLE_RATE_LIMIT = True
        
    if args.tui:
        run_tui(args)
        return
    metadata_workers = max(1, min(args.metadata_workers, SAFE_METADATA_WORKERS_MAX))
    detail_workers = max(1, min(args.detail_workers, SAFE_DETAIL_WORKERS_MAX))
    if args.output:
        output_path = args.output
    else:
        output_path = str(build_timestamped_output(Path.cwd(), kabupaten_kota=args.kabupaten_kota))
    run_scrape(
        output_path=output_path,
        page_size=args.page_size,
        max_pages=args.max_pages,
        metadata_workers=metadata_workers,
        detail_workers=detail_workers,
        skip_phone=args.skip_phone,
        kabupaten_kota=args.kabupaten_kota,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        # Keep window open if running as executable
        if getattr(sys, 'frozen', False):
            input("Press Enter to exit...")
        sys.exit(1)
