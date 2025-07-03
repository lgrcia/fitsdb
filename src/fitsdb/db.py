import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd
from datetime import datetime
from datetime import timedelta
import numpy as np

from fitsdb import core

# Convenience
# -----------
SQL_DAYS_BETWEEN = f"date(date, '-{core.NIGHT_HOURS} hours') >= date('{{date}}', '-{{past:.0f}} days') AND date(date, '-{core.NIGHT_HOURS} hours') <= date('{{date}}', '+{{future:.0f}} days')"
PWD = Path(__file__).parent


def in_value(value):
    return f"'{value}'" if isinstance(value, str) else value


def exposure_constraint(exposure=0, tolerance=1000000):
    return f"exposure between {exposure-tolerance} and {exposure+tolerance}"


def connect(file=None):
    if file is None:
        file = ":memory:"

    con = sqlite3.connect(file)
    cur = con.cursor()

    # check if file Table exists
    tables = list(cur.execute("SELECT name FROM sqlite_master WHERE type='table';"))
    if len(tables) == 0:
        db_creation = open(PWD / "sqlite.sql", "r").read()
        cur.executescript(db_creation)

    return con


def insert_file(con, data, update_obs=True):
    in_db = (
        len(
            con.execute(
                f"SELECT hash FROM files WHERE hash = ?", (data["hash"],)
            ).fetchall()
        )
        == 1
    )

    if not in_db:
        _data = data.copy()
        if _data["filter"]:
            _data["filter"] = data["filter"].replace("'", "p")

        obs = [
            "date",
            "instrument",
            "filter",
            "object",
            "type",
            "width",
            "height",
            "exposure",
            "ra",
            "dec",
            "jd",
            "hash",
            "path",
        ]

        _data["date"] = data["date"].strftime("%Y-%m-%d %H:%M:%S")

        con.execute(
            f"INSERT or IGNORE INTO files({','.join(obs)}) VALUES ({','.join(['?'] * len(obs))})",
            [_data[o] for o in obs],
        )

        # update observation
        if update_obs:
            # is file new
            _data["date"] = datetime.date(
                data["date"] - timedelta(hours=core.NIGHT_HOURS)
            )
            _data["date"] = _data["date"].strftime("%Y-%m-%d")
            unique_obs = (
                "date",
                "instrument",
                "filter",
                "object",
                "type",
                "width",
                "height",
                "exposure",
            )
            con.execute(
                f"INSERT OR IGNORE INTO observations({','.join(unique_obs)}, files) VALUES ({','.join(['?'] * len(unique_obs))}, 0)",
                [_data[o] for o in unique_obs],
            )
            query = " AND ".join(
                [f"{str(key)} = {in_value(_data[key])}" for key in unique_obs]
            )

            # number of files with this observation
            id = con.execute(
                f"SELECT rowid FROM observations where {query}"
            ).fetchall()[0][0]
            con.execute(f"UPDATE observations SET files = files + 1 WHERE rowid = {id}")
            # set id in files
            con.execute(
                f"UPDATE files SET id = {id} WHERE hash = {in_value(data['hash'])}"
            )
            return True
    else:
        return False


def observations(con, group_exposures=True, **kwargs):
    columns = {
        c[1]: "%"
        for c in con.execute("PRAGMA table_info(observations)").fetchall()[1:-3]
    }
    inputs = kwargs.copy()

    for key, value in inputs.items():
        inputs[key] = "%" if value is None else str(value).replace("*", "%")

    columns.update(inputs)

    where = " AND ".join(
        [f"{key} LIKE {in_value(value)}" for key, value in columns.items()]
    )
    query = f"select * from observations where {where}"

    if group_exposures:
        query = f"select *, SUM(files) from observations where {where} GROUP BY date, instrument, object, filter, type"
        df = pd.read_sql_query(query, con)
        df["files"]
        df = df.drop(columns=["files", "exposure"]).rename(
            columns={"SUM(files)": "files"}
        )
    else:
        query = f"select * from observations where {where}"
        df = pd.read_sql_query(query, con)

    return df


def calibration_files(
    con,
    im_type: str,
    date: datetime | str = None,
    exposure=None,
    filter=None,
    dimensions=None,
    instrument=None,
    past=1e3,
    future=0,
    tolerance=1e15,
    single_day=False,
):
    if date is None:
        date = datetime.now()
    if isinstance(date, datetime):
        date = date.strftime("%Y-%m-%d")

    sql_days = SQL_DAYS_BETWEEN.format(date=date, future=future, past=past)

    if exposure is None:
        exposure = 0
    sql_exposure = exposure_constraint(exposure=exposure, tolerance=tolerance)

    fields = {}
    if instrument is not None:
        fields["instrument"] = instrument
    if filter is not None:
        fields["filter"] = filter
    if dimensions is not None:
        fields["width"] = dimensions[0]
        fields["height"] = dimensions[1]

    query = " AND ".join([f"{key} = {in_value(fields[key])}" for key in fields])
    if im_type is not None:
        query += f" {'AND' if len(query) > 0 else ''} type = '{im_type}'"
    query = query.format(**fields)
    if len(query) > 0:
        query = f"AND {query}"

    single_day_sql = (
        f"AND date = (SELECT MAX(date(date, '-{core.NIGHT_HOURS} hours'))  FROM files WHERE {sql_days} {query})"
        if single_day
        else ""
    )

    obs_ids = pd.read_sql_query(
        f"""SELECT rowid FROM observations WHERE {sql_exposure} {query}
         {single_day_sql}
    """,
        con,
    ).values.flatten()

    _files = [
        pd.read_sql_query(
            f"select path from files where id={j} order by date", con
        ).values.flatten()
        for j in obs_ids
    ]
    if len(_files) > 0:
        _files = np.hstack(_files)

    return _files


def path_in_db(con, path):
    return (
        con.execute(f"SELECT * FROM files WHERE path='{path}'").fetchone() is not None
    )


def filter_query(table, instrument=None, date=None, filter_=None, object_=None):
    conditions = []
    if instrument:
        conditions.append(f"instrument REGEXP ?")
    if date:
        conditions.append(f"date REGEXP ?")
    if filter_:
        conditions.append(f"filter REGEXP ?")
    if object_:
        conditions.append(f"object REGEXP ?")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return f"SELECT * FROM {table} {where}"


def add_regexp_to_connection(con):
    import re

    def regexp(expr, item):
        if item is None:
            return False
        return re.search(expr, str(item), re.IGNORECASE) is not None

    con.create_function("REGEXP", 2, regexp)
