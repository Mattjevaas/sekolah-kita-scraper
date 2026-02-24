# Sekolah Kita Scraper

This project scrapes school data from https://sekolah.data.kemendikdasmen.go.id using the public JSON API behind the "Sekolah Kita" website and exports it to CSV.

The scraper is implemented in Python and can be run directly, via helper launchers (`.sh` for Linux/macOS, `.bat` for Windows), or as a standalone executable (`.exe`). Both interactive (TUI) and non-interactive (CLI) modes are supported.

## Features

- **Official API**: Uses the official JSON API instead of HTML scraping.
- **Region Filtering**: Filter schools by Kabupaten/Kota (Regency/City).
- **Auto-Optimization**:
  - Automatically detects the total number of schools to set the optimal page size.
  - Page size defaults to fetching all data in one request for efficiency.
- **Data Collected**:
  - School Name
  - Address
  - City (Kabupaten/Kota)
  - Province
  - Phone (optional; via detail endpoint)
- **Smart Rate Limiting**:
  - Adds random delays (0.5s - 1.5s) between requests to mimic human behavior.
  - Option to **disable rate limiting** for faster scraping (use with caution).
  - Automatically retries failed requests with exponential backoff.
- **Concurrency**: Uses threaded workers with safe caps to avoid overloading the server.
- **Real-time Progress**: Shows progress bars for page collection and detail fetching.
- **Organized Output**: CSV filenames include the region name and timestamp (e.g., `sekolah_kita_kota_bandung_20240224_120000.csv`).

## Files

- `scrape_sekolah_kita.py`: Main Python scraper script.
- `build_exe.bat`: Windows script to compile the scraper into a standalone `.exe`.
- `run_sekolah_kita.bat`: Windows launcher script.
- `run_sekolah_kita.sh`: Linux/macOS launcher script.
- `requirements.txt`: Python dependencies (mainly for building the executable).

## Requirements

- **To Run Source Code**: Python 3.8+ installed.
- **To Run Executable**: No Python required (Windows only).

## Usage

### 1. Interactive Mode (TUI) - Recommended

This is the easiest way to use the scraper. It guides you through the settings step-by-step.

**How to start:**
- **Windows (.exe)**: Double-click `sekolah-kita-scraper.exe`.
- **Windows (Script)**: Double-click `run_sekolah_kita.bat` or run `python scrape_sekolah_kita.py`.
- **Linux/macOS**: Run `./run_sekolah_kita.sh`.

**Steps:**
1.  **Region Filter**: Type a city name (e.g., "Bandung"). The tool will show a numbered list of matching regions. Select one to filter, or skip to scrape everything.
2.  **Page Size**: Press Enter to accept the default. The tool automatically detects the total number of schools and sets this as the default to fetch everything in one go.
3.  **Max Pages**: Press Enter to fetch all pages.
4.  **Workers**: Press Enter to accept safe defaults for concurrent connections.
5.  **Phone Numbers**: Choose `y` to fetch phone numbers (slower, requires more requests) or `n` to skip.
6.  **Rate Limiting**: Choose `n` (default) to keep safety delays, or `y` to disable them for speed (higher risk of blocking).
7.  **Start**: Confirm to begin scraping.

The CSV file will be saved in the same directory as the script/executable.

### 2. Command Line Interface (CLI)

For advanced users or automation, you can pass arguments directly.

```bash
# Example: Scrape all schools in "Kota Bandung"
python scrape_sekolah_kita.py --kabupaten-kota "Kota Bandung"

# Example: Scrape everything, disable rate limits (FAST but risky)
python scrape_sekolah_kita.py --no-rate-limit

# Example: Custom page size and limit
python scrape_sekolah_kita.py --page-size 1000 --max-pages 5
```

**Available Arguments:**

- `--kabupaten-kota "NAME"`: Filter by exact Regency/City name.
- `--no-rate-limit`: Disable the 0.5s-1.5s delay between requests.
- `--page-size N`: Number of schools per page. Default `0` (auto-detects total and fetches all in one page).
- `--max-pages N`: Limit the number of pages to fetch.
- `--skip-phone`: Do not fetch phone numbers (faster).
- `--metadata-workers N`: Number of threads for listing pages.
- `--detail-workers N`: Number of threads for fetching details.
- `--output FILE`: Custom output filename.
- `--tui`: Force interactive mode.

## Building Standalone Executable

You can compile the script into a standalone executable that works on computers without Python installed.

**Note**: PyInstaller compiles for the operating system it is running on. To build a Windows `.exe`, you must run the build script on Windows. To build a macOS binary, you must run it on macOS.

### Windows

1.  Ensure Python is installed on your machine.
2.  Double-click `build_exe.bat`.
3.  The script will:
    - Create a temporary virtual environment.
    - Install necessary packages (`pyinstaller`).
    - Compile the code into a single `.exe` file.
4.  The output file `sekolah-kita-scraper.exe` will be located in the `dist` folder.

### macOS / Linux

1.  Open a terminal in the project directory.
2.  Make the build script executable:
    ```bash
    chmod +x build_executable.sh
    ```
3.  Run the build script:
    ```bash
    ./build_executable.sh
    ```
4.  The output binary `sekolah-kita-scraper` will be located in the `dist` folder.

**Portable Usage**:
The generated executable (`.exe` or binary) is portable. You can move it to any folder on a compatible machine. When run, it will automatically save CSV files in the **same directory** where the executable is located.

## Output Format

The output is a CSV file with the following columns:

```csv
school_name,address,city,province,phone
```

- **Filename Format**: `sekolah_kita_{sanitized_region_name}_{timestamp}.csv`
  - Example: `sekolah_kita_kota_bandung_20240224_164500.csv`
