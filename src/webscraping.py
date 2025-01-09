'''
This script can be used to webscrape the google statistics of any football league and the corresponding betting odds from oddsportal.com.
Sometimes manual user inputs will be required (to select a league to be scraped, or to solve a Captcha while scraping.)
'''

import pandas as pd
import numpy as np
import re
import traceback
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

# function to request user input of the league and season to be scraped
def get_inputs_from_user():
    
    # league input
    scrapable_leagues = {1: "1. Bundesliga", 2: "2. Bundesliga", 3: "Premier League", 4: "EFL Championship", 5: "La Liga",
                         6: "Segunda División", 7: "Serie A", 8: "Serie B", 9: "Ligue 1", 10: "Ligue 2",
                         11: "Champions League", 12: "Europa League", 13: "Conference League"}
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
        else:
            print("The input must be between 1 and 13. Please try again.")
    
    # season input
    scrapable_seasons = {1: "2021/22", 2: "2022/23", 3: "2023/24", 4: "2024/25", 5: "Upcoming Matches"}
    while True:
        season_input = input("Please enter the season of the matches you want to scrape by providing the respective number:\n" +
                                     "\n".join([f"{key}: {value}" for key, value in scrapable_seasons.items()]) + "\n")
        
        if not season_input.isdigit():
            print("Input must be an int. Please try again.")
            continue
        season_input = int(season_input)

        if 1 <= season_input <= 5:
            season = scrapable_seasons[season_input]
            break
        else:
            print("The input must be between 1 and 5. Please try again.")

    # google search query and file path
    google_url = "https://www.google.com/search?q="+league.replace(" ", "+")+"+Spiele+"+season.replace("/", "+")
    google_file_path = "../data/"+league.replace(" ", "_").replace(".","")+"_"+season.replace("/", "_")+"_google_statistics.csv"

    # oddsportal page and file path
    oddsportal_pages = {1: "germany/bundesliga",
                        2: "germany/2-bundesliga",
                        3: "england/premier-league",
                        4: "england/championship",
                        5: "spain/laliga",
                        6: "spain/laliga2",
                        7: "italy/serie-a",
                        8: "italy/serie-b",
                        9: "france/ligue-1",
                        10: "france/ligue-2",
                        11: "europe/champions-league",
                        12: "europe/europa-league",
                        13: "europe/conference-league"}
    # if we are scraping the ongoing season, we need a different url than for past seasons
    current_year = datetime.now().year
    current_month = datetime.now().month
    if (season[0:4] == str(current_year)) or ((season[0:4] == str(current_year-1)) and current_month <= 5):
        odds_url = "https://www.oddsportal.com/football/"+oddsportal_pages[league_input]+"/results/"
    elif season == "Upcoming Matches":
        odds_url = "https://www.oddsportal.com/football/"+oddsportal_pages[league_input]
    else:
        odds_url = "https://www.oddsportal.com/football/"+oddsportal_pages[league_input]+"-"+season.replace("/", "-20")+"/results/"
    odds_file_path = "../data/"+league.replace(" ", "_").replace(".","")+"_"+season.replace("/", "_")+"_oddsportal_odds.csv"

    # file path for all matches
    matches_file_path = "../data/"+league.replace(" ", "_").replace(".","")+"_"+season.replace("/", "_")+"_matches.csv"
    
    return league, season, google_url, odds_url, google_file_path, matches_file_path, odds_file_path

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
def extract_date_from_google_text(text):
    if ("Heute" in text) or ("Gestern" in text):
        if "Heute" in text:
            date = datetime.now().date()
        else:
            date = datetime.now().date() - pd.Timedelta(days=1)
        day = date.day
        month = date.month
        year = date.year
    else:
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

# function to find all scrapable matches that are not in the mathes_df dataframe and add them
def find_all_scrapable_matches(driver, matches_df, league):

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

                date = extract_date_from_google_text(match.find_element(By.CLASS_NAME, "GOsQPe").text)  
                team_home, team_away = [t.text.split("\n")[1] for t in match.find_elements(By.CLASS_NAME, "L5Kkcd")]
                goals_home, goals_away = [t.text.split("\n")[0] for t in match.find_elements(By.CLASS_NAME, "L5Kkcd")]
                idx = "_".join([date, team_home, team_away, goals_home, goals_away])

                if not idx in matches_df.index:
                    matches_df.loc[idx] = [date, league, matchday_text, team_home, team_away, goals_home, goals_away]
        
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

def init_google_stats_scraping(google_url, google_file_path, matches_file_path, league):
    
    # Read existing or create csv files for the matches and match statistics to be scraped
    try:
        google_stats_df = pd.read_csv(google_file_path, index_col=0)
        matches_df = pd.read_csv(matches_file_path, index_col=0)
    except FileNotFoundError:
        print("This league and season has not been scraped yet. Creating a new dataframe.")
        stats = ["Attempts", "Attempts_On_Target", "Possession", "Passes",
            "Passing_Accuracy", "Fouls", "Yellow_Cards", "Red_Cards", "Offside", "Corners"]
        google_stats_df = pd.DataFrame(columns=[stat+"_"+team for stat in stats for team in ["Home", "Away"]])
        google_stats_df.to_csv(google_file_path)
        matches_df = pd.DataFrame(columns=["Date", "League", "Matchday", "Team_Home", "Team_Away", "Goals_Home", "Goals_Away"])
        matches_df.to_csv(matches_file_path)

    # Initialize driver and accept Cookies
    driver = webdriver.Chrome()
    driver.get(google_url)
    while True:
        try:
            cookies_button = WebDriverWait(driver, 3.5).until(EC.element_to_be_clickable((By.CLASS_NAME, "sy4vM")))
            cookies_button.click()
            break
        except TimeoutException:
            print("An error occured. \nFull stack trace:")
            traceback.print_exc()
            if let_user_fix_page_state_manually("Can you fix the page state manually? I'm expecting to click Google's accept cookies button next."):
                driver.get(google_url)
            else:
                break
        
    # Expand all matches to be scraped and save them in a dataframe
    while True:
        try:
            expand_all_matchdays(driver)
            find_all_scrapable_matches(driver, matches_df, league)
            break
        except TimeoutException:
            print("An error occured. \nFull stack trace:")
            traceback.print_exc()
            if let_user_fix_page_state_manually("Can you fix the page state manually? I'm expecting to click the \"Weitere Begegnungen\" button next."):
                continue
            else:
                raise KeyboardInterrupt("Cannot continue at this state. Aborting the webscraping")

    print(f"Driver and DataFrames are ready. {len(matches_df)} scrapable matches were found.")
    return driver, google_stats_df, matches_df

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

# function to scrape all matches from matches_df that are not in google_stats_df
def scrape_all_google_stats(driver, matches_df, google_stats_df):
    
    # iterate over all scrapable matches and search the statistics of those that are not in the google_stats_df
    progress_counter = 1
    for idx, row in matches_df.iterrows():
        print(f"Attempting to scrape match {progress_counter} of {len(matches_df)}: {row['Team_Home']} vs {row['Team_Away']} on {row['Date']}.")
        progress_counter += 1
        if not idx in google_stats_df.index:
            match_url = ("https://www.google.com/search?q="+row["Team_Home"]+" vs. "+row["Team_Away"]+" "+row["Date"]+" "+row["League"]).replace(" ", "+")
            driver.get(match_url)
            while True:
                try:
                    match_stats = scrape_statistics(driver)
                    google_stats_df.loc[idx] = match_stats
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

# function that attempts to export and waits for user to grant permissions in case they're denied
def wait_for_permission_and_export(df, file_path):
        while True:
            try:
                print(f"Exporting {file_path}.")
                df.to_csv(file_path)
                break
            except PermissionError:
                input("Cannot access the file. Please hit Enter when you closed the file.")

# initialize dataframe and driver to scrape betting odds
def init_oddsportal_scraping(odds_url, odds_file_path, season):
    if season != "Upcoming Matches":
        # Read existing or create csv files for the matches and match statistics to be scraped
        try:
            odds_df = pd.read_csv(odds_file_path, index_col=0)
        except FileNotFoundError:
            print("The odds for this league and season have not been scraped yet. Creating a new dataframe.")
            odds_cols = ["Odds_"+event+bookie for bookie in ["Average", "Bet365", "bet-at-home", "Betano", "Bwin"] for event in ["Home_", "Draw_", "Away_"]]
            odds_df = pd.DataFrame(columns=["Date", "Team_Home", "Team_Away", "Goals_Home", "Goals_Away"]+odds_cols+["Upcoming"])
            odds_df.to_csv(odds_file_path)
    else:
        odds_cols = ["Odds_"+event+bookie for bookie in ["Average", "Bet365", "bet-at-home", "Betano", "Bwin"] for event in ["Home_", "Draw_", "Away_"]]
        odds_df = pd.DataFrame(columns=["Date", "Team_Home", "Team_Away", "Goals_Home", "Goals_Away"]+odds_cols+["Upcoming"])
        odds_df.to_csv(odds_file_path)

    # Initialize driver and accept Cookies
    driver = webdriver.Chrome()
    driver.get(odds_url)
    cookies_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[id='onetrust-accept-btn-handler']")))
    cookies_button.click()

    
    return driver, odds_df

def extract_oddsportal_date(text, last_date):
    if any([day in text for day in ["Today", "Yesterday", "Tomorrow"]]):
        if "Today" in text:
            date = datetime.now().date()
        elif "Yesterday" in text:
            date = datetime.now().date() - pd.Timedelta(days=1)
        elif "Tomorrow" in text:
            date = datetime.now().date() + pd.Timedelta(days=1)
        day = date.day
        month = date.month
        year = date.year
    else:
        d = re.search(r"\d{2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s\d{4}", text)
        if d:
            date_str = d.group()
            day = int(date_str[:2])
            month = datetime.strptime(date_str[3:6], '%b').month
            year = int(date_str[-4:])
        else:
            return last_date
    return f"{day}.{month}.{year}"

def extract_teams_and_goals(text, season):
    infos = text.split("\n")
    if season != "Upcoming Matches":
        if not "pen." in text:
            return [infos[i] for i in [-9, -5, -8, -6]]
        else:
            return [infos[i-1] for i in [-9, -5, -8, -6]]
    else:
        return [infos[-7], infos[-5], None, None]


def scrape_match_odds(driver, match_link):
    original_window = driver.current_window_handle
    ActionChains(driver)\
        .key_down(Keys.CONTROL)\
        .click(match_link)\
        .key_up(Keys.CONTROL)\
        .perform()

    
    # Wait for new window and switch to it
    WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
    new_window = [window for window in driver.window_handles if window != original_window][0]
    driver.switch_to.window(new_window)
    bookies = ["Average", "Bet365", "bet-at-home", "Betano", "Bwin"]
    odds_dict = {key: None for key in [event+bookie for bookie in bookies for event in ["Home_", "Draw_", "Away_"]]}
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".flex.text-xs.h-9.border-black-borders")))
        bookie_infos = driver.find_elements(By.CSS_SELECTOR, ".flex.text-xs.h-9.border-black-borders")
        for info in [b.text for b in bookie_infos]:
            for bookie in bookies:
                if bookie in info:
                    odds_dict["Home_"+bookie] = info.split("\n")[-4]
                    odds_dict["Draw_"+bookie] = info.split("\n")[-3]
                    odds_dict["Away_"+bookie] = info.split("\n")[-2]

    finally:
        # Close new tab and switch back
        driver.close()
        driver.switch_to.window(original_window)
        return odds_dict

def let_odds_page_load(driver):
    # function to check whether last element has changed
    def _check(driver, prior_last):
        new_last = driver.find_elements(By.CLASS_NAME, "eventRow")[-1]
        return new_last.text != prior_last.text

    driver.refresh()
    while True:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "eventRow")))
        last_row = driver.find_elements(By.CLASS_NAME, "eventRow")[-1]
        actions = ActionChains(driver)
        actions.move_to_element(last_row).perform()
        try:
            WebDriverWait(driver, 10).until(lambda d: _check(driver, last_row))
        except TimeoutException:
            break


def scrape_all_odds(driver, odds_url, odds_df, season):
    if season != "Upcoming Matches":
        upcoming = False
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "pagination-link")))
        number_pages = len(driver.find_elements(By.CLASS_NAME, "pagination-link"))
        subpages = [odds_url+"/#/page/"+str(i)+"/" for i in range(1,number_pages)]
    else:
        upcoming = True
        subpages = [odds_url]

    for page in subpages:
        driver.get(page)
        let_odds_page_load(driver)

        date = extract_oddsportal_date(driver.find_element(By.CLASS_NAME, "eventRow").text, None)
        all_events = driver.find_elements(By.CLASS_NAME, "eventRow")
        progress_counter = 0
        for event_row in all_events:
            progress_counter += 1
            event_text = event_row.text
            date = extract_oddsportal_date(event_text, date)
            team_home, team_away, goals_home, goals_away = extract_teams_and_goals(event_text, season)
            idx = "_".join([date, team_home, team_away, str(goals_home), str(goals_away)])
            print(f"Attempting to scrape odds for match {progress_counter} of {len(all_events)} on {page[-7:-1].replace("/", " ")} of {len(subpages)}: {team_home} vs. {team_away} on {date}")
            if idx not in odds_df.index:
                match_link = event_row.find_element(By.CLASS_NAME, "group")
                odds_dict = scrape_match_odds(driver, match_link)
                odds_df.loc[idx] = ([date, team_home, team_away, goals_home, goals_away] + [odds_dict[event+bookie]
                                for bookie in ["Average", "Bet365", "bet-at-home", "Betano", "Bwin"] for event in ["Home_", "Draw_", "Away_"]]
                                + [upcoming])
                print("Scraping was successful!")
            else:
                print("Match odds are already in the Dataframe.")

def main():
    
    # get user input
    league, season, google_url, odds_url, google_file_path, matches_file_path, odds_file_path = get_inputs_from_user()

    if season != "Upcoming Matches":
        #  initialize the driver and dataframes for the google match statistics
        try:
            driver, google_stats_df, matches_df = init_google_stats_scraping(google_url, google_file_path, matches_file_path, league)
            wait_for_permission_and_export(matches_df, matches_file_path)
        except KeyboardInterrupt:
            print("Ending the Google statistics scraping...")
        else:
            # scrape all google match statistics           
            try:
                scrape_all_google_stats(driver, matches_df, google_stats_df)
                driver.quit()
            except KeyboardInterrupt:
                driver.quit()
            wait_for_permission_and_export(google_stats_df, google_file_path)
    
    #  initialize the driver and dataframes for the oddsportal historical odds and scrape all odds that weren't previously scraped.
    try:
        driver, odds_df = init_oddsportal_scraping(odds_url, odds_file_path, season)
    except KeyboardInterrupt:
        print("Ending the Webscraping...")
    else:
        # scrape all oddsportal betting odds      
        try:
            scrape_all_odds(driver, odds_url, odds_df, season)
            driver.quit()
        except KeyboardInterrupt:
            driver.quit()
        wait_for_permission_and_export(odds_df, odds_file_path)

if __name__ == "__main__":
    main()

import os
for odds_file in [f for f in os.listdir("../data/") if "odds" in f]:
    df = pd.read_csv("../data/"+odds_file, index_col = 0)
    if "Upcoming" in odds_file:
        df["Upcoming"] = True
    else:
        df["Upcoming"] = False
    df.to_csv(odds_file)