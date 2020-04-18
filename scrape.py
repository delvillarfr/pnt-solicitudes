import os
import time
import sys
import subprocess
import numpy as np
import pandas as pd
import warnings
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException


# My modules
import wrangler


def scrape_institutions_catalog():
    profile = webdriver.FirefoxProfile()
    #opts = webdriver.firefox.options.Options()
    #opts.set_headless()

    driver = webdriver.Firefox()#, options = opts)
    url = "https://consultapublicamx.inai.org.mx/vut-web/faces/view/consultaPublica.xhtml#inicio"
    driver.get(url)

    # Open the menu options for the government level
    gov_button = get_web_elements(
        driver, "//form[@id='formEntidadFederativa']//button", 1
        )
    gov_button[0].click()

    gov_options = get_web_elements(
        driver,
        "//form[@id='formEntidadFederativa']//a"
        )
    governments = [i.text for i in gov_options]

    ## Press the dropdown button again to enter loop
    gov_button[0].click()


    dfs = []

    # First entry in governments is "Selecciona"
    for government in governments[1: ]:
        time.sleep(5)

        # Find the buttons and the list of web elements once again...
        gov_button = get_web_elements(
            driver, "//form[@id='formEntidadFederativa']//button", 1
            )
        gov_button[0].click()
        gov_options = get_web_elements(
            driver,
            "//form[@id='formEntidadFederativa']//a"
            )
        gov_options[governments.index(government)].click()

        ## Now fetch the entities associated to this government
        options = get_web_elements(
            driver,
            "//div[@id='formListaSujetosAZ:listaAZSujetos']/ol//li/div/ol/child::li/input"
            )

        entities = [i.get_attribute("value") for i in options]
        ids = [i.get_attribute("id") for i in options]

        driver.back()

        df = pd.DataFrame(
                np.column_stack((len(entities) * [government], entities, ids)),
                columns = ["government", "institution", "id_pnt_institution"]
                )
        dfs.append(df)

    ## Close session
    driver.quit()


    df = pd.concat(dfs, axis = 0)
    df.to_csv("./raw/institutions.csv", index = False)


def process_institutions_catalog():
    df = pd.read_csv("./raw/institutions.csv")

    # Merge with INEGI catalog to get state ids
    ids = pd.read_csv("../inegi/catalogo_unico_areas_geoestadisticas/catun_localidad.csv")
    ids = ids[["Cve_Ent", "Nom_Ent"]].drop_duplicates()

    # Clean names for a clean merge...
    ids["Nom_Ent"] = ids["Nom_Ent"].str.replace(" De ", " de ")
    ids["Nom_Ent"] = ids["Nom_Ent"].str.replace(" de Ignacio de La Llave", "")
    df = df.merge(ids, left_on = "government", right_on = "Nom_Ent", how = "left")

    df["Cve_Ent"] = df["Cve_Ent"].fillna(0).astype(int).astype(str)

    # Check the PNT institution ids have the same length
    assert len(df["id_pnt_institution"].str.len().value_counts()) == 1

    df["id_government"] = "s" + wrangler.prepend_zeros(df["Cve_Ent"], 2)
    df["id_pnt_institution"] = df["id_pnt_institution"].str[-9: ]

    df = df[[
        "id_government",
        "government",
        "id_pnt_institution",
        "institution"
        ]].to_csv("./processed/institutions.csv", index = False)


def create_directory_structure():
    df = pd.read_csv("./processed/institutions.csv")

    for k in df.index:
        s = df["id_government"].iloc[k]
        i = df["id_pnt_institution"].iloc[k]
        subprocess.call(["mkdir", "-p", "raw/" + s + "/" + i])




def get_web_elements(driver, xpath, expected_length = None, secs_timeout = None):
    if secs_timeout is None:
        secs_timeout = 120

    response = WebDriverWait(driver, timeout = secs_timeout).until(
            lambda d: d.find_elements_by_xpath(xpath)
            )

    #if expected_length is not None:
        #warnings.warn("""
            #Mismatch between the expected and actual number of retrieved web
            #elements.
        #""")

    return response


def download_pnt_target_data(
        government, institution, target_dir, obligation = None
        ):

    if obligation is None:
        obligation = "DIRECTORIO"

    print("Starting scraping job with the following specs:")
    print({
        "government": government,
        "institution": institution,
        "target_dir": target_dir,
        "obligation": obligation
        })

    # Set Firefox preferences
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.download.folderList", 2)
    profile.set_preference("browser.download.manager.showWhenStarting", False)
    profile.set_preference("browser.download.dir", target_dir)
    profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/vnd.ms-excel")
    opts = webdriver.firefox.options.Options()
    #opts.set_headless()

    driver = webdriver.Firefox(firefox_profile=profile, options = opts)
    url = "https://consultapublicamx.inai.org.mx/vut-web/faces/view/consultaPublica.xhtml#inicio"
    driver.get(url)

    print("Driver initialized...")

    # Open the menu options for the government level
    options = get_web_elements(
        driver, "//form[@id='formEntidadFederativa']//button", 1
        )
    options[0].click()

    # Click on the desired government level
    options = get_web_elements(
        driver, "//form[@id='formEntidadFederativa']//a"
        )
    governments = [i.text for i in options]
    options[governments.index(government)].click()

    print("Government selected...")

    # Click on a letter before selecting an institution
    options = get_web_elements(
        driver,
        "//div[@id='formListaSujetosAZ:listaAZSujetos']/ol/child::li"
        )
    available_letters = [i.text for i in options]
    letter_index = available_letters.index(institution[0])
    options[letter_index].click()


    # Now select an institution. It must start with the stated letter
    ## list entries are 1-indexed in the HTML
    options = get_web_elements(
        driver,
        "//div[@id='formListaSujetosAZ:listaAZSujetos']/ol/li["
        + str(letter_index + 1) + "]/div/ol/child::li/input"
        )
    institutions = [i.get_attribute("value") for i in options]
    options[institutions.index(institution)].click()

    print("Government institution selected...")


    # Click on the dropdown menu to select the years.
    button_years = get_web_elements(
        driver, "//div[@id='periodoOriginal']/div/button", 1
        )
    button_years[0].click()

    # Select a year from the dropdown menu
    year_options = get_web_elements(
        driver, "//div[@id='periodoOriginal']//a"
        )
    years = [i.text for i in year_options]

    # Click again on the menu to enter loop...
    button_years[0].click()


    for year in years:
        # Click on the dropdown menu to select the years.
        button_years = get_web_elements(
            driver, "//div[@id='periodoOriginal']/div/button", 1
            )
        button_years[0].click()

        # Select a year from the dropdown menu
        year_options = get_web_elements(
            driver, "//div[@id='periodoOriginal']//a"
            )
        year_options[years.index(year)].click()

        print("Year range " + str(year) + " selected...")

        # Now select the type of data to download, e.g. the Directorio
        ## If there are no obligations, get outta here.
        try:
            options = get_web_elements(
                driver,
                "//div[@id='formListaObligaciones:listaObligacionesTransparencia']/div[1]/child::label",
                secs_timeout = 5
                )
        except TimeoutException:
            break

        obligations = [i.text for i in options]
        obligation_ids = [i.get_attribute("id") for i in options]

        # Proceed only if the obligation exists...
        if obligation in obligations:
            options[obligations.index(obligation)].click()


            # Click download
            options = get_web_elements(
                driver,
                "//a[starts-with(@id,'formDescargaArchivos')]"
                )
            options_labels = [i.text for i in options]

            # Skip if there is no download available
            if "DESCARGAR" in options_labels:
                options = options[options_labels.index("DESCARGAR")].click()


                # Select Excel download
                options = get_web_elements(
                    driver, "//span[@id='descargaExcel']//label", 1
                    )
                options[0].click()


                # Click on range
                button_excel_range = get_web_elements(
                    driver, "//span[@id='formModalRangos:panelRangoExcel']//button", 1
                    )
                button_excel_range[0].click()

                # Select range
                options = get_web_elements(driver, "//form[@id='formModalRangos']//a")
                excel_ranges = [i.text for i in options]


                # Click the excel range button again to enter loop...
                button_excel_range[0].click()

                # First entry in the range is "Selecciona"
                for excel_range in excel_ranges[1: ]:

                    # Click on range
                    button_excel_range = get_web_elements(
                        driver, "//span[@id='formModalRangos:panelRangoExcel']//button", 1
                        )
                    button_excel_range[0].click()

                    # Select range
                    options = get_web_elements(driver, "//form[@id='formModalRangos']//a") 
                    options[excel_ranges.index(excel_range)].click()

                    print("Download initialized for range " + str(excel_range) + "...")

                    # Count the number of files in the target directory
                    files_pre = os.listdir(target_dir)

                    ## hit Download
                    options = get_web_elements(
                        driver,
                        "//input[@id='formModalRangos:btnDescargaExcel']"
                        )
                    options[0].click()

                    ## Check if file has downloaded
                    files_post = files_pre
                    while (
                            (len(files_pre) + 1) != len(files_post)
                            or any([f[-3: ] != "xls" for f in files_post])
                        ):
                        time.sleep(5)
                        files_post = os.listdir(target_dir)

                    print("Download finalized...")

                # Close the download dialog by hitting <esc>
                webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(2)


    ## Close session

    driver.quit()

    return None


def download_pnt_bulk_data(obligation = None):
    df = pd.read_csv("./processed/institutions.csv")

    for i in df.index:
        print("Starting row " + str(i) + " of institutions catalog.")
        target_dir = (
            "/home/fdvom/grive/data/pnt/raw/"
            + df["id_government"].iloc[i] + "/"
            + df["id_pnt_institution"].iloc[i]
            )
        government = df["government"].iloc[i]
        institution = df["institution"].iloc[i]

        download_pnt_target_data(government, institution, target_dir, obligation)








# Function calls
#create_directory_structure()
download_pnt_bulk_data()
