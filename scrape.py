import os
import time
import sys
import pandas as pd
import warnings
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options


def get_web_elements(driver, xpath, expected_length = None):
    response = WebDriverWait(driver, timeout = 120).until(
            lambda d: d.find_elements_by_xpath(xpath)
            )

    #if expected_length is not None:
        #warnings.warn("""
            #Mismatch between the expected and actual number of retrieved web
            #elements.
        #""")

    return response


def download_pnt_data(
        government, entity, data_category, target_dir = None
        ):

    specs = {
            "government": government,
            "entity": entity,
            "data_category": data_category
            }
    print("Starting scraping job with the following specs:")
    print(specs)

    if target_dir is None:
        target_dir = "/home/fdvom/grive/data/pnt/" + government + "/" + entity + "/"

    # Set Firefox preferences
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.download.folderList", 2)
    profile.set_preference("browser.download.manager.showWhenStarting", False)
    profile.set_preference("browser.download.dir", target_dir)
    profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/vnd.ms-excel")
    opts = webdriver.firefox.options.Options()
    opts.set_headless()

    driver = webdriver.Firefox(firefox_profile=profile, options = opts)
    url = "https://consultapublicamx.inai.org.mx/vut-web/faces/view/consultaPublica.xhtml#inicio"
    driver.get(url)

    # Momentarily cheating
    #target_dir = "/home/fdvom/grive/data/pnt/FederaciSn/Aeropuerto Internacional de la Ciudad de MIxico, S.A. de C.V. (AICM)/"

    print("Driver initialized...")

    # Open the menu options for the government level
    options = get_web_elements(
        driver,
        "//form[@id='formEntidadFederativa']//button",
        1
        )
    options[0].click()

    # Click on the desired government level
    options = get_web_elements(
        driver,
        "//form[@id='formEntidadFederativa']//a"
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
    letter_index = available_letters.index(entity[0])
    options[letter_index].click()


    # Now select an institution. It must start with the stated letter
    ## list entries are 1-indexed in the HTML
    options = get_web_elements(
        driver,
        "//div[@id='formListaSujetosAZ:listaAZSujetos']/ol/li["
        + str(letter_index + 1) + "]/div/ol/child::li/input"
        )
    entities = [i.get_attribute("value") for i in options]
    options[entities.index(entity)].click()

    print("Government institution selected...")


    # Click on the dropdown menu to select the years.
    options = get_web_elements(
        driver,
        "//div[@id='periodoOriginal']/div/button",
        1
        )
    options[0].click()

    # Select a year from the dropdown menu
    options = get_web_elements(
        driver,
        "//div[@id='periodoOriginal']//a"
        )
    years = [i.text for i in options]

    options[0].click()

    print("Year range selected...")

    # Now select the type of data to download, e.g. the Directorio
    options = get_web_elements(
        driver,
        "//div[@id='formListaObligaciones:listaObligacionesTransparencia']/div[1]/child::label"
        )
    obligations = [i.text for i in options]
    obligation_ids = [i.get_attribute("id") for i in options]

    options[obligations.index("DIRECTORIO")].click()


    # Click download
    options = get_web_elements(
        driver,
        "//a[starts-with(@id,'formDescargaArchivos')]"
        )
    options_labels = [i.text for i in options]
    options = options[options_labels.index("DESCARGAR")].click()


    # Select Excel download
    options = get_web_elements(
        driver,
        "//span[@id='descargaExcel']//label",
        1
        )
    options[0].click()


    # Click on range
    options = get_web_elements(
        driver,
        "//span[@id='formModalRangos:panelRangoExcel']//button",
        1
        )
    options[0].click()


    # Select range
    options = get_web_elements(
        driver,
        "//form[@id='formModalRangos']//a",
        )
    excel_ranges = [i.text for i in options]
    options[1].click()

    print("Download initialized...")

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
        print(len(files_pre))
        print(len(files_post))
        print([f[-3: ] for f in files_post])
        print([f[-3: ] != "xls" for f in files_post])
        time.sleep(5)
        files_post = os.listdir(target_dir)

    print("Download finalized...")

    ## Close session

    driver.quit()

    return None


#government = "Federación"
#entity = "Aeropuerto Internacional de la Ciudad de México, S.A. de C.V. (AICM)"
#data_category = "DIRECTORIO"
#target_dir = None
#
#download_pnt_data(government, entity, data_category)
#
#
#sys.exit()

# Create the government-entity dataset

# Set Firefox preferences
profile = webdriver.FirefoxProfile()
profile.set_preference("browser.download.folderList", 2)
profile.set_preference("browser.download.manager.showWhenStarting", False)
profile.set_preference("browser.download.dir", target_dir)
profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/vnd.ms-excel")
#opts = webdriver.firefox.options.Options()
#opts.set_headless()

driver = webdriver.Firefox(firefox_profile=profile)#, options = opts)
url = "https://consultapublicamx.inai.org.mx/vut-web/faces/view/consultaPublica.xhtml#inicio"
driver.get(url)

# Open the menu options for the government level
options = get_web_elements(
    driver,
    "//form[@id='formEntidadFederativa']//button",
    1
    )
options[0].click()

# Click on the desired government level
options = get_web_elements(
    driver,
    "//form[@id='formEntidadFederativa']//a"
    )
governments = [i.text for i in options]
options[governments.index(government)].click()


# Click on a letter before selecting an institution
options = get_web_elements(
    driver,
    "//div[@id='formListaSujetosAZ:listaAZSujetos']/ol/child::li"
    )
available_letters = [i.text for i in options]
letter_index = available_letters.index(entity[0])
options[letter_index].click()


# Now select an institution. It must start with the stated letter
## list entries are 1-indexed in the HTML
options = get_web_elements(
    driver,
    "//div[@id='formListaSujetosAZ:listaAZSujetos']/ol/li["
    + str(letter_index + 1) + "]/div/ol/child::li/input"
    )
entities = [i.get_attribute("value") for i in options]
options[entities.index(entity)].click()


# Click on the dropdown menu to select the years.
options = get_web_elements(
    driver,
    "//div[@id='periodoOriginal']/div/button",
    1
    )
options[0].click()

# Select a year from the dropdown menu
options = get_web_elements(
    driver,
    "//div[@id='periodoOriginal']//a"
    )
years = [i.text for i in options]

options[0].click()


# Now select the type of data to download, e.g. the Directorio
options = get_web_elements(
    driver,
    "//div[@id='formListaObligaciones:listaObligacionesTransparencia']/div[1]/child::label"
    )
obligations = [i.text for i in options]
obligation_ids = [i.get_attribute("id") for i in options]

options[obligations.index("DIRECTORIO")].click()


# Click download
options = get_web_elements(
    driver,
    "//a[starts-with(@id,'formDescargaArchivos')]"
    )
options_labels = [i.text for i in options]
options = options[options_labels.index("DESCARGAR")].click()


# Select Excel download
options = get_web_elements(
    driver,
    "//span[@id='descargaExcel']//label",
    1
    )
options[0].click()


# Click on range
options = get_web_elements(
    driver,
    "//span[@id='formModalRangos:panelRangoExcel']//button",
    1
    )
options[0].click()


# Select range
options = get_web_elements(
    driver,
    "//form[@id='formModalRangos']//a",
    )
excel_ranges = [i.text for i in options]
options[1].click()

## hit Download
options = get_web_elements(
    driver,
    "//input[@id='formModalRangos:btnDescargaExcel']"
    )
options[0].click()


## Close session
driver.quit()
