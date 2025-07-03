CREATE TABLE files (
    date text, 
    path text PRIMARY KEY,
    instrument text, 
    filter text, 
    type text, 
    object text, 
    width int, 
    height int, 
    jd real,
    ra real,
    dec real,
    id int, 
    exposure real,
    hash text UNIQUE,
    FOREIGN KEY(id) REFERENCES observations(rowid)
);

CREATE TABLE observations (
  date text,
  instrument text,
  filter text,
  type text,
  object text,
  width int,
  height int,
  exposure real,
  files int,
  UNIQUE(date, instrument, filter, object, type, width, height, exposure)
);

CREATE TABLE products (
  id int,
  datetime text,
  version text,
  files int,
  path text,
  status text,
  FOREIGN KEY(id) REFERENCES observations(id)
);