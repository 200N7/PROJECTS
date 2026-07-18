from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix,
                             mean_absolute_error, mean_squared_error, r2_score)
import numpy as np

def divider():
    print("=" * 56)

def find_best_model(results):
    return max(results, key=lambda x: results[x]['score'])

def run_comparator(results, y_test, problem_type):
    if not results:
        print("  No models to compare.")
        return None, None, {}

    divider()
    print("  MODULE 4 — MODEL COMPARISON")
    divider()

    label = "Accuracy" if problem_type == 'classification' else "R2 Score"
    best_name = find_best_model(results)

    print(f"  {'Model':<30} {label:<12} Status")
    print("  " + "-" * 50)
    for name, res in sorted(results.items(), key=lambda x: x[1]['score'], reverse=True):
        status = "<-- BEST" if name == best_name else ""
        print(f"  {name:<30} {res['score']}%{'':<6} {status}")
    divider()

    best_result = results[best_name]
    preds       = best_result['predictions']
    metrics     = {}

    if problem_type == 'classification':
        precision = round(precision_score(y_test, preds, average='weighted', zero_division=0) * 100, 2)
        recall    = round(recall_score(y_test, preds, average='weighted', zero_division=0) * 100, 2)
        f1        = round(f1_score(y_test, preds, average='weighted', zero_division=0) * 100, 2)
        cm        = confusion_matrix(y_test, preds)
        metrics   = {'precision': precision, 'recall': recall, 'f1': f1, 'confusion_matrix': cm}

        print(f"\n  Detailed metrics for: {best_name}")
        divider()
        print(f"  Accuracy   : {best_result['score']}%")
        print(f"  Precision  : {precision}%")
        print(f"  Recall     : {recall}%")
        print(f"  F1 Score   : {f1}%")
        print(f"\n  Confusion Matrix:")
        print(cm)
    else:
        mae  = round(mean_absolute_error(y_test, preds), 4)
        rmse = round(np.sqrt(mean_squared_error(y_test, preds)), 4)
        r2   = round(r2_score(y_test, preds) * 100, 2)
        metrics = {'mae': mae, 'rmse': rmse, 'r2': r2}

        print(f"\n  Detailed metrics for: {best_name}")
        divider()
        print(f"  R2 Score   : {r2}%")
        print(f"  MAE        : {mae}")
        print(f"  RMSE       : {rmse}")

    divider()
    print()
    return best_name, best_result, metrics