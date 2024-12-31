import pandas as pd
import numpy as np
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

def get_inputs():
    
    # league input
    scrapable_leagues = {1: "1. Bundesliga", 2: "2. Bundesliga", 3: "Premier League", 4: "EFL Championship", 5: "La Liga",
                         6: "Segunda División", 7: "Serie A", 8: "Serie B", 9: "Ligue 1", 10: "Ligue 2",
                         11: "Champions League", 12: "Europa League", 13: "Conference League"}
    while True:
        try:
            league_input = int(input("Please enter the league of the matches you want to scrape by providing the respective number:\n" +
                                     "\n".join([f"{key}: {value}" for key, value in scrapable_leagues.items()]) + "\n"))
            if 1 <= league_input <= 13:
                break
            else:
                print("Please enter a number between 1 and 13.")
        except ValueError:
            print("Invalid input. Please enter a number between 1 and 13.")
    
    # season input
    while True:
        season_input = input("Please enter the season of the matches you want to scrape in the following format: YYYY/YY, \nfor example: \"2024/25\".\n")
        if re.match(r"^\d{4}/\d{2}$", season_input):
            start_year, end_year = map(int, season_input.split('/'))
            current_year = datetime.now().year
            if start_year <= current_year and end_year == (start_year % 100) + 1:
                break
            else:
                print("Invalid season. The season should not be in the future and should be in the format YYYY/YY.")
        else:
            print("Invalid input. Please enter the season in the format YYYY/YY.")
    
    return scrapable_leagues[league_input], season_input


def read_or_create_match_data_csv(file_path):
    try:
        match_data = pd.read_csv(file_path)
    except FileNotFoundError:
        stats = ["Team", "Tore", "Schüsse", "Torschüsse", "Ballbesitz", "Pässe", "Passgenauigkeit", "Fouls", "Gelbe", "Rote", "Abseits", "Ecken"]
        match_data = pd.DataFrame(columns=(["Spieltag", "Datum", "Sieger"] + [stat+"_"+team for stat in stats for team in ["A", "B"]]))
        match_data.to_csv(file_path)
    return match_data

def init_driver_and_df():
    league, season = get_inputs()

    # get URL
    driver = webdriver.Chrome()
    driver.get("https://www.google.com/search?q="+league.replace(" ", "+")+"+spiele+"+season.replace("/", "+"))

    # Accept Cookies
    cookies_button = driver.find_element(By.CLASS_NAME, "sy4vM")
    cookies_button.click()

    # Check if URL contains "Weitere Begegnungen" button
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'Z4Cazf'))
        )
        print("Page is ready to be scraped!")

        # if successful read or create the dataframe and exit while loop
        file_path = "../data/"+league.replace(" ", "_")+"_"+season.replace("/", "_")+".csv"
        df = read_or_create_match_data_csv(file_path)
    except TimeoutException as e:
        driver.quit()
        raise RuntimeError(e+f"The search query \"{league} {season} spiele\" did not return the expected results. Please try again.")

    return driver, df, file_path

def element_has_changed(prior_element, first=True):
    """Return a function that checks if the new element is different from the prior one."""
    def _check(driver):
        matchdays = driver.find_elements(By.CLASS_NAME, "OcbAbf")
        idx = 0 if first else len(matchdays)-1
        return matchdays[idx].text != prior_element.text
    return _check

def expand_all_matchdays(driver, scroll=True):
    ### CONTINUE HERE: Why isn't the element clickable (it seems to be enabled but not displayed) when returning to the page?? ###
    element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'Z4Cazf')))
    element.click()
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'OcbAbf')))
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

def get_stat_values(stat_string):
    words = stat_string.split()
    return [w for w in words if w.isdigit()]

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
    match.click()

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'MzWkAb')))
        statistics = driver.find_elements(By.CLASS_NAME, 'MzWkAb')

        [Schüsse_A, Schüsse_B] = get_stat_values(statistics[0].text)
        [Torschüsse_A, Torschüsse_B] = get_stat_values(statistics[1].text)
        [Ballbesitz_A, Ballbesitz_B] = get_stat_values(statistics[2].text)
        [Pässe_A, Pässe_B] = get_stat_values(statistics[3].text)
        [Passgenauigkeit_A, Passgenauigkeit_B] = get_stat_values(statistics[4].text)
        [Fouls_A, Fouls_B] = get_stat_values(statistics[5].text)
        [Gelbe_A, Gelbe_B] = get_stat_values(statistics[6].text)
        [Rote_A, Rote_B] = get_stat_values(statistics[7].text)
        [Abseits_A, Abseits_B] = get_stat_values(statistics[8].text)
        [Ecken_A, Ecken_B] = get_stat_values(statistics[9].text)
        
        scraped_stats = [Schüsse_A, Schüsse_B, Torschüsse_A, Torschüsse_B, Ballbesitz_A,
                         Ballbesitz_B, Pässe_A, Pässe_B, Passgenauigkeit_A, Passgenauigkeit_B,
                         Fouls_A, Fouls_B, Gelbe_A, Gelbe_B, Rote_A, Rote_B, Abseits_A, Abseits_B,
                         Ecken_A, Ecken_B]
    except TimeoutException:
        scraped_stats = [np.nan]*20
    
    back_button = driver.find_element(By.CLASS_NAME, "vtLYrb")
    back_button.click()
    
    return [Datum, Ergebnis, Team_A, Team_B, Tore_A, Tore_B] + scraped_stats

def scrape_next_match(driver, df):
    matchdays = driver.find_elements(By.CLASS_NAME, 'OcbAbf')
    new_match_scraped = False
    
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
                print(len(new_row))
                print(len(df.columns))
                df.loc[len(df.index)] = new_row
                new_match_scraped = True
                break
        else:
            continue
        break

    return new_match_scraped
                
def main():
    
    driver, df, file_path = init_driver_and_df()

    continue_scraping = True
    while continue_scraping:
        expand_all_matchdays(driver)
        continue_scraping = scrape_next_match(driver, df)

    driver.quit()
    df.to_csv(file_path)


if __name__ == "__main__":
    main()
