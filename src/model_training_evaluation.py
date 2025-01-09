import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score, mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns

def prepare_feature_sets(df):
    """Create different feature sets for evaluation"""
    basic_features = ['Team_Home', 'Team_Away', 'Odds_Home_Average', 'Odds_Draw_Average', 'Odds_Away_Average']
    odds_features = ['Team_Home', 'Team_Away'] + [col for col in df.columns if "Odds" in col]
    rolling_features = ['Team_Home', 'Team_Away'] + [col for col in df.columns if "Rolling" in col]    
    all_features = [col for col in df.columns if not col in [
        'Date', 'Targ_Var_Winner', 'Targ_Var_Difference',
        "Points_Home", "Points_Away", 'Goals_Home', 'Goals_Away'
    ]]
    
    return {
        'basic': basic_features,
        'odds': odds_features,
        'rolling_form': rolling_features,
        'all_features': all_features
    }

def chronological_split(df):
    """Split data chronologically into train, validation, and test sets"""
    df = df.sort_values('Date')
    train_size = int(0.6 * len(df))
    val_size = int(0.2 * len(df))
    
    train = df.iloc[:train_size]
    val = df.iloc[train_size:train_size + val_size]
    test = df.iloc[train_size + val_size:]
    
    return train, val, test

def prepare_data(df, features):
    """Prepare data for model training"""
    categorical = ['Team_Home', 'Team_Away', "League", "Matchday"]
    cat_features = [f for f in features if f in categorical]
    num_features = [f for f in features if f not in categorical]
    
    # Handle categorical features
    X = pd.get_dummies(df[features], columns=cat_features)
    
    # Scale numerical features if there are any
    if num_features:
        scaler = StandardScaler()
        X[num_features] = scaler.fit_transform(X[num_features])
    
    return X

def train_and_evaluate_models(df, param_grid):
    """Train and evaluate models with different parameters and feature sets"""
    train, val, test = chronological_split(df)
    feature_sets = prepare_feature_sets(df)
    results = []
    
    for features_name, features in feature_sets.items():
        print(f"Processing feature set: {features_name}")
        X_train = prepare_data(train, features)
        X_val = prepare_data(val, features)
        X_test = prepare_data(test, features)
        
        # Ensure consistent columns
        for col in set(X_train.columns) - set(X_val.columns):
            X_val[col] = 0
        for col in set(X_train.columns) - set(X_test.columns):
            X_test[col] = 0
            
        X_val = X_val[X_train.columns]
        X_test = X_test[X_train.columns]
        
        for params in param_grid:
            print(f"Training with params: {params}")
            
            # Classification model
            clf = RandomForestClassifier(**params, random_state=42)
            clf.fit(X_train, train['Targ_Var_Winner'])
            
            train_acc = accuracy_score(train['Targ_Var_Winner'], clf.predict(X_train))
            val_acc = accuracy_score(val['Targ_Var_Winner'], clf.predict(X_val))
            train_f1 = f1_score(train['Targ_Var_Winner'], clf.predict(X_train), average='weighted')
            val_f1 = f1_score(val['Targ_Var_Winner'], clf.predict(X_val), average='weighted')
            
            # Regression model
            reg = RandomForestRegressor(**params, random_state=42)
            reg.fit(X_train, train['Targ_Var_Difference'])
            
            train_mse = mean_squared_error(train['Targ_Var_Difference'], reg.predict(X_train))
            val_mse = mean_squared_error(val['Targ_Var_Difference'], reg.predict(X_val))
            train_r2 = r2_score(train['Targ_Var_Difference'], reg.predict(X_train))
            val_r2 = r2_score(val['Targ_Var_Difference'], reg.predict(X_val))
            
            results.append({
                'features': features_name,
                'n_estimators': params["n_estimators"],
                "max_depth": params["max_depth"],
                "min_samples_split": params["min_samples_split"],
                "min_samples_leaf": params["min_samples_leaf"],
                'train_acc': train_acc,
                'val_acc': val_acc,
                'train_f1': train_f1,
                'val_f1': val_f1,
                'train_mse': train_mse,
                'val_mse': val_mse,
                'train_r2': train_r2,
                'val_r2': val_r2
            })
    
    return pd.DataFrame(results)

def plot_results(df):
    # Columns for 5x4 grid
    param_columns = ["features", "n_estimators", "max_depth", "min_samples_split", "min_samples_leaf"]
    metrics = ['acc', 'f1', 'mse', 'r2']

    # Set up the figure
    fig, axes = plt.subplots(4, 5, figsize=(20, 16))
    plt.subplots_adjust(hspace=0.4, wspace=0.3)
    for row, metric in enumerate(metrics):
        for col, param in enumerate(param_columns):
            ax = axes[row, col]
    
    # Prepare data for plotting
            plot_data = []
            for param_value in df[param].unique():
                mask = df[param] == param_value
                train_vals = df[mask][f'train_{metric}']
                val_vals = df[mask][f'val_{metric}']
                
                plot_data.extend([
                    *zip(train_vals, [param_value] * len(train_vals), ['train'] * len(train_vals)),
                    *zip(val_vals, [param_value] * len(val_vals), ['val'] * len(val_vals))
                ])
            
            plot_df = pd.DataFrame(plot_data, columns=['value', 'param', 'type'])
            
            # Create boxplot
            sns.boxplot(data=plot_df, x='param', y='value', hue='type', ax=ax)
            
            # Customize plot
            ax.set_title(f'{param} vs {metric}')
            if col == 0:
                ax.set_ylabel(metric)
            else:
                ax.set_ylabel('')
            ax.set_xlabel('')
            ax.tick_params(axis='x', rotation=45)
            
            # Remove redundant legends except for last column
            if col < 4:
                ax.get_legend().remove()
    
    plt.tight_layout()
    return fig

# Update parameter grid to test all combinations
param_grid = [
    {'n_estimators': n, 'max_depth': d, 'min_samples_split': s, 'min_samples_leaf': l}
    for n in [100, 200, 500]
    for d in [None, 10, 20, 30]
    for s in [2, 5, 10]
    for l in [1, 2, 4]
]

# Run analysis
df = pd.read_csv("../data/complete_merged_and_prepared_data.csv", index_col = 0)
df["Date"] = pd.to_datetime(df["Date"])

results = train_and_evaluate_models(df, param_grid)
results.to_csv("../data/model_evaluation_results.csv")
plot_results(results).savefig("../plots/evaluation_parameters.png")

results.sort_values("val_acc", ascending=False).head(10)
results.sort_values("val_f1", ascending=False).head(10)
results.sort_values("val_mse").head(10)
results.sort_values("val_r2", ascending=False).head(10)

train, val, test = chronological_split(df)
train_plus_val = pd.concat([train, val])

features = prepare_feature_sets(df)["all_features"]
features

X_train_plus_val = prepare_data(train_plus_val, features)
X_test = prepare_data(test, features)

# Ensure consistent columns
for col in set(X_train_plus_val.columns) - set(X_test.columns):
    X_test[col] = 0
    
X_test = X_test[X_train_plus_val.columns]

# Classification model
clf = RandomForestClassifier(n_estimators=200, max_depth=25, min_samples_split=10, min_samples_leaf=2, random_state=37)
clf.fit(X_train_plus_val, train_plus_val['Targ_Var_Winner'])

train_acc = accuracy_score(train_plus_val['Targ_Var_Winner'], clf.predict(X_train_plus_val))
test_acc = accuracy_score(test['Targ_Var_Winner'], clf.predict(X_test))
train_f1 = f1_score(train_plus_val['Targ_Var_Winner'], clf.predict(X_train_plus_val), average='weighted')
test_f1 = f1_score(test['Targ_Var_Winner'], clf.predict(X_test), average='weighted')

# Regression model
reg = RandomForestRegressor(n_estimators=100, max_depth = 30, min_samples_split = 5, min_samples_leaf = 1, random_state=37)
reg.fit(X_train_plus_val, train_plus_val['Targ_Var_Difference'])

train_mse = mean_squared_error(train_plus_val['Targ_Var_Difference'], reg.predict(X_train_plus_val))
test_mse = mean_squared_error(test['Targ_Var_Difference'], reg.predict(X_test))
train_r2 = r2_score(train_plus_val['Targ_Var_Difference'], reg.predict(X_train_plus_val))
test_r2 = r2_score(test['Targ_Var_Difference'], reg.predict(X_test))

print(train_acc)
print(test_acc)

print(train_mse)
print(test_mse)
