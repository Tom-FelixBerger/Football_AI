import pandas as pd
import os
import re

def concat_all_data():
    df_list_dict = {"matches": [], "odds": [], "statistics": []}
    for file in os.listdir("../data"):
        file = "../data/"+file
        for df_kind in df_list_dict.keys():
            if df_kind in file:
                df_list_dict[df_kind].append(pd.read_csv(file, index_col=0))

    matches_df = pd.concat(df_list_dict["matches"])
    odds_df = pd.concat(df_list_dict["odds"])
    stats_df = pd.concat(df_list_dict["statistics"])

    return matches_df, odds_df, stats_df

def translate_team_names(dfs):
    def replace_in_text(text, translation_dict):
        for original, translated in translation_dict.items():
            text = re.sub(original, translated, text)
        return text
    
    def replace_in_df(df):
        for col in df.columns:
            df[col] = df[col].apply(lambda x: replace_in_text(x, translation_dict) if isinstance(x, str) else x)
        df.index = df.index.map(lambda x: replace_in_text(str(x), translation_dict))
        return df
    
    translation_dict = {
        "Bayern": "Bayern Munich",
        "VfB Stuttgart": "Stuttgart",
        "Eintracht Frankfurt": "Eintracht Frankfurt",  
        "Union Berlin": "Union Berlin",  
        "Werder Bremen": "Werder Bremen",  
        "Köln": "FC Koln",
        "Dortmund": "Dortmund",  
        "RB Leipzig": "RB Leipzig",  
        "Wolfsburg": "Wolfsburg",  
        "Hertha": "Hertha Berlin",
        "Leverkusen": "Bayer Leverkusen",
        "Augsburg": "Augsburg",  
        "Mönchengladbach": "B. Monchengladbach",
        "Arminia": "Arminia Bielefeld",
        "Mainz": "Mainz",  
        "Schalke": "Schalke",  
        "Hoffenheim": "Hoffenheim",  
        "Freiburg": "Freiburg",  
        "Bochum": "Bochum",  
        "Greuther Fürth": "Greuther Furth",
        "Heidenheim": "Heidenheim",  
        "Darmstadt 98": "Darmstadt",
        "St. Pauli": "St. Pauli",  
        "Holstein": "Holstein Kiel"
    }

    return [replace_in_df(df) for df in dfs]    

def join_and_sort(matches_df, odds_df, stats_df):
    odds_df = odds_df.drop(["Date", "Team_Home", "Team_Away", "Goals_Home", "Goals_Away"], axis=1)
    complete_df = matches_df.join(odds_df).join(stats_df)
    complete_df["Date"] = pd.to_datetime(complete_df["Date"], format="%d.%m.%Y")
    complete_df = complete_df.sort_values(by="Date")
    return complete_df
    

def drop_or_impute_missing_values(df):
    for event in ["Odds_Home", "Odds_Draw", "Odds_Away"]:
        impute_list = [col for col in df.columns if event in col]
        df[impute_list] = df.apply(lambda row: row[impute_list].astype(float).fillna(row[event+"_Average"]), axis=1)
    df = df.dropna()
    return df

def add_wins_and_rolling_stats(df):
    df["Points_Home"] = df.apply(lambda x: 3 if x["Goals_Home"]>x["Goals_Away"] else (0 if x["Goals_Home"]<x["Goals_Away"] else 1), axis=1)
    df["Points_Away"] = df.apply(lambda x: 3 if x["Goals_Home"]<x["Goals_Away"] else (0 if x["Goals_Home"]>x["Goals_Away"] else 1), axis=1)
    
    all_teams = pd.unique(df["Team_Home"])
    for col in [c for c in df.columns if c not in ["Date", "League", "Matchday", "Team_Home", "Team_Away"]]:
        if "Home" in col:
            for team in all_teams:
                sub_df = df[df["Team_Home"]==team]
                df.loc[df["Team_Home"] == team, "Rolling_" + col] = sub_df[col].rolling(window=3, closed="left").mean()
        elif "Away" in col:
            for team in all_teams:
                sub_df = df[df["Team_Away"]==team]
                df.loc[df["Team_Away"] == team, "Rolling_" + col] = sub_df[col].rolling(window=3, closed="left").mean()
    return df.dropna()

def main():
    matches_df, odds_df, stats_df = concat_all_data()
    matches_df, stats_df = translate_team_names([matches_df, stats_df])
    complete_df = join_and_sort(matches_df, odds_df, stats_df)
    
    complete_df = drop_or_impute_missing_values(complete_df)
    complete_df = add_wins_and_rolling_stats(complete_df)
    complete_df.to_csv("../data/complete_merged_and_prepared_data.csv")

if __name__ == "__main__":
    main()


pd.read_csv("../data/complete_merged_and_prepared_data.csv", index_col = 0)