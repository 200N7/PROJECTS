import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split

def divider():
    print("=" * 56)

def confirm_preprocessing_plan(analysis, safe_input):
    divider()
    print("  MODULE 2 — PREPROCESSING PLAN")
    divider()
    m = analysis['total_missing']
    d = analysis['duplicates']
    c = len(analysis['categorical_cols'])
    n = len(analysis['numeric_cols'])

    print(f"  Missing values : {'None found' if m == 0 else str(m) + ' — will fill automatically'}")
    print(f"  Duplicates     : {'None found' if d == 0 else str(d) + ' rows — will remove'}")
    print(f"  Encoding       : {'None needed' if c == 0 else str(c) + ' categorical column(s) — label encoding'}")
    print(f"  Scaling        : {'None needed' if n == 0 else 'StandardScaler on ' + str(n) + ' numeric column(s)'}")
    print(f"  Train/Test     : 80% train / 20% test split")
    divider()
    print("  1. Yes — proceed")
    print("  2. No  — skip preprocessing (not recommended)")
    divider()
    choice = safe_input("  Your choice (1 or 2): ")
    return choice != '2'

def handle_missing_values(df, feature_cols, analysis):
    filled = 0
    for col in feature_cols:
        missing = df[col].isnull().sum()
        if missing > 0:
            if col in analysis['numeric_cols']:
                val = df[col].median()
                df[col] = df[col].fillna(val)
                print(f"    Filled {missing} missing in '{col}' with median ({round(val, 2)})")
            else:
                val = df[col].mode()[0]
                df[col] = df[col].fillna(val)
                print(f"    Filled {missing} missing in '{col}' with mode ({val})")
            filled += missing
    if filled == 0:
        print("    No missing values found.")
    return df, filled

def remove_duplicates(df):
    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    removed = before - len(df)
    if removed > 0:
        print(f"    Removed {removed} duplicate rows.")
    else:
        print("    No duplicates found.")
    return df, removed

def encode_target(df, target_col):
    target_encoder = None
    if df[target_col].dtype == 'object':
        le = LabelEncoder()
        df[target_col] = le.fit_transform(df[target_col].astype(str))
        target_encoder = le
        print(f"    Encoded target '{target_col}' — classes: {list(le.classes_)}")
    return df, target_encoder

def encode_categorical(df, feature_cols, analysis):
    encoders = {}
    encoded  = []
    for col in feature_cols:
        if col in analysis['categorical_cols']:
            try:
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col].astype(str))
                encoders[col] = le
                encoded.append(col)
                print(f"    Encoded '{col}'")
            except Exception as e:
                print(f"    WARNING: Could not encode '{col}' — skipping. ({e})")
    if not encoded:
        print("    No categorical columns to encode.")
    return df, encoders, encoded

def scale_features(df, feature_cols, analysis):
    scaler = None
    numeric_in_features = [c for c in analysis['numeric_cols'] if c in feature_cols]
    if numeric_in_features:
        scaler = StandardScaler()
        df[numeric_in_features] = scaler.fit_transform(df[numeric_in_features])
        print(f"    Scaled {len(numeric_in_features)} numeric column(s).")
    else:
        print("    No numeric columns to scale.")
    return df, scaler

def split_data(df, feature_cols, target_col):
    X = df[feature_cols]
    y = df[target_col]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"    Train size : {len(X_train)} rows")
    print(f"    Test size  : {len(X_test)} rows")
    return X_train, X_test, y_train, y_test

def run_preprocessor(df, target_col, feature_cols, analysis, safe_input):
    proceed = confirm_preprocessing_plan(analysis, safe_input)
    if not proceed:
        print("\n  Skipping preprocessing. Using raw data.\n")
        X = df[feature_cols]
        y = df[target_col]
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            return X_train, X_test, y_train, y_test, {}, None, None
        except Exception as e:
            print(f"  ERROR splitting data: {e}")
            return None

    divider()
    print("  PREPROCESSING IN PROGRESS...")
    divider()

    print("\n  Step 1 — Handling missing values:")
    df, filled = handle_missing_values(df, feature_cols, analysis)

    print("\n  Step 2 — Removing duplicates:")
    df, removed = remove_duplicates(df)

    print("\n  Step 3 — Encoding target column:")
    df, target_encoder = encode_target(df, target_col)

    print("\n  Step 4 — Encoding categorical features:")
    df, encoders, encoded_cols = encode_categorical(df, feature_cols, analysis)

    print("\n  Step 5 — Scaling numeric features:")
    df, scaler = scale_features(df, feature_cols, analysis)

    print("\n  Step 6 — Splitting into train and test sets:")
    try:
        X_train, X_test, y_train, y_test = split_data(df, feature_cols, target_col)
    except Exception as e:
        print(f"  ERROR during split: {e}")
        return None

    print()
    divider()
    print("  PREPROCESSING COMPLETE")
    divider()
    print(f"  Missing values filled : {filled}")
    print(f"  Duplicates removed    : {removed}")
    print(f"  Columns encoded       : {len(encoded_cols)}")
    print(f"  Scaling applied       : {'Yes' if scaler else 'No'}")
    print(f"  Train size            : {len(X_train)} rows")
    print(f"  Test size             : {len(X_test)} rows")
    divider()
    print()

    return X_train, X_test, y_train, y_test, encoders, scaler, target_encoder