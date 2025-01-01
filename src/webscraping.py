import pandas as pd
import numpy as np
import re
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

def get_inputs_from_user():
    
    # league input
    scrapable_leagues = {1: "1. Bundesliga", 2: "2. Bundesliga", 3: "Premier League", 4: "EFL Championship", 5: "La Liga",
                         6: "Segunda División", 7: "Serie A", 8: "Serie B", 9: "Ligue 1", 10: "Ligue 2",
                         11: "Champions League", 12: "Europa League", 13: "Conference League", 14: "Other (Enter league name manually)"}
    while True:
        try:
            league_input = int(input("Please enter the league of the matches you want to scrape by providing the respective number:\n" +
                                     "\n".join([f"{key}: {value}" for key, value in scrapable_leagues.items()]) + "\n"))
            if 1 <= league_input <= 13:
                league = scrapable_leagues[league_input]
                break
            elif league_input == 14:
                league = input("Please enter the name of the league you want to scrape.\n")
                break
            else:
                print("Please enter a number between 1 and 14.")
        except ValueError:
            print("Invalid input. Please try again.")
    
    # season input
    while True:
        season = input("Please enter the season of the matches you want to scrape in the following format: YYYY/YY, \nfor example: \"2024/25\".\n")
        if re.match(r"^\d{4}/\d{2}$", season):
            start_year, end_year = map(int, season.split('/'))
            current_year = datetime.now().year
            if start_year <= current_year and end_year == (start_year % 100) + 1:
                break
            else:
                print("Invalid season. The season should not be in the future and should be in the format YYYY/YY.")
        else:
            print("Invalid input. Please enter the season in the format YYYY/YY.")

    search_url = "https://www.google.com/search?q="+league.replace(" ", "+")+"+spiele+"+season.replace("/", "+")
    
    return league, season, search_url


def read_or_create_match_data_csv(file_path):
    try:
        match_data = pd.read_csv(file_path, index_col=0)
    except FileNotFoundError:
        stats = ["Team", "Tore", "Schüsse", "Torschüsse", "Ballbesitz", "Pässe", "Passgenauigkeit", "Fouls", "Gelbe", "Rote", "Abseits", "Ecken"]
        match_data = pd.DataFrame(columns=(["Spieltag", "Datum", "Sieger"] + [stat+"_"+team for stat in stats for team in ["A", "B"]]))
        match_data.to_csv(file_path)
    return match_data

def init_driver_and_df(league, season, search_url):

    # get URL
    driver = webdriver.Chrome()
    driver.get(search_url)

    # Accept Cookies
    cookies_button = driver.find_element(By.CLASS_NAME, "sy4vM")
    cookies_button.click()

    # Check if URL contains "Weitere Begegnungen" button
    try:
        element = WebDriverWait(driver, 3.5).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'Z4Cazf'))
        )
        print("Page is ready to be scraped!")

        # if successful read or create the dataframe and exit while loop
        file_path = "../data/"+league.replace(" ", "_")+"_"+season.replace("/", "_")+".csv"
        df = read_or_create_match_data_csv(file_path)
    except TimeoutException as e:
        driver.quit()
        raise RuntimeError(str(e)+f"\nThe search query \"{league} {season} spiele\" did not return the expected results. Please try again.")

    return driver, df, file_path

def element_has_changed(prior_element, first=True):
    """Return a function that checks if the new element is different from the prior one."""
    def _check(driver):
        matchdays = driver.find_elements(By.CLASS_NAME, "OcbAbf")
        idx = 0 if first else len(matchdays)-1
        return matchdays[idx].text != prior_element.text
    return _check

def expand_all_matchdays(driver, scroll=True):
    try:
        WebDriverWait(driver, 3.5).until(EC.presence_of_element_located((By.CLASS_NAME, 'Z4Cazf')))
        candidate_buttons = driver.find_elements(By.CLASS_NAME, 'Z4Cazf')
        for b in candidate_buttons:
            if b.is_displayed():
                expand_button = b
                break
    except TimeoutException as e:
        raise RuntimeError(str(e)+"\nThe \"Weitere Begegnungen\" button is not present.")
    try:
        WebDriverWait(driver, 3.5).until(EC.element_to_be_clickable(expand_button))
        expand_button.click()
    except:
        print("\nThe \"Weitere Begegnungen\" button is not clickable. \n" +
              "Assuming that all matchdays are already expanded.")

    try:
        WebDriverWait(driver, 3.5).until(EC.presence_of_element_located((By.CLASS_NAME, 'OcbAbf')))
    except TimeoutException:
        raise RuntimeError("The page did not load the matchdays correctly. Please try again.")
    
    if scroll:
        # load all matchdays to top and bottom
        actions = ActionChains(driver)
        for idx, first in [(0, True), (-1, False)]:        
            while True:
                try:
                    matchdays = driver.find_elements(By.CLASS_NAME, 'OcbAbf')
                    prior_match = matchdays[idx]
                    actions.move_to_element(prior_match).perform()
                    WebDriverWait(driver, 3.5).until(element_has_changed(prior_match, first=first))
                except TimeoutException:
                    break

def split_stats(statistics):
    stat_list = []
    for i in range(10):
        stat_list += [w for w in statistics[i].text.split() if w.isdigit()]
    
    return stat_list

def scrape_data_of_match(match, driver):
    participants = match.find_elements(By.CLASS_NAME, 'L5Kkcd')
    Team_A = participants[0].find_element(By.CLASS_NAME, 'ellipsisize').text.split('\n')[0]
    Team_B = participants[1].find_element(By.CLASS_NAME, 'ellipsisize').text.split('\n')[0]

    date_el = match.find_element(By.CLASS_NAME, 'GOsQPe')
    Datum = date_el.find_element(By.CLASS_NAME, 'imspo_mt__cmd').text
    Datum = Datum.replace(',', '')
    
    Tore_A = participants[0].find_element(By.CLASS_NAME, 'imspo_mt__tt-w').text.split('\n')[0]
    Tore_A = int(Tore_A.split()[0])
    Tore_B = participants[1].find_element(By.CLASS_NAME, 'imspo_mt__tt-w').text.split('\n')[0]
    Tore_B = int(Tore_B.split()[0])
    Ergebnis = 'U'
    if Tore_A > Tore_B:
        Ergebnis = 'A'
    elif Tore_A < Tore_B:
        Ergebnis = 'B'
    
    actions = ActionChains(driver)
    actions.move_to_element(match).perform()
    WebDriverWait(driver,3.5).until(EC.element_to_be_clickable(match))
    match.click()
    time.sleep(1)

    try:
        WebDriverWait(driver, 3.5).until(EC.presence_of_element_located((By.CLASS_NAME, 'MzWkAb')))
        statistics = driver.find_elements(By.CLASS_NAME, 'MzWkAb')
        scraped_stats = split_stats(statistics)
    except TimeoutException:
        scraped_stats = [np.nan]*20
    
    back_button = driver.find_element(By.CLASS_NAME, "vtLYrb")
    back_button.click()
    
    return [Datum, Ergebnis, Team_A, Team_B, Tore_A, Tore_B] + scraped_stats

def scrape_next_match(driver, df):
    new_match_scraped = False

    try:
        WebDriverWait(driver, 3.5).until(EC.presence_of_element_located((By.CLASS_NAME, 'OcbAbf')))
        matchdays = driver.find_elements(By.CLASS_NAME, 'OcbAbf')
        matchdays = [m for m in matchdays if m.find_elements(By.CLASS_NAME, "GVj7ae")]

        for matchday in matchdays:
            # determine the number of the matchday
            matchday_text = matchday.find_elements(By.CLASS_NAME, 'GVj7ae')
            matchday_text = re.search(r'Spieltag (\d+) von', matchday_text[0].text)
            matchday_no = int(matchday_text.group(1)) if matchday_text else np.nan

            matches = [match for match in matchday.find_elements(By.CLASS_NAME, 'KAIX8d') if match.text != '']
            for match in matches:
                participants = match.find_elements(By.CLASS_NAME, 'L5Kkcd')
                Team_A = participants[0].find_element(By.CLASS_NAME, 'ellipsisize').text.split('\n')[0]
                Team_B = participants[1].find_element(By.CLASS_NAME, 'ellipsisize').text.split('\n')[0]
                        
                # is the match already in the dataframe?                
                if df[(df['Spieltag']==matchday_no)&(df['Team_A']==Team_A)&(df['Team_B']==Team_B)].empty:
                    new_row = [matchday_no] + scrape_data_of_match(match, driver)
                    df.loc[len(df.index)] = new_row
                    new_match_scraped = True
                    break
            else:
                continue
            break
    except TimeoutException as e:
        raise RuntimeError(str(e)+"\nThe page did not load the matchdays correctly. Please try again.")

    return new_match_scraped
                
def main():
    
    league, season, search_url = get_inputs_from_user()
    while True:
        try:
            driver, df, file_path = init_driver_and_df(league, season, search_url)
            expand_all_matchdays(driver)
            break
        except RuntimeError as e:
            print(str(e) + "\n Trying again...")
    

    continue_scraping = True
    while continue_scraping:
        try:
            continue_scraping = scrape_next_match(driver, df)
        except Exception as e:
            continue_scraping = False
            print(str(e) + "\n Exporting scraped data as csv. Please start the script again.")
            df.to_csv(file_path)
            break
        while True:
            try:
                expand_all_matchdays(driver, scroll=False)
                break
            except RuntimeError as e:
                print(str(e) + "\n Trying again...")

    driver.quit()


if __name__ == "__main__":
    main()
