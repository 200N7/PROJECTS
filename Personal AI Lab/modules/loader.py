import pandas as pd

def divider():
    print("=" * 56)

# Loads CSV and shows preview
def load_dataset(filepath):
    try:
        df = pd.read_csv(filepath)
        divider()
        print("  DATASET LOADED SUCCESSFULLY")
        divider()
        print(f"  File       : {filepath.split('/')[-1].split(chr(92))[-1]}")
        print(f"  Rows       : {df.shape[0]}")
        print(f"  Columns    : {df.shape[1]}")
        divider()
        print("\n  First 5 rows of your data:\n")
        print(df.head().to_string())
        print()
        return df
    except FileNotFoundError:
        print("  ERROR: File not found. Please check the path.")
        return None
    except pd.errors.EmptyDataError:
        print("  ERROR: File is empty.")
        return None
    except Exception as e:
        print(f"  ERROR: Could not load file. Reason: {str(e)}")
        return None

# Detects the most likely target column
# Improved: prefers last non-ID column, avoids columns with too few OR too many unique values
def detect_target_column(df):
    ignore_keywords = ['id', 'name', 'index', 'serial', 'no', 'number', 'code', 'roll']
    candidates = []

    for col in df.columns:
        col_lower = col.lower()

        # Skip columns that look like identifiers
        if any(kw == col_lower or col_lower.startswith(kw) for kw in ignore_keywords):
            continue

        # Skip if all values are unique (likely an ID)
        if df[col].nunique() == len(df):
            continue

        unique_ratio = df[col].nunique() / len(df)

        # Good target: small number of unique values relative to dataset
        if unique_ratio <= 0.10:
            candidates.append((col, unique_ratio))

    if candidates:
        # Prefer the LAST good candidate — targets are usually the last column
        # among candidates, sort by position in dataframe (later = better)
        col_order = {col: i for i, col in enumerate(df.columns)}
        candidates.sort(key=lambda x: col_order[x[0]], reverse=True)
        return candidates[0][0]

    # Fallback: return last column
    return df.columns[-1]

# Asks user to confirm or override the target column
def confirm_target_column(df, safe_input):
    detected = detect_target_column(df)
    divider()
    print("  STEP 1 — CONFIRM TARGET COLUMN")
    print("  (The column you want to predict)")
    divider()
    print(f"  Detected target : '{detected}'")
    print(f"  Unique values   : {list(df[detected].unique()[:6])}")
    divider()
    print("  1. Yes — this is correct")
    print("  2. No  — let me choose manually")
    divider()
    choice = safe_input("  Your choice (1 or 2): ")

    if choice == '1':
        print(f"\n  Target column confirmed: '{detected}'\n")
        return detected

    elif choice == '2':
        print("\n  All available columns:\n")
        for i, col in enumerate(df.columns):
            dtype = str(df[col].dtype)
            unique = df[col].nunique()
            print(f"  {i+1:2}. {col:<25} type: {dtype:<10} unique values: {unique}")
        divider()
        col_choice = safe_input("  Enter column number: ")
        try:
            selected = df.columns[int(col_choice) - 1]
            print(f"\n  Target column set to: '{selected}'\n")
            return selected
        except (ValueError, IndexError):
            print("  Invalid choice. Using detected column.\n")
            return detected
    else:
        print("  Invalid input. Using detected column.\n")
        return detected

# Detects whether problem is classification or regression
def detect_problem_type(df, target_col):
    col = df[target_col]
    # If text values — classification
    if col.dtype == 'object':
        return 'classification'
    # If only 2 unique values — classification (binary)
    if col.nunique() == 2:
        return 'classification'
    # If few unique values relative to size — classification
    if col.nunique() <= 15 and (col.nunique() / len(col)) < 0.05:
        return 'classification'
    # Otherwise regression
    return 'regression'

# Asks user to confirm the problem type
def confirm_problem_type(df, target_col, safe_input):
    detected = detect_problem_type(df, target_col)
    divider()
    print("  STEP 2 — CONFIRM PROBLEM TYPE")
    divider()
    print(f"  Detected type : {detected.upper()}")
    if detected == 'classification':
        vals = list(df[target_col].unique()[:6])
        print(f"  Because '{target_col}' has discrete values: {vals}")
    else:
        print(f"  Because '{target_col}' has continuous numeric values")
        print(f"  Unique values count: {df[target_col].nunique()}")
    divider()
    print("  1. Yes — this is correct")
    print("  2. No  — switch to the other type")
    divider()
    choice = safe_input("  Your choice (1 or 2): ")

    if choice == '1':
        print(f"\n  Problem type confirmed: {detected.upper()}\n")
        return detected
    elif choice == '2':
        switched = 'regression' if detected == 'classification' else 'classification'
        print(f"\n  Problem type set to: {switched.upper()}\n")
        return switched
    else:
        print("  Invalid input. Using detected type.\n")
        return detected

# Detects which columns are informative features
def detect_feature_columns(df, target_col):
    ignore_keywords = ['id', 'name', 'index', 'serial', 'code', 'roll']
    feature_cols = []
    ignored_cols = []

    for col in df.columns:
        if col == target_col:
            continue
        col_lower = col.lower()

        # Check if it looks like an ID or name column
        is_identifier = any(kw == col_lower or col_lower.startswith(kw)
                            for kw in ignore_keywords)
        # Check if all values are unique (definitely an ID)
        all_unique = df[col].nunique() == len(df)

        if is_identifier or all_unique:
            ignored_cols.append(col)
        else:
            feature_cols.append(col)

    return feature_cols, ignored_cols

# Asks user to confirm or override feature columns
def confirm_feature_columns(df, target_col, safe_input):
    feature_cols, ignored_cols = detect_feature_columns(df, target_col)
    divider()
    print("  STEP 3 — CONFIRM FEATURE COLUMNS")
    print("  (Columns used as inputs to train the model)")
    divider()
    print("  Will USE these columns as features:")
    for col in feature_cols:
        print(f"    + {col}")
    if ignored_cols:
        print("\n  Will IGNORE these columns (non-informative):")
        for col in ignored_cols:
            print(f"    - {col}")
    divider()
    print("  1. Yes — looks correct")
    print("  2. No  — let me select manually")
    divider()
    choice = safe_input("  Your choice (1 or 2): ")

    if choice == '1':
        print(f"\n  Features confirmed.\n")
        return feature_cols
    elif choice == '2':
        available = [col for col in df.columns if col != target_col]
        print("\n  Available columns (excluding target):\n")
        for i, col in enumerate(available):
            print(f"  {i+1}. {col}")
        divider()
        print("  Enter column numbers separated by commas.")
        print("  Example: 1,2,3,4")
        divider()
        manual = safe_input("  Your selection: ")
        try:
            indices  = [int(x.strip()) - 1 for x in manual.split(',')]
            selected = [available[i] for i in indices if 0 <= i < len(available)]
            if not selected:
                print("  No valid columns selected. Using detected features.\n")
                return feature_cols
            print(f"\n  Features set to: {selected}\n")
            return selected
        except (ValueError, IndexError):
            print("  Invalid input. Using detected features.\n")
            return feature_cols
    else:
        print("  Invalid input. Using detected features.\n")
        return feature_cols

# Prints final confirmed settings
def print_confirmed_settings(filepath, target_col, problem_type, feature_cols):
    divider()
    print("  CONFIRMED SETTINGS")
    divider()
    print(f"  File            : {filepath.split('/')[-1].split(chr(92))[-1]}")
    print(f"  Target column   : {target_col}")
    print(f"  Problem type    : {problem_type.upper()}")
    print(f"  Feature columns : {', '.join(feature_cols)}")
    print(f"  Feature count   : {len(feature_cols)}")
    divider()
    print("\n  Starting full analysis...\n")

# Main loader function — accepts safe_input from main
def run_loader(filepath, safe_input):
    df = load_dataset(filepath)
    if df is None:
        return None, None, None, None

    if len(df) < 20:
        print("  WARNING: Dataset has fewer than 20 rows.")
        print("  ML results may not be reliable.\n")
    elif len(df) < 50:
        print("  NOTE: Small dataset (fewer than 50 rows).")
        print("  Results should be interpreted carefully.\n")

    target_col   = confirm_target_column(df, safe_input)
    problem_type = confirm_problem_type(df, target_col, safe_input)
    feature_cols = confirm_feature_columns(df, target_col, safe_input)

    if not feature_cols:
        print("  ERROR: No valid feature columns found.")
        return None, None, None, None

    print_confirmed_settings(filepath, target_col, problem_type, feature_cols)
    return df, target_col, problem_type, feature_cols