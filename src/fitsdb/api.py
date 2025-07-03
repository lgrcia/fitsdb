import pandas as pd
from fastapi import FastAPI

from fitsdb import db

app = FastAPI()


@app.get("/")
def read_root():
    return {"Welcome to": "fitsdb API"}


@app.get("/observations/")
def read_observations(
    instrument: str | None = None,
    filter: str | None = None,
    date: str | None = None,
    object: str | None = None,
):
    con = db.connect("dev/db.sql")
    obs = db.observations(
        con, instrument=instrument, filter=filter, date=date, object=object
    )
    data = obs.to_dict(orient="records")
    con.close()
    return data


@app.get("/files/{index}")
def read_files(index: int):
    con = db.connect("dev/db.sql")
    files = pd.read_sql("SELECT * FROM files where id = ?", con, params=(index,))
    data = files.to_dict(orient="records")
    data = sorted(data, key=lambda x: x["date"])
    con.close()
    return data
