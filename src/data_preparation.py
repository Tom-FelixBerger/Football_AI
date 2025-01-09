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
    odds_df = odds_df.copy()
    odds_df = odds_df.drop(["Date", "Team_Home", "Team_Away", "Goals_Home", "Goals_Away", "Upcoming"], axis=1)
    complete_df = matches_df.join(odds_df).join(stats_df)
    complete_df["Date"] = pd.to_datetime(complete_df["Date"], format="%d.%m.%Y")
    complete_df = complete_df.sort_values(by="Date")
    return complete_df
    

def impute_missing_odds(df):
    for event in ["Odds_Home", "Odds_Draw", "Odds_Away"]:
        impute_list = [col for col in df.columns if event in col]
        df[impute_list] = df.apply(lambda row: row[impute_list].astype(float).fillna(row[event+"_Average"]), axis=1)
    return df

def add_rolling_stats(df):

    all_teams = pd.unique(df["Team_Home"])
    for col in [c for c in df.columns if c not in ["Date", "League", "Matchday", "Team_Home",
                                                   "Team_Away", "Upcoming", "Targ_Var_Goals_Home", "Targ_Var_Goals_Away"]]:
        if "Home" in col:
            for team in all_teams:
                sub_df = df[df["Team_Home"]==team]
                df.loc[df["Team_Home"] == team, "Rolling_" + col] = sub_df[col].rolling(window=3, closed="left").mean()
        elif "Away" in col:
            for team in all_teams:
                sub_df = df[df["Team_Away"]==team]
                df.loc[df["Team_Away"] == team, "Rolling_" + col] = sub_df[col].rolling(window=3, closed="left").mean()
    
    return df

def add_target_variables_and_wins(df):
    def _winner(row):
        diff = row["Targ_Var_Difference"]
        return "Home" if diff > 0 else ("Draw" if diff == 0 else "Away")
    
    df["Targ_Var_Difference"] = df["Goals_Home"] - df["Goals_Away"]
    df["Targ_Var_Winner"] = df.apply(_winner, axis = 1)
    df["Targ_Var_Goals_Home"] = df["Goals_Home"].copy()
    df["Targ_Var_Goals_Away"] = df["Goals_Away"].copy()
    df["Points_Home"] = df.apply(lambda x: 3 if x["Goals_Home"]>x["Goals_Away"] else (0 if x["Goals_Home"]<x["Goals_Away"] else 1), axis=1)
    df["Points_Away"] = df.apply(lambda x: 3 if x["Goals_Home"]<x["Goals_Away"] else (0 if x["Goals_Home"]>x["Goals_Away"] else 1), axis=1)
    
    return df

def drop_unwanted_cols(df):
    legitimate_cols = (["Team_Home", "Team_Away"] + 
                       [col for col in df.columns if any([s in col for s in ["Rolling", "Odds", "Targ_Var"]])])
    return df[legitimate_cols]

def main():
    matches_df, odds_df, stats_df = concat_all_data()
    matches_df, stats_df = translate_team_names([matches_df, stats_df])

    complete_df = join_and_sort(matches_df, odds_df, stats_df)
    complete_df = impute_missing_odds(complete_df)
    complete_df = complete_df.dropna()
    complete_df = add_target_variables_and_wins(complete_df)
    
    upcoming_df = odds_df[odds_df["Upcoming"]].copy()
    upcoming_df = impute_missing_odds(upcoming_df)
    complete_df = pd.concat([complete_df, upcoming_df.drop("Upcoming", axis=1)])

    complete_df = add_rolling_stats(complete_df)
    complete_df = drop_unwanted_cols(complete_df)
    complete_df = complete_df.dropna(subset=[col for col in complete_df.columns if "Targ_Var" not in col])
    complete_df.to_csv("../data/complete_merged_and_prepared_data.csv")

if __name__ == "__main__":
    main()