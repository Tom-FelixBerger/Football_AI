import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from datetime import datetime


def explaining_data(df):
    """Prepare data for model training"""
    features = [col for col in df.columns if not "Targ_Var" in col]
    categorical = ['Team_Home', 'Team_Away']
    cat_features = [f for f in features if f in categorical]
    num_features = [f for f in features if f not in categorical]
    
    # Handle categorical features
    X = pd.get_dummies(df[features], columns=cat_features)
    
    # Scale numerical features if there are any
    if num_features:
        scaler = StandardScaler()
        X[num_features] = scaler.fit_transform(X[num_features])
    
    return X

def main():
    complete_df = pd.read_csv("../data/complete_merged_and_prepared_data.csv", index_col = 0)
    past_df = complete_df.dropna()
    upcoming_df = complete_df[complete_df["Targ_Var_Winner"].isna()]
    X_past = explaining_data(past_df)
    X_upcoming = explaining_data(upcoming_df)
    for col in set(X_past.columns) - set(X_upcoming.columns):
        X_upcoming[col] = 0
    X_upcoming = X_upcoming[X_past.columns]

    # Classification model
    clf = RandomForestClassifier(n_estimators=500, max_depth=30, min_samples_split=10, min_samples_leaf=4, random_state=37)
    clf.fit(X_past, past_df['Targ_Var_Winner'])

    # Regression model
    reg = RandomForestRegressor(n_estimators=500, max_depth = 10, min_samples_split = 10, min_samples_leaf = 4, random_state=37)
    reg.fit(X_past, past_df[['Targ_Var_Difference', "Targ_Var_Goals_Home", "Targ_Var_Goals_Away"]])

    upcoming_df.loc[:, ["Winner_Prediction"]] = clf.predict(X_upcoming)
    upcoming_df.loc[:, ["Difference_Prediction", "Goals_Home_Prediction", "Goals_Away_Prediction"]] = reg.predict(X_upcoming)
    upcoming_df[["Team_Home", "Team_Away", "Winner_Prediction", "Difference_Prediction", "Goals_Home_Prediction", "Goals_Away_Prediction"]].to_excel("../data/prediction"+str(datetime.now().date())+".xlsx")

if __name__ == "__main__":
    main()

