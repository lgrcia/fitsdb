from datetime import datetime, timedelta

import pandas as pd

from fitsdb import core, db

FAKE_CONFIG = {
    "test": {
        "instrument_names": {
            "main": ["name1", "name2", "name3"],
        },
        "definition": {
            "keyword_instrument": "INSTRUMENT",
        },
    }
}


def test_instruments_definitions():

    definitions = core.instruments_definitions(FAKE_CONFIG)

    for name in ["name1", "name2", "name3"]:
        assert name in definitions and definitions[name]["name"] == "main"


def test_get_definition():
    definitions = core.instruments_definitions(FAKE_CONFIG)
    fake_header = {"INSTRUMENT": "name1"}

    definition = core.get_definition(fake_header, ["INSTRUMENT"], definitions)

    assert definition["name"] == "main"


def test_no_header_no_definitions():
    assert (
        core.get_data_from_header({}, core.get_definition)["instrument"] == "(default)"
    )


def test_insert_file():
    con = db.connect()
    header = dict(date=datetime.now())
    data = core.get_data_from_header(header, core.get_definition)
    db.insert_file(con, data)


def test_midnight_overlap():

    science = [
        {
            "DATE-OBS": (datetime(2020, 2, 1, 22) + timedelta(hours=i)).isoformat(),
            "IMAGETYP": "light",
        }
        for i in range(10)
    ]

    con = db.connect()

    for header in science:
        data = core.get_data_from_header(header, core.get_definition)
        db.insert_file(con, data)

    con.commit()
    assert len(db.observations(con).values) == 1
    assert db.observations(con).values[0][0] == "2020-02-01"


def test_calibration_files_flats():

    flats = [
        {
            "DATE-OBS": datetime(2020, 4, 1 if i < 5 else 3, 1, i + 1).isoformat(),
            "IMAGETYP": "flat",
            "OBJECT": "star1",
            "FILTER": "a" if i < 5 else "b",
            "PATH": f"flat_{i}_{'a' if i < 5 else 'b'}.fits",
        }
        for i in range(10)
    ]

    con = db.connect()

    for header in flats:
        data = core.get_data_from_header(header, core.get_definition, header["PATH"])
        db.insert_file(con, data)

    con.commit()

    # all flats any day
    files = db.calibration_files(con, "flat", "2020-04-05", single_day=False)
    assert len(files) == 10 and all(["flat" in f for f in files])
    # all flats single day
    files = db.calibration_files(con, "flat", "2020-04-05", single_day=True)
    assert len(files) == 5 and all(["flat" in f for f in files])
    # specific filter flats any day
    files = db.calibration_files(
        con, "flat", "2020-04-01", filter="a", single_day=False
    )
    assert len(files) == 5 and all([f.strip(".fits")[-1] == "a" in f for f in files])


def test_calibration_files_darks():
    darks = [
        {
            "DATE-OBS": datetime(2020, 4, 1 if i < 10 else 3, 1, i).isoformat(),
            "IMAGETYP": "dark",
            "EXPTIME": 10 if i < 10 else 20,
            "PATH": f"dark_{i}_{10 if i < 10 else 20}.fits",
        }
        for i in range(20)
    ]

    con = db.connect()

    for header in darks:
        data = core.get_data_from_header(header, core.get_definition, header["PATH"])
        db.insert_file(con, data)

    con.commit()

    # all darks any exposure
    files = db.calibration_files(con, "dark")
    assert len(files) == 20 and all(["dark" in f for f in files])

    # all darks exposure 10
    files = db.calibration_files(con, "dark", exposure=10.0, tolerance=0)
    assert len(files) == 10 and all(
        [f.strip(".fits")[-2::] == "10" in f for f in files]
    )

    # all darks exposure 20
    files = db.calibration_files(con, "dark", exposure=20.0, tolerance=0)
    assert len(files) == 10 and all(
        [f.strip(".fits")[-2::] == "20" in f for f in files]
    )


def test_add_duplicate():
    con = db.connect()
    header = {"DATE-OBS": datetime.now().isoformat()}
    data = core.get_data_from_header(header, core.get_definition)
    db.insert_file(con, data, update_obs=False)
    db.insert_file(con, data, update_obs=False)
    db.insert_file(con, data, update_obs=False)

    header = {"DATE-OBS": (datetime.now() + timedelta(days=1)).isoformat()}
    data = core.get_data_from_header(header, core.get_definition)
    db.insert_file(con, data, update_obs=False)
    con.commit()

    # Try to insert the same file again
    assert not db.insert_file(con, data, update_obs=False)

    # Check that the file was not added again
    assert con.execute("SELECT COUNT(*) FROM files").fetchall()[0][0] == 2


def test_obs_id():
    headers = [{"TELESCOP": "c"}, {"TELESCOP": "a"}, {"TELESCOP": "b"}]
    con = db.connect()

    for header in headers:
        data = core.get_data_from_header(header, core.get_definition)
        db.insert_file(con, data)

    con.commit()

    files_inst_id = pd.read_sql("SELECT instrument, id FROM files", con).to_dict(
        orient="records"
    )
    obs = db.observations(con)

    for file in files_inst_id:
        assert obs.loc[file["id"]].instrument == file["instrument"]
