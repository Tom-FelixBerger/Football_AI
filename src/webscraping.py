import pandas as pd
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

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
        match_data = pd.DataFrame(columns=(["Wettbewerb", "Spieltag", "Datum", "Sieger"] + [stat+"_"+team for stat in stats for team in ["A", "B"]]))
        match_data.to_csv(file_path)
    return match_data

def init_driver_and_df():
    while True:
        league, season = get_inputs()

        # check if the URL contains "Weitere Begegnungen" button
        driver = webdriver.Chrome()
        driver.get("https://www.google.com/search?q="+league.replace(" ", "+")+"+spiele+"+season.replace("/", "+"))
        try:
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'Z4Cazf'))
            )
            print("Page is ready to be scraped!")

            # if successful read or create the dataframe and exit while loop
            df = read_or_create_match_data_csv("../data/"+league.replace(" ", "_")+"_"+season.replace("/", "_")+".csv")
            break
        except TimeoutException:
            print(f"The search query \"{league} {season} spiele\" did not return the expected results. Please try again.")
            driver.quit()

    return driver, df
    
def expand_all_matches(driver):
    pass

def main():
    
    driver, df = init_driver_and_df()

    expand_all_matches(driver)


if __name__ == "__main__":
    main()
