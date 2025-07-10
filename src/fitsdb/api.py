import os

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fitsdb import db

app = FastAPI()

DB_PATH = os.environ.get("FITSDB", None)
LIMIT = os.environ.get("LIMIT", "30")

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/observations/")
def read_observations(
    instrument: str | None = None,
    filter: str | None = None,
    date: str | None = None,
    object: str | None = None,
    type: str | None = None,
):
    con = db.connect(DB_PATH)
    obs = db.observations(
        con,
        instrument=instrument,
        filter=filter,
        date=date,
        object=object,
        type=type,
        sort_id=False,
        limit=int(LIMIT),
    )
    data = obs.to_dict(orient="records")
    con.close()
    return data


@app.get("/files/{index}")
def read_files(index: int):
    con = db.connect(DB_PATH)
    files = pd.read_sql("SELECT * FROM files where id = ?", con, params=(index,))
    data = files.to_dict(orient="records")
    data = sorted(data, key=lambda x: x["date"])
    con.close()
    return data
