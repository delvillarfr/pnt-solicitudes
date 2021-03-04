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
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import ElementNotInteractableException


def wait_for_loader_to_disappear(wait):
    wait.until(EC.invisibility_of_element(
        (By.CLASS_NAME, "loader")
        ))
    return None


def get_solicitud_data(driver, i):
    print(i)

    try:
        elem = driver.find_element_by_id("heading" + str(i))
        elem.find_element_by_id("divPrincipal" + str(i)).click()
        fields = elem.find_elements_by_class_name("row")
        result = [f.text for f in fields]

    except NoSuchElementException:
        try:
            driver.find_element_by_css_selector(".page-item.next a").click()
            raise AssertionError
        except ElementNotInteractableException:
            result = []

    return result


def get_solicitudes(state = None, starting_page = None, spp = None):
    """
        spp (int): Number of solicitudes per page. It can be 20, 50, 100, 200,
            or 500.
    """
    if state is None:
        state = "01"

    if starting_page is None:
        starting_page = 1

    if spp is None:
        spp = 500

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
    short_wait = WebDriverWait(driver, 2, poll_frequency=0.1)

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
            driver.find_element_by_css_selector(".page-item.next a").click()
        page = starting_page

        # Problem: the list of solicitudes takes a while to fully update.
        # While updating, either divPrincipal or its contents show up as stale
        # or it is not possible to view the contents.
        wait_for_loader_to_disappear(wait)
        #wait.until(lambda d: page_has_loaded(d, spp))


        while True:
            print("Ent: " + state)
            print("Page: " + str(page) + " of " + str(n_pages))

            wait_for_loader_to_disappear(wait)
            #wait.until(lambda d: page_has_loaded(d, spp))

            # A stale exception means that the list of solicitudes was still
            # loading. Ignore this exception and start again when it occurs.
            try:
                records = [] 
                for i in range(spp):
                    fields = get_solicitud_data(driver, i)

                    if fields == "reload":
                        driver.quit()
                        return get_solicitudes(state, page, spp)
                    else:
                        records.append(fields)

                df = pd.DataFrame(records)
                df.to_csv("./raw/solicitudes/s" + state + "/p" + str(page) + ".csv", index = False)

                try:
                    driver.find_element_by_css_selector(".page-item.next a").click()
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



#def page_has_loaded(driver, spp):
#    try:
#        get_solicitud_data(driver, 0)
#        get_solicitud_data(driver, spp-1)
#        verdict = True
#
#    except StaleElementReferenceException:
#        verdict = False
#
#    return verdict
#
#def wait_for_loader_to_disappear(wait):
#    wait.until(EC.invisibility_of_element(
#        (By.XPATH, "/html/body/div[1]/div[2]")
#        ))
#    return None
#def get_solicitud_data(driver, wait, short_wait, i, trial_no = None):
#    if trial_no is None:
#        trial_no = 1
#    print(i)
#
#
#    try:
#        driver.find_element_by_id("divPrincipal" + str(i)).click()
#    except StaleElementReferenceException:
#        print("Stale Exception. Trying again...")
#        time.sleep(2)
#        return get_solicitud_data(driver, wait, short_wait, i)
#
#
#    try:
#        fields = short_wait.until(EC.visibility_of_all_elements_located(
#            (By.XPATH, "//div[@id='accordion']/div["+str(2*i + 1)+"]/div[2]//div[@class='row']")
#            ))
#    except TimeoutException:
#        trial_no += 1
#        if trial_no > 3:
#            print("Failed too many times. Restarting on current page.")
#            return "reload"
#
#        print("Failed to get the solicitud information. Trying again...")
#        time.sleep(5)
#        #driver.find_element_by_id("divPrincipal" + str(i)).click()
#        # Go forth and back to ``refresh'' the page...
#        driver.find_element_by_xpath(
#                "//ul[@id='pagination']/li[@class='page-item next']/a"
#                ).click()
#        wait_for_loader_to_disappear(wait)
#        driver.find_element_by_xpath(
#                "//ul[@id='pagination']/li[@class='page-item prev']/a"
#                ).click()
#        wait_for_loader_to_disappear(wait)
#        time.sleep(5)
#        return get_solicitud_data(driver, wait, short_wait, i, trial_no)
#
#    return fields
#
#
#def page_has_loaded(driver, n_items):
#    try:
#        driver.find_element_by_id("divPrincipal0").click()
#        time.sleep(1)
#        driver.find_element_by_xpath(
#                "//div[@id='accordion']/div[1]/div[2]//div[@class='row']"
#                )
#    except (StaleElementReferenceException, NoSuchElementException) as e:
#        print("Stale Exception. Wait for page to load...")
#        return False
#    driver.find_element_by_id("divPrincipal0").click()
#
#    time.sleep(3)
#
#    try:
#        driver.find_element_by_id("divPrincipal"+str(n_items-1)).click()
#        time.sleep(1)
#        driver.find_element_by_xpath(
#                "//div[@id='accordion']/div["+str(2*(n_items-1) + 1)+"]/div[2]//div[@class='row']"
#                )
#    except (StaleElementReferenceException, NoSuchElementException) as e:
#        print("Stale Exception. Wait for page to load...")
#        return False
#    driver.find_element_by_id("divPrincipal"+str(n_items-1)).click()
#
#    return True
#
#
#def get_solicitudes(state = None, starting_page = None):
#    if state is None:
#        state = "01"
#
#    if starting_page is None:
#        starting_page = 1
#
#
#    # Set Firefox preferences
#    profile = webdriver.FirefoxProfile()
#    # Do not load images.
#    profile.set_preference("permissions.default.image", 2)
#    opts = webdriver.firefox.options.Options()
#    #opts.set_headless()
#
#    driver = webdriver.Firefox(firefox_profile=profile, options = opts)
#    wait = WebDriverWait(driver, 360, poll_frequency=0.1)
#    short_wait = WebDriverWait(driver, 2, poll_frequency=0.1)
#
#    url = "https://buscador.plataformadetransparencia.org.mx/en/buscadornacional?buscador=informacion%20publica&coleccion=2"
#
#    driver.get(url)
#
#    try:
#
#        # Filter by state
#        wait.until(EC.element_to_be_clickable(
#            (By.ID, "o_" + str(int(state)))
#            )).click()
#
#        # Order results by most recent
#        wait_for_loader_to_disappear(wait)
#        wait.until(EC.element_to_be_clickable(
#            (By.XPATH, "/html/body/div[1]/section/div/div/div/div/div/section/div/div[2]/div/div[2]/div[3]/div[2]/div/div[1]/div[2]/div[1]/div/button")
#            )).click()
#        wait_for_loader_to_disappear(wait)
#        driver.find_element_by_id("bs-select-3-1").click()
#
#        # Select number records per page
#        wait_for_loader_to_disappear(wait)
#        wait.until(EC.element_to_be_clickable(
#            (By.XPATH, "/html/body/div[1]/section/div/div/div/div/div/section/div/div[2]/div/div[2]/div[3]/div[2]/div/div[1]/div[2]/div[2]/div/button/div/div/div")
#            )).click()
#        wait_for_loader_to_disappear(wait)
#        driver.find_element_by_id("bs-select-4-4").click()
#
#        # Record the number of pages
#        wait_for_loader_to_disappear(wait)
#        driver.find_element_by_xpath(
#                "//ul[@id='pagination']/li[@class='page-item last']/a"
#                ).click()
#        wait_for_loader_to_disappear(wait)
#        n_pages = driver.find_element_by_xpath(
#            "//ul[@id='pagination']/li[@class='page-item active']/a"
#            ).text
#        wait_for_loader_to_disappear(wait)
#        driver.find_element_by_xpath(
#                "//ul[@id='pagination']/li[@class='page-item first']/a"
#                ).click()
#
#        for i in range(starting_page - 1):
#            print(i+1)
#            wait_for_loader_to_disappear(wait)
#            driver.find_element_by_xpath(
#                    "//ul[@id='pagination']/li[@class='page-item next']/a"
#                    ).click()
#        page = starting_page
#
#        # Problem: the list of solicitudes takes a while to fully update.
#        # While updating, either divPrincipal or its contents show up as stale
#        # or it is not possible to view the contents.
#        wait_for_loader_to_disappear(wait)
#        while page_has_loaded(driver, n_items = 500) == False:
#            time.sleep(1)
#
#
#        # Extract information from every record in every page
#
#        ## Loop over pages
#
#        while True:
#            print("Ent: " + state)
#            print("Page: " + str(page) + " of " + str(n_pages))
#            wait_for_loader_to_disappear(wait)
#            while page_has_loaded(driver, n_items = 500) == False:
#                time.sleep(1)
#
#            records = [] 
#            for i in range(500):
#                try:
#                    fields = get_solicitud_data(driver, wait, short_wait, i)
#                    if fields == "reload":
#                        driver.quit()
#                        return get_solicitudes(state, page)
#                except NoSuchElementException:
#                    break
#                records.append([f.text for f in fields])
#
#            #if records == "try_again":
#            #    print("Too many failures. Starting over at current page.")
#            #    driver.quit()
#            #    return get_solicitudes(state, page)
#
#            df = pd.DataFrame(records)
#            df.to_csv("./raw/solicitudes/s" + state + "/p" + str(page) + ".csv", index = False)
#
#            try:
#                # Go to next page
#                driver.find_element_by_xpath(
#                        "//ul[@id='pagination']/li[@class='page-item next']/a"
#                        ).click()
#
#            except NoSuchElementException:
#                break
#
#            # If we're not in the last page, test the DataFrame contains
#            # all records.
#            assert len(df) == 500
#
#            page += 1
#
#    except StaleElementReferenceException:
#        print("Stale exception. Restarting on current page...")
#        driver.quit()
#        return get_solicitudes(state, page)
#
#    finally:
#        ## ALWAYS close the session
#        driver.quit()
#
#    return None

#get_solicitudes("01")



#def click_all_solicitudes(driver, n_solicitudes):
#    print("clicking all solicitudes...")
#    for i in range(n_solicitudes):
#        print(i)
#        try:
#            driver.find_element_by_id("divPrincipal" + str(i)).click()
#        except StaleElementReferenceException:
#            print("Stale Exception. Trying again...")
#            time.sleep(5)
#            driver.find_element_by_id("divPrincipal" + str(i)).click()
#
#    return None

#def get_solicitudes(state = None, starting_page = None):
#    if state is None:
#        state = "01"
#
#    if starting_page is None:
#        starting_page = 1
#
#
#    # Set Firefox preferences
#    profile = webdriver.FirefoxProfile()
#    # Do not load images.
#    profile.set_preference("permissions.default.image", 2)
#    opts = webdriver.firefox.options.Options()
#    opts.set_headless()
#
#    driver = webdriver.Firefox(firefox_profile=profile, options = opts)
#    wait = WebDriverWait(driver, 60, poll_frequency=0.1)
#    short_wait = WebDriverWait(driver, 5, poll_frequency=0.1)
#
#    url = "https://buscador.plataformadetransparencia.org.mx/en/buscadornacional?buscador=informacion%20publica&coleccion=2"
#
#    driver.get(url)
#
#    try:
#
#        # Filter by state
#        wait.until(EC.element_to_be_clickable(
#            (By.ID, "o_" + str(int(state)))
#            )).click()
#
#        # Order results by most recent
#        wait_for_loader_to_disappear(wait)
#        wait.until(EC.element_to_be_clickable(
#            (By.XPATH, "/html/body/div[1]/section/div/div/div/div/div/section/div/div[2]/div/div[2]/div[3]/div[2]/div/div[1]/div[2]/div[1]/div/button")
#            )).click()
#        wait_for_loader_to_disappear(wait)
#        driver.find_element_by_id("bs-select-3-1").click()
#
#        # Select 500 records per page
#        wait_for_loader_to_disappear(wait)
#        wait.until(EC.element_to_be_clickable(
#            (By.XPATH, "/html/body/div[1]/section/div/div/div/div/div/section/div/div[2]/div/div[2]/div[3]/div[2]/div/div[1]/div[2]/div[2]/div/button/div/div/div")
#            )).click()
#        wait_for_loader_to_disappear(wait)
#        driver.find_element_by_id("bs-select-4-4").click()
#
#        # Go to starting page (we go from oldest to newest solicitud)
#        wait_for_loader_to_disappear(wait)
#        driver.find_element_by_xpath(
#                "//ul[@id='pagination']/li[@class='page-item last']/a"
#                ).click()
#        wait_for_loader_to_disappear(wait)
#        n_pages = driver.find_element_by_xpath(
#            "//ul[@id='pagination']/li[@class='page-item active']/a"
#            ).text
#
#        for i in range(starting_page - 1):
#            print(i+1)
#            wait_for_loader_to_disappear(wait)
#            driver.find_element_by_xpath(
#                    "//ul[@id='pagination']/li[@class='page-item prev']/a"
#                    ).click()
#        page = starting_page
#
#
#        # Extract information from every record in every page
#
#        ## Loop over pages
#
#        while True:
#            print("Ent: " + state)
#            print("Page: " + str(page) + " of " + str(n_pages))
#
#            wait_for_loader_to_disappear(wait)
#            time.sleep(1)
#            #test = wait.until(EC.element_to_be_clickable(
#            #    (By.XPATH, "//div[@id='accordion']/div/div[1]/div/button")
#            #    ))
#            #toggle_btns = get_web_elements(
#            #    driver, "//div[@id='accordion']/div/div[1]/div/button"
#            #    )
#            #while len(toggle_btns) < 50:
#            #    print("There's not enough toggle buttons detected!")
#            #    time.sleep(2)
#            #    toggle_btns = get_web_elements(
#            #        driver, "//div[@id='accordion']/div/div[1]/div/button"
#            #        )
#
#            df = pd.DataFrame(get_page_data(driver, 100)
#
#            if page > 1:
#                assert len(df) == 100
#
#            df.to_csv("./raw/solicitudes/s" + state + "/p" + str(page) + ".csv", index = False)
#
#            page += 1
#
#            # Go to next page
#            #wait_for_loader_to_disappear(wait)
#            driver.find_element_by_xpath(
#                    "//ul[@id='pagination']/li[@class='page-item prev']/a"
#                    ).click()
#
#    finally:
#        ## ALWAYS close the session
#        driver.quit()
#
#    return None


## Set Firefox preferences
#profile = webdriver.FirefoxProfile()
#profile.set_preference("browser.download.folderList", 2)
#profile.set_preference("browser.download.manager.showWhenStarting", False)
#opts = webdriver.firefox.options.Options()
##opts.set_headless()
#
#driver = webdriver.Firefox(firefox_profile=profile, options = opts)
#url = "https://buscador.plataformadetransparencia.org.mx/en/buscadornacional?buscador=00103&coleccion=2"
##url = "https://buscador.plataformadetransparencia.org.mx/en/buscadornacional?buscador=informacion%20publica&coleccion=2"
#driver.get(url)
#wait = WebDriverWait(driver, 30, poll_frequency=1)#, ignored_exceptions=[ElementNotVisibleException, ElementNotSelectableException])
#
#
#state = 15
#
#time.sleep(5)
#
## Filter by state
#options = get_web_elements(
#    driver, "//input[@id='o_" + str(state) + "']"
#    )
#options[0].click()
#
#time.sleep(5)
#
## Select 500 records per page
#options = get_web_elements(
#        driver, "//div[@class='form-group']/div[1]"
#        )
#options[1].click()
#
#time.sleep(2)
#
#options = get_web_elements(
#        driver, "//*[@id='bs-select-4-4']"
#        )
#options[0].click()
#
#time.sleep(5)
#
#
#
#starting_page = 5
#for i in range(starting_page - 1):
#    print(i+1)
#    # Go to next page
#    # Wait until the loader becomes stale
#    #option = wait.until(EC.element_to_be_clickable(
#    #    (By.XPATH, "//ul[@id='pagination']/li[@class='page-item next']/a")
#    #    ))
#    #option.click()
#    #nxt = driver.find_element_by_xpath("//ul[@id='pagination']/li[@class='page-item next']/a")
#    #loader = driver.find_element_by_xpath("/html/body/div[1]/div[2]")
#    #nxt = driver.find_element_by_xpath("//ul[@id='pagination']/li[@class='page-item next']/a")
#    #nxt = wait.until(EC.visibility_of_element_located(
#    #    (By.XPATH, "//ul[@id='pagination']/li[@class='page-item next']/a")
#    #    ))
#    #nxt.click()
#    nxt = wait.until(EC.presence_of_element_located(
#        (By.XPATH, "//ul[@id='pagination']/li[@class='page-item next']/a")
#        ))
#    nxt.click()
#    #wait.until(EC.staleness_of(
#    #    driver.find_element_by_xpath("/html/body/div[1]/div[2]")
#    #    ))
#
## Extract information from every record in every page
#
### Loop over pages
#page = 0
#
##while True:
##for n in range(3):
#l = []
#page += 1
#
#toggle_btns = get_web_elements(
#    driver, "//div[@id='accordion']/div/div[1]/div/button"
#    )
#
#for i in range(20):
#
#    toggle_btns[i].click()
#
#    options = get_web_elements(
#        driver, "//div[@id='accordion']/div["+str(2*i + 1)+"]/div[2]//div[@class='row']"
#        )
#    d = {
#            o.text.split("\n", maxsplit = 1)[0]: o.text.split("\n", maxsplit = 1)[1]
#            for o in options
#            }
#
#    l.append(d)
#
## Go to next page
#options = get_web_elements(
#    driver, "//ul[@id='pagination']/li[@class='page-item next']/a"
#    )
#options[0].click()
#time.sleep(5)
#def get_web_elements(driver, xpath, expected_length = None, secs_timeout = None):
#    if secs_timeout is None:
#        secs_timeout = 120
#
#    #response = WebDriverWait(driver, timeout = secs_timeout).until(
#    #        lambda d: d.find_elements_by_xpath(xpath)
#    #        )
#    response = driver.find_elements_by_xpath(xpath)
#
#    return response
#
#def my_click(element):
#    try:
#        element.click()
#    except ElementClickInterceptedException:
#        time.sleep(1)
#        return myclick(element)
#    return None
#
#def get_page_data(driver, wait, n_items, trial_number = None):
#    if trial_number is None:
#        trial_number = 1
#    elif trial_number > 4:
#        return "try_again"
#        
#    l = [] 
#    for i in range(n_items):
#        print(i)
#        try:
#            driver.find_element_by_id("divPrincipal" + str(i)).click()
#        except NoSuchElementException:
#            d = {"end": True}
#            l.append(d)
#            break
#
#        try:
#            fields = wait.until(EC.visibility_of_all_elements_located(
#                (By.XPATH, "//div[@id='accordion']/div["+str(2*i + 1)+"]/div[2]//div[@class='row']")
#                ))
#        except TimeoutException:
#            print("Failed to get the solicitud information. Trying again...")
#            # Go forth and back to ``refresh'' the page...
#            driver.find_element_by_xpath(
#                    "//ul[@id='pagination']/li[@class='page-item next']/a"
#                    ).click()
#            wait_for_loader_to_disappear(wait)
#            driver.find_element_by_xpath(
#                    "//ul[@id='pagination']/li[@class='page-item prev']/a"
#                    ).click()
#            wait_for_loader_to_disappear(wait)
#            time.sleep(1)
#            return get_page_data(driver, wait, n_items, trial_number + 1)
#
#        l.append([f.text for f in fields])
#
#    return l
