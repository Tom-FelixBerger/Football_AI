import pandas as pd
import numpy as np
import re
import time
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

# function to request user input of the league and season to be scraped
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
        except ValueError as e:
            print("Invalid input. Please try again.")
    
    # season input
    while True:
        season = input("Please enter the season of the matches you want to scrape in the following format: YYYY/YY, \nfor example: \"2024/25\".\n")
        if re.match(r"^\d{4}/\d{2}$", season):
            start_year, end_year = map(int, season.split("/"))
            current_year = datetime.now().year
            if start_year <= current_year and end_year == (start_year % 100) + 1:
                break
            else:
                print("Invalid season. The season should not be in the future and should be in the format YYYY/YY.")
        else:
            print("Invalid input. Please enter the season in the format YYYY/YY.")

    # google search query, for example "1. Bundesliga Spiele 2024/25"
    search_url = "https://www.google.com/search?q="+league.replace(" ", "+")+"+Spiele+"+season.replace("/", "+")
    
    return league, season, search_url



def init_driver_and_df(league, season, search_url):

    driver = webdriver.Chrome()
    driver.get(search_url)

    # Accept Cookies
    try:
        cookies_button = WebDriverWait(driver, 3.5).until(EC.element_to_be_clickable((By.CLASS_NAME, "sy4vM")))
        cookies_button.click()
    except TimeoutException as e:
        print("No cookies button found. Continuing without accepting cookies.")

    # Check if URL contains "Weitere Begegnungen" button
    try:
        WebDriverWait(driver, 3.5).until(EC.presence_of_element_located((By.CLASS_NAME, "Z4Cazf")))
    except TimeoutException as e:
        print(f"Error: {str(e)}")
        print("\nFull stack trace:")
        traceback.print_exc()
        raise RuntimeError(f"The search query \"{league} {season} spiele\" did not return the expected results.")

    # if successful read or create the dataframe
    file_path = "../data/"+league.replace(" ", "_")+"_"+season.replace("/", "_")+".csv"
    try:
        df = pd.read_csv(file_path, index_col=0)
    except FileNotFoundError:
        print("This league and season has not been scraped yet. Creating a new dataframe.")
        stats = ["Team", "Goals", "Attempts", "Attempts_On_Target", "Possession", "Passes",
            "Passing_Accuracy", "Fouls", "Yellow_Cards", "Red_Cards", "Offside", "Corners"]
        df = pd.DataFrame(columns=(["Matchday", "Date", "Winner"] + [stat+"_"+team for stat in stats
                                                                        for team in ["Home", "Away"]]))
        df.to_csv(file_path)

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
        WebDriverWait(driver, 3.5).until(EC.presence_of_element_located((By.CLASS_NAME, "Z4Cazf")))
        candidate_buttons = driver.find_elements(By.CLASS_NAME, "Z4Cazf")
        for b in candidate_buttons:
            if b.is_displayed():
                expand_button = b
                break
    except TimeoutException as e:
        print(f"Error: {str(e)}")
        print("\nFull stack trace:")
        traceback.print_exc()
        raise RuntimeError("The \"Weitere Begegnungen\" button is not present.")
    try:
        expand_button.click()
    except Exception:
        print("\nThe \"Weitere Begegnungen\" button is not clickable. \n" +
              "Assuming that all matchdays are already expanded.") # CONTINUE HERE: There is some weird error that causes the driver to crash apparently #####

    try:
        WebDriverWait(driver, 3.5).until(EC.presence_of_element_located((By.CLASS_NAME, "OcbAbf")))
    except TimeoutException as e:
        print(f"Error: {str(e)}")
        print("\nFull stack trace:")
        traceback.print_exc()
        raise RuntimeError("The page did not load the matchdays correctly.")
    
    if scroll:
        # load all matchdays to top and bottom
        actions = ActionChains(driver)
        for idx, first in [(0, True), (-1, False)]:        
            while True:
                try:
                    matchdays = driver.find_elements(By.CLASS_NAME, "OcbAbf")
                    prior_match = matchdays[idx]
                    actions.move_to_element(prior_match).perform()
                    WebDriverWait(driver, 3.5).until(element_has_changed(prior_match, first=first))
                except TimeoutException:
                    break

def scrape_statistics(match, driver):
    
    actions = ActionChains(driver)
    actions.move_to_element(match).perform()
    WebDriverWait(driver,3.5).until(EC.element_to_be_clickable(match))
    match.click()
    time.sleep(1)

    try:
        WebDriverWait(driver, 3.5).until(EC.presence_of_element_located((By.CLASS_NAME, "MzWkAb")))
        statistics = driver.find_elements(By.CLASS_NAME, "MzWkAb")
        scraped_stats = []
        for i in range(10):
            scraped_stats += [w for w in statistics[i].text.split() if w.isdigit()]
    
    except TimeoutException:
        scraped_stats = [np.nan]*20
    
    back_button = driver.find_element(By.CLASS_NAME, "vtLYrb")
    back_button.click()
    
    return scraped_stats

def extract_date_from_text(text):
    if "Heute" in text:
        return datetime.now().date()
    if "Gestern" in text:
        return datetime.now().date() - pd.Timedelta(days=1)
    
    # past years are given as two digits by google
    if d := re.search(r"\d{1,2}\.\d{1,2}\.\d{2}", text):
        year = "20" + d.group().split('.')[2]
    # the current year is not explicitly written out
    else:
        year = datetime.now().year

    # Reconstruct the date string
    if d := re.search(r"\d{1,2}\.\d{1,2}\.", text):
        day, month = d.group().split(".")[0:2]
        return datetime.strptime(f"{day}.{month}.{year}", "%d.%m.%Y").date()
    else:
        raise ValueError("The date could not be extracted from the text.")

# function to find the next match that is not in the data yet and scrape it
def scrape_next_match(driver, df):

    new_match_scraped = False
    try:

        # find and iterate over all matchdays on the page (some "OcbAbf" elements are empty)
        WebDriverWait(driver, 3.5).until(EC.presence_of_element_located((By.CLASS_NAME, "OcbAbf")))
        matchdays = [m for m in driver.find_elements(By.CLASS_NAME, "OcbAbf") if m.find_elements(By.CLASS_NAME, "GVj7ae")]
        for matchday in matchdays:
            matchday_text = matchday.find_element(By.CLASS_NAME, "GVj7ae").text

            # find and iterate over all matches of the matchday (some "KAIX8d" elements are empty)
            matches = [match for match in matchday.find_elements(By.CLASS_NAME, "KAIX8d") if match.text != ""]
            for match in matches:

                # if match is in the past, scrape identifiers of the match and check if it's not already in the dataframe
                date = extract_date_from_text(match.find_element(By.CLASS_NAME, "GOsQPe").text)       
                if date <= datetime.now().date():
                    team_home, team_away = [t.text.split("\n")[1] for t in match.find_elements(By.CLASS_NAME, "L5Kkcd")]
                    if df[(df["Date"]==date)&(df["Team_Home"]==team_home)&(df["Team_Away"]==team_away)].empty:
                        goals_home, goals_away = [t.text.split("\n")[1] for t in match.find_elements(By.CLASS_NAME, "L5Kkcd")]
                        winner = "Draw"
                        if goals_home > goals_away:
                            winner = "Home"
                        elif goals_home < goals_away:
                            winner = "Away"
                        new_row = ([matchday_text, date, winner, team_home, team_away, goals_home, goals_away]
                                    + scrape_statistics(match, driver))
                        df.loc[len(df.index)] = new_row
                        new_match_scraped = True
                        break
            else:
                continue
            break

    except TimeoutException as e:
        print(f"Error: {str(e)}")
        print("\nFull stack trace:")
        traceback.print_exc()
        raise RuntimeError(str(e)+"\nThe page did not load the matchdays correctly.")

    return new_match_scraped
                
def main():
    
    # get user input and initialize the driver and dataframe
    while True:
        try:
            league, season, search_url = get_inputs_from_user()
            driver, df, file_path = init_driver_and_df(league, season, search_url)
            expand_all_matchdays(driver)
            break
        except RuntimeError as e:
            if driver:
                driver.quit()
            print(f"Error: {str(e)}")
            print("\nFull stack trace:")
            traceback.print_exc()
            print("\n Please try again.")
    
    # scrape all matches of the league and season
    continue_scraping = True
    while continue_scraping:
        try:
            continue_scraping = scrape_next_match(driver, df)
            expand_all_matchdays(driver, scroll=False)
        except Exception as e:
            continue_scraping = False
            print(f"Error: {str(e)}")
            print("\nFull stack trace:")
            traceback.print_exc()
            print("Exporting scraped data as csv. Please start the script again.")
            df.to_csv(file_path)

    driver.quit()


if __name__ == "__main__":
    main()


