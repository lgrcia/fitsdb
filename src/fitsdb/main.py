import argparse
import os
from multiprocessing import Pool
from pathlib import Path

from tqdm import tqdm

from fitsdb import core, db


def get_files(folder: str | Path, name: str) -> list[Path]:
    return Path(folder).rglob(name)


def get_query_params(instrument=None, date=None, filter_=None, object_=None):
    params = []
    if instrument:
        params.append(instrument)
    if date:
        params.append(date)
    if filter_:
        params.append(filter_)
    if object_:
        params.append(object_)
    return params


def index_folder(
    folder: str, instruments_file: str, db_file: str, p=None, duplicate=False
):
    if p is None:
        p = os.cpu_count() or 1

    folder_path = Path(folder)
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder '{folder}' does not exist.")
    if instruments_file:
        instruments_path = Path(instruments_file)
        if not instruments_path.exists():
            raise FileNotFoundError(
                f"Instruments file '{instruments_file}' does not exist."
            )

    files = list(get_files(folder, "*.f*t*"))
    _get_data = core.file_to_data_function(instruments_file)
    con = db.connect(db_file)
    added = 0

    if duplicate:
        new_files = files
    else:
        print("Checking new files")
        new_files = [file for file in files if not db.path_in_db(con, file)]

    with Pool(processes=p) as pool:
        for data in tqdm(
            pool.imap(_get_data, new_files),
            total=len(new_files),
        ):
            is_inserted = db.insert_file(con, data)
            if is_inserted:
                added += 1

    con.commit()
    con.close()
    if db_file is None:
        print(f"Database created at: {db_file}")

    print(f"{added} files added to the database.")


def show_table(table, db_path, instrument, date, filter_, object_):
    import pandas as pd

    con = db.connect(db_path)
    db.add_regexp_to_connection(con)
    query = db.filter_query(table, instrument, date, filter_, object_)
    params = get_query_params(instrument, date, filter_, object_)
    df = pd.read_sql_query(query, con, params=params)
    print(df)
    con.close()


def main():
    parser = argparse.ArgumentParser(description="FITS parser CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # index command
    index_parser = subparsers.add_parser(
        "index", help="Index FITS files into a database."
    )
    index_parser.add_argument("folder", type=str, help="Folder containing FITS files.")
    index_parser.add_argument(
        "-i",
        "--instruments",
        type=str,
        default=None,
        help="Path to instruments config yaml file.",
    )
    index_parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Path to output database file (default: db.sqlite in folder)",
    )
    index_parser.add_argument(
        "-p",
        "--processes",
        type=int,
        default=None,
        help="Number of processes to use for indexing (default: number of CPU cores).",
    )
    index_parser.add_argument(
        "--duplicate",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Reset the database before indexing (default: False).",
    )

    # show observations
    show_obs_parser = subparsers.add_parser(
        "observations", help="Show observations from the database."
    )
    show_obs_parser.add_argument("db", type=str, help="Path to the database file.")
    show_obs_parser.add_argument("-i", "--instrument", type=str, default=None)
    show_obs_parser.add_argument("-d", "--date", type=str, default=None)
    show_obs_parser.add_argument(
        "-f", "--filter", dest="filter_", type=str, default=None
    )
    show_obs_parser.add_argument(
        "-o", "--object", dest="object_", type=str, default=None
    )
    show_obs_parser.add_argument("--exposure", action=argparse.BooleanOptionalAction)
    show_obs_parser.set_defaults(exposure=False)

    args = parser.parse_args()

    if args.command == "index":
        db_path = args.output if args.output else str(Path(args.folder) / "db.sqlite")
        index_folder(
            args.folder, args.instruments, db_path, args.processes, args.duplicate
        )

    elif args.command == "observations" or args.command == "files":
        con = db.connect(args.db)

        if args.command == "observations":
            obs_df = db.observations(
                con,
                filter=args.filter_,
                instrument=args.instrument,
                date=args.date,
                object=args.object_,
                group_exposures=not args.exposure,
            )
            print(obs_df)

        con.close()


if __name__ == "__main__":
    main()
