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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

# function to request user input of the league and season to be scraped
def get_inputs_from_user():
    
    # league input
    scrapable_leagues = {1: "1. Bundesliga", 2: "2. Bundesliga", 3: "Premier League", 4: "EFL Championship", 5: "La Liga",
                         6: "Segunda División", 7: "Serie A", 8: "Serie B", 9: "Ligue 1", 10: "Ligue 2",
                         11: "Champions League", 12: "Europa League", 13: "Conference League", 14: "Other (Enter league name manually)"}
    while True:
        league_input = input("Please enter the league of the matches you want to scrape by providing the respective number:\n" +
                                     "\n".join([f"{key}: {value}" for key, value in scrapable_leagues.items()]) + "\n")
        
        if not league_input.isdigit():
            print("Input must be an int. Please try again.")
            continue
        league_input = int(league_input)

        if 1 <= league_input <= 13:
            league = scrapable_leagues[league_input]
            break
        elif league_input == 14:
            league = input("Please enter the name of the league you want to scrape.\n")
            break
        else:
            print("The input must be between 1 and 14. Please try again.")
    
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

# clicks the expand button and scroll up and down to expand all matchdays
def expand_all_matchdays(driver):

    # checks if a new element has been loaded while scrolling up or down through the page
    def _check(driver, prior_element, scroll_up):
        matchdays = driver.find_elements(By.CLASS_NAME, "OcbAbf")
        idx = 0 if scroll_up else len(matchdays)-1
        return matchdays[idx].text != prior_element.text

    expand_button = WebDriverWait(driver, 3.5).until(EC.element_to_be_clickable((By.CLASS_NAME, "Z4Cazf")))
    expand_button.click()

    # load all matches by scrolling up and then down through the page
    WebDriverWait(driver, 3.5).until(EC.presence_of_element_located((By.CLASS_NAME, "OcbAbf")))
    actions = ActionChains(driver)
    for idx, scrup in [(0, True), (-1, False)]:        
        while True:
            try:
                matchdays = driver.find_elements(By.CLASS_NAME, "OcbAbf")
                prior_match = matchdays[idx]
                actions.move_to_element(prior_match).perform()
                WebDriverWait(driver, 3.5).until(lambda d: _check(d, prior_match, scroll_up=scrup))
            except TimeoutException:
                break

# returns the date in pandas datetime format from the google date text of football matches
def extract_date_from_text(text):
    if "Heute" in text:
        return datetime.now().date()
    if "Gestern" in text:
        return datetime.now().date() - pd.Timedelta(days=1)
    
    d = re.search(r"\d{1,2}\.\d{1,2}\.", text)
    day, month = d.group().split(".")[0:2]

    # Find out the year, which is either given as two digits by google, ...
    if y := re.search(r"\d{1,2}\.\d{1,2}\.\d{2}", text):
        year = "20" + y.group().split('.')[2]
    # or not explicitly written out if it is recent. In that case it is either the current year or the last year.
    else:
        current_year = datetime.now().year 
        if datetime.strptime(f"{day}.{month}.{str(current_year)}", "%d.%m.%Y").date() <= datetime.now().date():
            year = str(current_year)
        else:
            year = str(current_year-1)

    # Reconstruct the date string
    return f"{day}.{month}.{year}"

# function to find the next match that is not in the mathes_df dataframe and add it
def find_all_scrapable_matches(driver, stats_df):
        
        # create a dataframe to store the scrapable matches
        matches_df = pd.DataFrame(columns=["Date", "Matchday", "Team_Home", "Team_Away",
                                           "Goals_Home", "Goals_Away"])

        # find and iterate over all matchdays on the page
        WebDriverWait(driver, 3.5).until(EC.presence_of_element_located((By.CLASS_NAME, "OcbAbf")))
        matchdays = driver.find_elements(By.CLASS_NAME, "OcbAbf")
        matchday_text = "No matchday text found"
        for matchday in matchdays:
            try:
                matchday_text = matchday.find_element(By.CLASS_NAME, "GVj7ae").text
            except NoSuchElementException:
                pass

            # find and iterate over all matches of the matchday (some "KAIX8d" elements are empty)
            matches = [match for match in matchday.find_elements(By.CLASS_NAME, "KAIX8d") if match.text != ""]
            for match in matches:

                # if the match has a result, scrape identifiers of the match and check if it's not already in the dataframe
                try:
                    result_line = match.find_element(By.CLASS_NAME, "imspo_mt__tt-w")
                    result_line.find_element(By.CLASS_NAME, "imspo_mt__t-sc")
                except NoSuchElementException:
                    continue

                date = extract_date_from_text(match.find_element(By.CLASS_NAME, "GOsQPe").text)  
                team_home, team_away = [t.text.split("\n")[1] for t in match.find_elements(By.CLASS_NAME, "L5Kkcd")]
                goals_home, goals_away = [t.text.split("\n")[0] for t in match.find_elements(By.CLASS_NAME, "L5Kkcd")]

                if stats_df[(stats_df["Date"]==date)&(stats_df["Team_Home"]==team_home)&(stats_df["Team_Away"]==team_away)].empty:
                    matches_df.loc[len(matches_df.index)] = [date, matchday_text, team_home, team_away, goals_home, goals_away]
        
        return matches_df

# function that does nothing or raises a KeyboardInterrupt if the user chooses to abort.
def let_user_fix_page_state_manually(problem_message):
    print(problem_message)
    while True:
        choice = input("1: Problem was solved manually. Please continue.\n" +
                        "2: Problem cannot be solved manually. Continue anyway.\n" +
                        "3: Abort webscraping and save data to csv file.\n")
        if not choice.isdigit():
            print("Invalid input. Please enter 1 2, or 3.")
        choice = int(choice)
        
        if not choice in {1, 2, 3}:
            print("Invalid input. Please enter 1, 2, or 3.")
        if choice == 1:
            print("Continuing...")
            return True
        if choice == 2:
            print("Continuing...")
            return False
        if choice == 3:
            raise KeyboardInterrupt("Aborting the webscraping due to user choice.")

def init_driver_and_df(league, season, search_url):

    # Read existing or create csv file for the match statistics to be scraped
    file_path = "../data/"+league.replace(" ", "_")+"_"+season.replace("/", "_")+".csv"
    try:
        stats_df = pd.read_csv(file_path, index_col=0)
    except FileNotFoundError:
        print("This league and season has not been scraped yet. Creating a new dataframe.")
        stats = ["Team", "Goals", "Attempts", "Attempts_On_Target", "Possession", "Passes",
            "Passing_Accuracy", "Fouls", "Yellow_Cards", "Red_Cards", "Offside", "Corners"]
        stats_df = pd.DataFrame(columns=(["Date", "Matchday"] + [stat+"_"+team for stat in stats
                                                                        for team in ["Home", "Away"]]))
        stats_df.to_csv(file_path)

    
    # Initialize driver and accept Cookies
    driver = webdriver.Chrome()
    driver.get(search_url)
    while True:
        try:
            cookies_button = WebDriverWait(driver, 3.5).until(EC.element_to_be_clickable((By.CLASS_NAME, "sy4vM")))
            cookies_button.click()
            break
        except TimeoutException:
            print("An error occured. \nFull stack trace:")
            traceback.print_exc()
            if let_user_fix_page_state_manually("Can you fix the page state manually? I'm expecting to click Google's accept cookies button next."):
                driver.get(search_url)
            else:
                break
        
    # Expand all matches to be scraped and save them in a dataframe
    while True:
        try:
            expand_all_matchdays(driver)
            matches_df = find_all_scrapable_matches(driver, stats_df)
            break
        except TimeoutException:
            print("An error occured. \nFull stack trace:")
            traceback.print_exc()
            if let_user_fix_page_state_manually("Can you fix the page state manually? I'm expecting to click the \"Weitere Begegnungen\" button next."):
                continue
            else:
                raise KeyboardInterrupt("Cannot continue at this state. Aborting the webscraping")

    print(f"Driver and DataFrames are ready. {len(matches_df)} scrapable matches were found.")
    return driver, stats_df, matches_df, file_path

def scrape_statistics(driver):

    # click on the "Mehr zu diesem Spiel" button to show the statistics
    show_more_button = WebDriverWait(driver,3.5).until(EC.element_to_be_clickable((By.CLASS_NAME, "U0faLd")))
    show_more_button.click()

    # if match has statistics, scrape them, otherwise insert NaNs
    try:
        WebDriverWait(driver, 3.5).until(EC.presence_of_element_located((By.CLASS_NAME, "MzWkAb")))
        statistics = driver.find_elements(By.CLASS_NAME, "MzWkAb")
        scraped_stats = [w for i in range(10) for w in statistics[i].text.split() if w.isdigit()]
    except TimeoutException:
        scraped_stats = [np.nan]*20
    
    return scraped_stats

# function to scrape all matches from matches_df that are not in stats_df
def scrape_all_matches(driver, matches_df, stats_df, league):
    
    # iterate over all scrapable matches and search the statistics of those that are not in the stats_df
    for idx, row in matches_df.iterrows():
        print(f"Attempting to scrape match {idx + 1} of {len(matches_df)}: {row['Team_Home']} vs {row['Team_Away']} on {row['Date']}.")
        if stats_df[(stats_df["Date"]==row["Date"])&(stats_df["Team_Home"]==row["Team_Home"])&(stats_df["Team_Away"]==row["Team_Away"])].empty:
            match_url = ("https://www.google.com/search?q="+row["Team_Home"]+" vs. "+row["Team_Away"]+" "+row["Date"]+" "+league).replace(" ", "+")
            driver.get(match_url)
            while True:
                try:
                    match_stats = scrape_statistics(driver)
                    new_row = ([row["Date"], row["Matchday"], row["Team_Home"], row["Team_Away"], row["Goals_Home"], row["Goals_Away"]] + match_stats)
                    stats_df.loc[len(stats_df.index)] = new_row
                    print(f"Scraping was successful!")
                    break
                except TimeoutException:
                    print("An error occured. \nFull stack trace:")
                    traceback.print_exc()
                    if let_user_fix_page_state_manually("Can you fix the page state manually? I'm expecting to click the \"Mehr zu diesem Spiel\" button next."):
                        continue
                    else:
                        print("The match could not be scraped and was thus skipped.")
        else:
            print("The match is already in the DataFrame.")

def main():
    
    # get user input
    league, season, search_url = get_inputs_from_user()

    #  initialize the driver and dataframe and scrape all matches from matches df that are not in stats_df, then export to csv
    try:
        driver, stats_df, matches_df, file_path = init_driver_and_df(league, season, search_url)
    except KeyboardInterrupt:
        pass
    else:                 
        try:
            scrape_all_matches(driver, matches_df, stats_df, league)
        except KeyboardInterrupt:
            driver.quit()
        while True:
            try:
                print("Exporting scraped data to csv.")
                stats_df.to_csv(file_path)
                break
            except PermissionError:
                input("Permission to export csv denied. Please hit Enter when you closed the file.")

if __name__ == "__main__":
    main()

