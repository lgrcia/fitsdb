# fitsdb

`fitsdb` is a command-line interface and Python package for indexing FITS files into an SQL database. It extracts metadata from FITS headers and organizes it for easy querying.

For example, the command
```bash
fitsdb index fits_folder
```
makes a SQLite database with metadata from FITS files and their corresponding observations. A python package then provides convenience functions. For example

```python
from fitsdb import db

con = db.connect("db.sqlite")

db.observations_files(con, "dark", "2020-04-01", filter="a", exposure=20.0, tolerance=5, past=3)
```
returns a list of dark calibration files 
- with exposure times of 20 seconds +/- 5 seconds.
- taken at most 3 days prior to the science frames on a specific date.


## Installation

`fitsdb` is available on PyPI. It is recommended to install it in a fresh Python virtual environment. You can use [uv](https://github.com/astral-sh/uv) for fast and reproducible environment management, or use `venv`/`pip` as you prefer.

### Using PyPI (recommended)
```bash
uv venv
source .venv/bin/activate
uv pip install fitsdb
```

### From source
```bash
git clone https://github.com/lgrcia/fitsdb.git
cd fitsdb
uv venv
source .venv/bin/activate
uv sync
uv pip install -e .
```

This will install the `fitsdb` CLI and all dependencies.

## Instrument YAML Configuration

The instrument configuration YAML file defines how FITS header keywords are mapped to database fields and how instrument names are recognized. This file is required for the `index` command and is specified using the `-i` or `--instruments` option in the CLI. The CLI uses this configuration to correctly interpret FITS headers for different instruments and to standardize the metadata stored in the database.

### Example Structure
```yaml
default:
    instrument_names:
        default: ["default",]
    definition:
        keyword_instrument: "TELESCOP"
        keyword_object: "OBJECT"
        keyword_image_type: "IMAGETYP"
        keyword_light_images: "light"
        keyword_dark_images: "dark"
        keyword_flat_images: "flat"
        keyword_bias_images: "bias"
        keyword_observation_date: "DATE-OBS"
        keyword_exposure_time: "EXPTIME"
        keyword_filter: "FILTER"
        keyword_ra: "RA"
        keyword_dec: "DEC"
        keyword_jd: "JD"
        unit_ra : "deg"
        unit_dec : "deg"
        scale_jd : "utc"

speculoos:
    instrument_names:
        # these are all the possible names under the 'keyword_image_type' that
        # correspond to the Callisto instrument
        Callisto: ["speculoos-Callisto", "callisto"]
        Europa: ["speculoos-Europa",]
        Io: ["speculoos-Io",]
        Ganymede: ["speculoos-Ganymede",]
        Artemis: ["speculoos-Artemis", "artemis", "sno"]
    definition:
        keyword_light_images: "Light Frame"

Other:
    instrument_names:
        Trius-SX694: ["Trius-SX694",]
    definition:
        keyword_instrument: "INSTRUME"
        keyword_light_images: "Light_Frame"
```

### Sections
- **instrument_names**: Maps instrument aliases to canonical names.
- **definition**: Maps FITS header keywords to logical fields used by the parser.

You can add more sections for different instruments as needed. The `default` section is used as a fallback.

## CLI Usage

### Index FITS Files
To index FITS files into a database, use:
```bash
fitsdb index <folder> -i instruments.yaml [-o output.sqlite]
```

#### Arguments:
- `<folder>`: Path to the folder containing FITS files.
- `-i`, `--instruments`: Path to the `instruments.yaml` file defining instrument configurations. If not provided, a built-in default is used.
- `-o`, `--output`: (Optional) Path to the output database file. Defaults to `db.sqlite` in the folder.
- `-p`, `--processes`: (Optional) Number of processes to use for indexing (default: number of CPU cores).

### Show Observations
Show observations from the database (supports regex, case-insensitive):
```bash
fitsdb observations <db.sqlite> [-i INSTRUMENT] [-d DATE] [-f FILTER] [-o OBJECT] [--exposure/--no-exposure]
```

#### Arguments:
- `<db.sqlite>`: Path to the SQLite database file.
- `-i`, `--instrument`: Filter by instrument name (regex).
- `-d`, `--date`: Filter by observation date (YYYY-MM-DD).
- `-f`, `--filter`: Filter by filter name (regex).
- `-o`, `--object`: Filter by object name (regex).
- `--exposure`: Show exposure times.
- `--no-exposure`: Do not show exposure times (default).

All regex filters are case-insensitive.

## Development
### Requirements
- Python 3.11+
- Dependencies listed in `pyproject.toml`.

### Testing
Run unit tests using:
```bash
pytest
```

## License
MIT License

