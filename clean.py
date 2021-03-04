import os
import sys
import numpy as np
import pandas as pd


# My modules
import wrangler




#def classify_document(fpath):
#    """ Find the year range the file belongs to.
#    
#    Returns:
#        str: The year range. It is one of "2015 - 2017", "2018", "2019"
#            or "2020"
#    """


def get_header_information():
    """ Get the headers for all downloaded files.
    """
    f_info = []
    heads = []
    for s in os.listdir("./raw"):
        print(s)
        if s[0] == "s":
            for i in os.listdir("./raw/" + s):
                print(i)
                for f in os.listdir("./raw/" + s + "/" + i):
                    f_info.append(
                            {
                                "id_government": s,
                                "id_pnt_institution": i,
                                "fname": f
                                }
                            )
                    
                    df = pd.read_excel("./raw/" + s + "/" + i + "/" + f)

                    # Get the header row and drop rows before it.
                    # This assumes:
                    #   1. The header row is the first row without missing values.
                    #   2. The header row has no missing values...
                    header_i = np.where(~df.isna().any(axis = 1))[0][0]
                    head = df.iloc[header_i, : ]
                    heads.append(head.values)

    n_cols = np.array([len(a) for a in heads])

    # Cast this as an np.ndarray
    heads_a = np.empty((len(heads), np.max(n_cols)))
    heads_a[: , : ] = np.nan
    heads_a = heads_a.astype(object)

    for i in range(len(heads)):
        cols = len(heads[i])
        heads_a[i, : cols] = heads[i]

    header_info = pd.DataFrame(f_info)
    header_info = pd.concat((header_info, pd.DataFrame(heads_a)), axis = 1)

    header_info.to_csv("./processed/header_info.csv", index = False)


def clean_header(series):
    for sub in [
            (".", ""),
            ("-", " "),
            ("_", " "),
            ("*", ""),
            ("á", "a"),
            ("é", "e"),
            ("í", "i"),
            ("ó", "o"),
            ("ú", "u"),
            ("Á", "a"),
            ("É", "e"),
            ("Í", "i"),
            ("Ó", "o"),
            ("Ú", "u"),
            ("Ñ", "n"),
            ("ñ", "n"),
            ("\xc3\x91", "n"),
            ("ü", "u"),
            ("Ü", "u"),
            ("\xc3\x9c", "u"),
            ("\xa0", " "),
            ("<", "")
            ]:
        series = series.str.replace(sub[0], sub[1])

    # Remove extra whitespace
    series = series.str.replace('\s+', ' ', regex = True)

    # Lower case, strip
    series = series.str.lower().str.strip()
    return series


def get_unique_headers():
    """ Categorize the files by header type
    """
    df = pd.read_csv("./processed/header_info.csv")

    heads = df.iloc[: , 3: ]

    # Clean the headers
    # lower, strip, remove accents,
    for c in heads.columns:
        heads[c] = clean_header(heads[c])

    # Sort the dataframe, row by row
    for i in heads.index:
        heads.loc[i, : ] = heads.loc[i, : ].sort_values()

    heads.drop_duplicates().to_csv("./processed/unique_headers.csv", index = False)


def append_gov_data(gov_level):

    raw_dir = "./raw/" + gov_level + "/"

    dfs = []

    for raw_dir_f in os.listdir(raw_dir):
        for f in os.listdir(raw_dir + raw_dir_f):
            df = pd.read_excel(raw_dir + raw_dir_f + "/" + f)

            # Get the header row and drop rows before it.
            # This assumes:
            #   1. The header row is the first row without missing values.
            #   2. The header row has no missing values...
            header_i = np.where(~df.isna().any(axis = 1))[0][0]
            head = df.iloc[header_i, : ]
            df = df.iloc[header_i + 1: , :]

            df.columns = clean_header(head)
            header_renames = {
                "denominacion del cargo o nombramiento otorgado": "denominacion del cargo",
                "nombre del servidor(a) publico(a)": "nombre",
                "primer apellido del servidor(a) publico(a)": "primer apellido",
                "segundo apellido del servidor(a) publico(a)": "segundo apellido",
                "area o unidad administrativa de adscripcion": "area de adscripcion",
                "domicilio oficial: tipo de vialidad (catalogo)": "tipo de vialidad",
                "domicilio oficial: nombre de vialidad": "nombre de vialidad",
                "domicilio oficial: numero exterior": "numero exterior",
                "domicilio oficial: numero interior": "numero interior",
                "domicilio oficial: tipo de asentamiento (catalogo)": "tipo de asentamiento",
                "domicilio oficial: nombre del asentamiento": "nombre del asentamiento",
                "domicilio oficial: clave de la localidad": "clave de la localidad",
                "domicilio oficial: nombre de la localidad": "nombre de la localidad",
                "domicilio oficial: clave del municipio": "clave del municipio",
                "domicilio oficial: nombre del municipio": "nombre del municipio o delegacion",
                "domicilio oficial: nombre del municipio o delegacion": "nombre del municipio o delegacion",
                "domicilio oficial: clave de la entidad federativa": "clave de la entidad federativa",
                "domicilio oficial: nombre de la entidad federativa (catalogo)": "nombre de la entidad federativa",
                "domicilio oficial: codigo postal": "codigo postal",
                "area(s) responsable(s) que genera(n), posee(n), publica(n) y actualizan la informacion": "area responsable de la informacion",
                "fecha de inicio del periodo que se informa (dia/mes/ano)": "fecha de inicio del periodo que se informa",
                "fecha de termino del periodo que se informa (dia/mes/ano)": "fecha de termino del periodo que se informa",
                "fecha de alta en el cargo (dia/mes/ano)": "fecha de alta en el cargo",
                "domicilio oficial: numero interior, en su caso": "domicilio oficial: numero interior",
                "domicilio oficial: nombre del municipio o delegacion": "domicilio oficial: nombre del municipio",
                "domicilio oficial: clave de la entidad federativa (18)": "clave de la entidad federativa",
                "domicilio oficial: nombre de la entidad federativa (nayarit)": "nombre de la entidad federativa",
                "correo electronico oficial, en su caso": "correo electronico oficial",
                "area (s) responsable (s) de la informacion": "area responsable de la informacion",
                "fecha de validacion de la informacion (dia/mes/ano)": "fecha de validacion",
                "denominacion del cargo o nombramiento otorgado": "denominacion del cargo",
                "nombre(s)": "nombre",
                "numero interior, en su caso": "numero interior",
                "numero (s) de telefono oficial y extension": "numero(s) de telefono oficial",
                "ano": "ejercicio"
            }
            df = df.rename(header_renames, axis = 1)

            # Check that headers are unique
            assert df.columns.duplicated().sum() == 0

            dfs.append(df)

    df = pd.concat(dfs, axis = 0)
    del dfs

    df.to_csv("./processed/" + gov_level + ".csv", index = False)

    return df

#df = append_gov_data("s00")







#df = df.iloc[header_i + 1: , : ]
#df.columns = head
#
#
## 
#
#
#classifier = {}
#
## 2020 files have 4 rows of header and have column values of 2020 under
## column Ejercicio
## Column 1 should equal ejercicio
#header_2020 = df.iloc[3, 1].strip() == "Ejercicio"
## That column's contents should equal "2020"
#contents_2020 = (df.iloc[4: , 1] == "2020").all()
#classifier["2020"] = header and contents
#
#
## 2019 files have 4 rows of header and have column values of 2019 under
## column Ejercicio
## Column 1 should equal ejercicio
#header_2019 = df.iloc[3, 1].strip() == "Ejercicio"
## That column's contents should equal "2019"
#contents_2019 = (df.iloc[4: , 1] == "2019").all()
#classifier["2019"] = header and contents
