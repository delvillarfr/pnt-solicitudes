import numpy as np
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import ElementNotInteractableException


def wait_for_loader_to_disappear(wait):
    wait.until(EC.invisibility_of_element(
        (By.CLASS_NAME, "loader")
        ))
    return None


def go_to_next_page(driver):
    driver.find_element_by_css_selector(".page-item.next a").click()
    return None


def get_solicitud_data(driver, i):
    """ Click on the i-th solicitud in the current page and fetch its contents.

    Args:
        i (int): the solicitud index in the current page.

    Returns:
        list: the solicitud data.
    """
    print(i)

    try:
        elem = driver.find_element_by_id("heading" + str(i))
        elem.find_element_by_id("divPrincipal" + str(i)).click()
        fields = elem.find_elements_by_class_name("row")
        result = [f.text for f in fields]

    # Return an empty list if the driver is at the last page and the solicitud
    # index exceeds the number of solicitudes on the page.
    except NoSuchElementException:
        try:
            driver.find_element_by_css_selector(".page-item.next a").click()
            raise AssertionError
        except ElementNotInteractableException:
            result = []

    return result


def get_solicitudes(
        state = None,
        starting_page = None,
        spp = None,
        directory = None
        ):
    """ Fetch and save solicitudes in the Plataforma Nacional de Transparencia.

    Each page's solicitudes are saved in .csv format for further processing.
    The .csv files are saved in the target directory. The default directory is
    "./raw/", i.e. page 124 of state "09" is saved as "./raw/s09_p124.csv".

    Solicitudes are loaded in the website by searching for
    "informacion publica".

    Args:
        state (str): The INEGI state id. One of "00", "01", ..., "32". "00"
            refers to the federal government.
        starting_page (int): The starting page to fetch solicitudes.
        spp (int): Number of solicitudes per page. It can be 20, 50, 100, 200,
            or 500.
        directory (str): The target directory.
    """
    if state is None:
        state = "01"

    if starting_page is None:
        starting_page = 1

    if spp is None:
        spp = 500

    if directory is None:
        directory = "./raw/"


    # Set Firefox preferences
    profile = webdriver.FirefoxProfile()
    # Do not load images.
    profile.set_preference("permissions.default.image", 2)

    # Set headless mode
    opts = webdriver.firefox.options.Options()
    opts.set_headless()

    # Initialize driver and waits
    driver = webdriver.Firefox(firefox_profile=profile, options = opts)
    wait = WebDriverWait(driver, 360, poll_frequency=0.1)

    # informacion publica hits all solicitudes.
    url = "https://buscador.plataformadetransparencia.org.mx/en/buscadornacional?buscador=informacion%20publica&coleccion=2"
    driver.get(url)
    wait_for_loader_to_disappear(wait)

    # The driver is guaranteed to quit from here onwards
    try:

        # Filter by state
        wait.until(EC.element_to_be_clickable((By.ID, "o_" + str(int(state))))).click()
        wait_for_loader_to_disappear(wait)


        # Order and select number of records per page
        buttons = driver.find_elements_by_css_selector("#divCombos button")

        buttons[0].click()
        driver.find_element_by_id("bs-select-3-1").click()
        wait_for_loader_to_disappear(wait)

        buttons[1].click()
        # Map spp to the corresponding selection.
        d = {
                20: "bs-select-4-0",
                50: "bs-select-4-1",
                100: "bs-select-4-2",
                200: "bs-select-4-3",
                500: "bs-select-4-4"
                }
        driver.find_element_by_id(d[spp]).click()
        wait_for_loader_to_disappear(wait)


        # Record the number of pages
        x = driver.find_elements_by_css_selector("#totalResultados span")[-1].text
        n_pages = int(np.ceil(float(x.replace(",", "")) / spp))


        # Go to the starting page
        for i in range(starting_page - 1):
            print(i+1)
            wait_for_loader_to_disappear(wait)
            go_to_next_page(driver)
        wait_for_loader_to_disappear(wait)

        page = starting_page


        # Loop through pages and exit when it is not possible to go to the
        # next page, i.e. when the driver is at the last page...
        while True:
            print("Ent: " + state)
            print("Page: " + str(page) + " of " + str(n_pages))

            wait_for_loader_to_disappear(wait)

            # A stale exception means that the list of solicitudes was still
            # loading. Ignore this exception and start again on the current
            # page when it occurs.
            try:
                records = [] 
                for i in range(spp):
                    fields = get_solicitud_data(driver, i)

                df = pd.DataFrame(records)
                df.to_csv(directory + "s" + state + "_p" + str(page) + ".csv", index = False)

                try:
                    go_to_next_page(driver)
                except ElementNotInteractableException:
                    break

                # If we're not in the last page, test the DataFrame has all rows.
                assert len(df) == spp

                page += 1
            
            except StaleElementReferenceException:
                pass

    finally:
        driver.quit()

    return None
