import sys
import os
import warnings
warnings.filterwarnings('ignore')

sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
'''
from loader       import run_loader
from analyzer     import run_analyzer
from preprocessor import run_preprocessor
from trainer      import run_trainer
from comparator   import run_comparator
from insights     import run_insights
from visualizer   import run_visualizer
'''
from modules.loader import run_loader
from modules.analyzer import run_analyzer
from modules.preprocessor import run_preprocessor
from modules.trainer import run_trainer
from modules.comparator import run_comparator
from modules.insights import run_insights
from modules.visualizer import run_visualizer
DATASETS_DIR = os.path.join(os.path.dirname(__file__), 'datasets')

def divider():
    print("=" * 56)

def banner():
    divider()
    print("          PERSONAL AI LAB")
    print("     Automated ML Experiment Platform")
    divider()
    print("  Making ML accessible to everyone.")
    print("  Load any CSV. Get full ML analysis.")
    print()
    print("  Type EXIT at any prompt to quit safely.")
    divider()
    print()

def safe_input(prompt):
    try:
        val = input(prompt).strip()
        if val.upper() == 'EXIT':
            print()
            divider()
            print("  Session ended by user. Goodbye.")
            divider()
            sys.exit(0)
        return val
    except (KeyboardInterrupt, EOFError):
        print()
        divider()
        print("  Session interrupted. Goodbye.")
        divider()
        sys.exit(0)

def list_csv_files():
    if not os.path.exists(DATASETS_DIR):
        os.makedirs(DATASETS_DIR)
    return sorted([f for f in os.listdir(DATASETS_DIR) if f.lower().endswith('.csv')])

def select_file():
    divider()
    print("  STEP 0 — SELECT YOUR DATASET")
    divider()
    csv_files = list_csv_files()
    print("  1. Choose from available datasets")
    print("  2. Enter full path to your own CSV file")
    divider()
    choice = safe_input("  Your choice (1 or 2): ")

    if choice == '1':
        if not csv_files:
            print("\n  No CSV files found in datasets/ folder.")
            print("  Please add a CSV or choose option 2.\n")
            return select_file()
        divider()
        print("  Available datasets:\n")
        for i, fname in enumerate(csv_files):
            size = os.path.getsize(os.path.join(DATASETS_DIR, fname))
            size_str = f"{size // 1024} KB" if size >= 1024 else f"{size} bytes"
            print(f"  {i+1}. {fname}  ({size_str})")
        print()
        if len(csv_files) == 1:
            divider()
            print(f"  Only one file found: {csv_files[0]}")
            confirm = safe_input("  Use this file? (yes / no): ").lower()
            if confirm in ['yes', 'y']:
                fp = os.path.join(DATASETS_DIR, csv_files[0])
                print(f"\n  Selected: {csv_files[0]}\n")
                return fp
            else:
                return select_file()
        divider()
        sel = safe_input(f"  Enter number (1 to {len(csv_files)}): ")
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(csv_files):
                fp = os.path.join(DATASETS_DIR, csv_files[idx])
                print(f"\n  Selected: {csv_files[idx]}\n")
                return fp
            print("  Invalid number. Please try again.\n")
            return select_file()
        except ValueError:
            print("  Invalid input. Please enter a number.\n")
            return select_file()

    elif choice == '2':
        divider()
        print("  Enter the full path to your CSV file.")
        print("  Example: C:\\Users\\Name\\Documents\\data.csv")
        divider()
        path = safe_input("  File path: ")
        if not path:
            print("  No path entered. Please try again.\n")
            return select_file()
        path = os.path.expanduser(os.path.expandvars(path.strip('"').strip("'")))
        if not os.path.exists(path):
            print(f"\n  File not found: {path}")
            print("  Please check the path and try again.\n")
            return select_file()
        if not path.lower().endswith('.csv'):
            confirm = safe_input("  File is not .csv. Try anyway? (yes / no): ").lower()
            if confirm not in ['yes', 'y']:
                return select_file()
        print(f"\n  File found: {os.path.basename(path)}\n")
        return path
    else:
        print("  Invalid choice. Please enter 1 or 2.\n")
        return select_file()

def run(filepath):
    df, target_col, problem_type, feature_cols = run_loader(filepath, safe_input)
    if df is None:
        print("  Could not load dataset.\n")
        return False

    df_original = df.copy()
    analysis = run_analyzer(df, target_col, feature_cols)

    divider()
    cont = safe_input("  Proceed to preprocessing? (yes / no): ").lower()
    if cont not in ['yes', 'y']:
        print("\n  Stopped after analysis.\n")
        return True

    result = run_preprocessor(df, target_col, feature_cols, analysis, safe_input)
    if result is None:
        print("  Preprocessing failed.\n")
        return False
    X_train, X_test, y_train, y_test, encoders, scaler, target_encoder = result

    results = run_trainer(X_train, X_test, y_train, y_test, problem_type, safe_input)
    if not results:
        print("  No models trained.\n")
        return False

    best_name, best_result, detail_metrics = run_comparator(results, y_test, problem_type)
    if best_name is None:
        print("  Could not compare models.\n")
        return False

    run_insights(best_name, best_result, feature_cols, analysis, problem_type)
    run_visualizer(df, df_original, target_col, feature_cols, analysis,
                   results, best_name, best_result, detail_metrics, problem_type)

    divider()
    print("  ANALYSIS COMPLETE")
    divider()
    print(f"  Dataset    : {os.path.basename(filepath)}")
    print(f"  Best model : {best_name}")
    print(f"  Score      : {best_result['score']}%")
    print(f"  Graphs     : output/graphs/")
    divider()
    print()
    print("  Always verify results with domain knowledge")
    print("  before making any real world decisions.")
    divider()
    print()
    return True

def main():
    banner()
    while True:
        filepath = select_file()
        run(filepath)
        divider()
        again = safe_input("  Analyse another dataset? (yes / no): ").lower()
        print()
        if again not in ['yes', 'y']:
            divider()
            print("  Thank you for using Personal AI Lab.")
            divider()
            break

if __name__ == '__main__':
    if len(sys.argv) > 1:
        banner()
        fp = sys.argv[1]
        if not os.path.exists(fp):
            print(f"  File not found: {fp}")
            sys.exit(1)
        run(fp)
    else:
        main()