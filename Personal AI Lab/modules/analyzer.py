import pandas as pd

def divider():
    print("=" * 56)

def check_class_balance(df, target_col):
    counts = df[target_col].value_counts()
    total  = len(df)
    ratio  = counts.max() / total
    if ratio > 0.80:
        return "HIGH imbalance — results may be misleading", counts
    elif ratio > 0.65:
        return "Moderate imbalance detected", counts
    else:
        return "Balanced", counts

def run_analyzer(df, target_col, feature_cols):
    divider()
    print("  MODULE 1 — DATASET ANALYSIS REPORT")
    divider()

    total_missing = df[feature_cols].isnull().sum().sum()
    missing_pct   = round((total_missing / (df.shape[0] * len(feature_cols))) * 100, 2) if feature_cols else 0
    duplicates    = df.duplicated().sum()

    numeric_cols     = df[feature_cols].select_dtypes(include=['int64','float64','int32','float32']).columns.tolist()
    categorical_cols = df[feature_cols].select_dtypes(include=['object','category','bool']).columns.tolist()

    balance_status, counts = check_class_balance(df, target_col)

    print(f"  Total rows        : {df.shape[0]}")
    print(f"  Total columns     : {df.shape[1]}")
    print(f"  Feature columns   : {len(feature_cols)}")
    print(f"  Missing values    : {total_missing} ({missing_pct}%)")
    print(f"  Duplicate rows    : {duplicates}")
    print(f"  Numeric features  : {len(numeric_cols)}")
    print(f"  Categorical feats : {len(categorical_cols)}")
    print(f"  Class balance     : {balance_status}")
    for cls, cnt in counts.items():
        pct = round(cnt / len(df) * 100, 1)
        print(f"                      {cls}: {cnt} ({pct}%)")
    divider()

    # Per-column missing detail
    col_missing = df[feature_cols].isnull().sum()
    if col_missing.sum() > 0:
        print("\n  Missing values per column:")
        for col, cnt in col_missing.items():
            if cnt > 0:
                pct = round(cnt / len(df) * 100, 1)
                flag = " <- HIGH (>10%)" if pct > 10 else ""
                print(f"    {col}: {cnt} ({pct}%){flag}")
    else:
        print("\n  No missing values in feature columns.")

    # Basic statistics
    if numeric_cols:
        print("\n  Statistics for numeric features:\n")
        stats = df[numeric_cols].describe().round(2)
        print(stats.to_string())

    print()
    divider()
    print()

    return {
        'numeric_cols'    : numeric_cols,
        'categorical_cols': categorical_cols,
        'total_missing'   : int(total_missing),
        'duplicates'      : int(duplicates),
        'balance_status'  : balance_status,
        'class_counts'    : counts
    }