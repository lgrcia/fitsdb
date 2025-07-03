import re
from datetime import datetime
from functools import partial
from hashlib import sha1
from pathlib import Path

import yaml
from astropy import units as astropy_units
from astropy.coordinates import Angle
from astropy.io import fits
from astropy.io.fits import Header
from dateutil import parser

DEFAULT_INSTRUMENT = {
    "instrument_names": {"default": ["default"]},
    "definition": {
        "keyword_instrument": "TELESCOP",
        "keyword_object": "OBJECT",
        "keyword_image_type": "IMAGETYP",
        "keyword_light_images": "light",
        "keyword_dark_images": "dark",
        "keyword_flat_images": "flat",
        "keyword_bias_images": "bias",
        "keyword_observation_date": "DATE-OBS",
        "keyword_exposure_time": "EXPTIME",
        "keyword_filter": "FILTER",
        "keyword_ra": "RA",
        "keyword_dec": "DEC",
        "keyword_jd": "JD",
        "unit_ra": "deg",
        "unit_dec": "deg",
        "scale_jd": "utc",
    },
}
DEFAULT_CONFIG = {"default": DEFAULT_INSTRUMENT}
NIGHT_HOURS = 12.0


def fits_to_dict(fits_header: Header | Path, definition: dict) -> dict:
    # date
    date = fits_header.get(definition["keyword_observation_date"], None)
    date = parser.parse(date) if date else datetime(1800, 1, 1)

    # image type
    im_type = fits_header.get(definition["keyword_image_type"], None)

    type_dict = {
        definition["keyword_light_images"]: "light",
        definition["keyword_dark_images"]: "dark",
        definition["keyword_flat_images"]: "flat",
        definition["keyword_bias_images"]: "bias",
    }

    im_type_str = im_type or ""
    matched_type = ""
    for key, value in type_dict.items():
        if key and re.search(key, im_type_str, re.IGNORECASE):
            matched_type = value
            break
    im_type = matched_type

    def get_deg(key):
        value = fits_header.get(definition[f"keyword_{key}"], None)
        if value is None:
            return -1.0
        else:
            unit = astropy_units.__dict__[definition[f"unit_{key}"]]
            return Angle(value, unit).to(astropy_units.deg).value

    return dict(
        date=date,
        type=im_type,
        exposure=float(fits_header.get(definition["keyword_exposure_time"], -1.0)),
        object=fits_header.get(definition["keyword_object"], ""),
        filter=fits_header.get(definition["keyword_filter"], ""),
        width=fits_header.get("NAXIS1", 1),
        height=fits_header.get("NAXIS2", 1),
        jd=float(fits_header.get(definition["keyword_jd"], -1.0)),
        ra=float(get_deg("ra")),
        dec=float(get_deg("dec")),
    )


def instruments_name_keywords(config: dict) -> list[str]:
    return list(
        set(
            [
                value["definition"]["keyword_instrument"]
                for value in config.values()
                if "keyword_instrument" in value["definition"]
            ]
        )
    )


def instruments_definitions(config: dict) -> dict:
    default_definition = DEFAULT_INSTRUMENT["definition"]
    definitions = {}
    for _, value in config.items():
        for main_name, names in value["instrument_names"].items():
            for name in names:
                definitions[name.strip().lower()] = {
                    "name": main_name.strip().lower(),
                    **default_definition,
                    **value["definition"],
                }

    return definitions


def get_definition(
    fits_header: Header, keywords: list | tuple = (), definitions: dict = None
) -> dict:

    for keyword in keywords:
        if keyword in fits_header:
            instrument_name = fits_header[keyword].strip().lower()
            if instrument_name not in definitions:
                continue
            else:
                return definitions[instrument_name]

    return {**DEFAULT_INSTRUMENT["definition"], "name": "default"}


def unique_hash(string: str) -> str:
    return sha1(string.encode("utf-8"), usedforsecurity=False).hexdigest()


def get_data_from_header(
    fits_header: Header | dict, get_definition: callable, path: Path | str | None = None
) -> dict:
    definition = get_definition(fits_header)
    data = fits_to_dict(fits_header, definition)
    data["instrument"] = definition["name"]
    data["hash"] = unique_hash(
        f"{data['instrument']}-{data['filter']}-{data['date'].strftime('%Y-%m-%d %H:%M:%S')}"
    )
    data["path"] = str(path.absolute()) if isinstance(path, Path) else path
    return data


def get_data(file: Path | str, get_definition: callable) -> dict:
    header = fits.getheader(file)
    data = get_data_from_header(header, get_definition, path=file)
    return data


def file_to_data_function(config_file: str | Path = None) -> callable:
    config = yaml.safe_load(open(config_file)) if config_file else DEFAULT_CONFIG
    name_keywords = instruments_name_keywords(config)
    definitions = instruments_definitions(config)
    _get_definition = partial(
        get_definition, keywords=name_keywords, definitions=definitions
    )
    return partial(get_data, get_definition=_get_definition)
