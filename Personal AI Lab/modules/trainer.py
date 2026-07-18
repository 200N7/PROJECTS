from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.metrics import accuracy_score, r2_score
import warnings
warnings.filterwarnings('ignore')

def divider():
    print("=" * 56)

def confirm_training(problem_type, safe_input):
    divider()
    print("  MODULE 3 — MODEL TRAINING PLAN")
    divider()
    if problem_type == 'classification':
        print("  Will train these 3 models:")
        print("    1. Logistic Regression")
        print("    2. K Nearest Neighbours Classifier")
        print("    3. Decision Tree Classifier")
    else:
        print("  Will train these 3 models:")
        print("    1. Linear Regression")
        print("    2. K Nearest Neighbours Regressor")
        print("    3. Decision Tree Regressor")
    divider()
    print("  1. Yes — train all models")
    print("  2. No  — skip training")
    divider()
    choice = safe_input("  Your choice (1 or 2): ")
    return choice != '2'

def train_single_model(name, model, X_train, X_test, y_train, y_test, problem_type):
    try:
        print(f"  Training {name}...", end='', flush=True)
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        if problem_type == 'classification':
            score = round(accuracy_score(y_test, preds) * 100, 2)
        else:
            score = round(r2_score(y_test, preds) * 100, 2)
        label = "Accuracy" if problem_type == 'classification' else "R2 Score"
        print(f"\r  Training {name:<35} done   {label}: {score}%")
        return model, score, preds
    except Exception as e:
        print(f"\r  Training {name:<35} FAILED ({str(e)})")
        return None, None, None

def run_trainer(X_train, X_test, y_train, y_test, problem_type, safe_input):
    proceed = confirm_training(problem_type, safe_input)
    if not proceed:
        print("\n  Skipping model training.\n")
        return {}

    divider()
    print("  TRAINING IN PROGRESS...")
    divider()
    print()

    if problem_type == 'classification':
        # Determine good K for KNN based on dataset size
        k = min(5, max(1, len(X_train) // 10))
        models = {
            'Logistic Regression' : LogisticRegression(max_iter=2000, random_state=42),
            'KNN Classifier'      : KNeighborsClassifier(n_neighbors=k),
            'Decision Tree'       : DecisionTreeClassifier(random_state=42, max_depth=10)
        }
    else:
        k = min(5, max(1, len(X_train) // 10))
        models = {
            'Linear Regression'   : LinearRegression(),
            'KNN Regressor'       : KNeighborsRegressor(n_neighbors=k),
            'Decision Tree'       : DecisionTreeRegressor(random_state=42, max_depth=10)
        }

    results = {}
    for name, model in models.items():
        trained, score, preds = train_single_model(
            name, model, X_train, X_test, y_train, y_test, problem_type
        )
        if trained is not None:
            results[name] = {
                'model'       : trained,
                'score'       : score,
                'predictions' : preds
            }

    print()
    divider()
    if results:
        print(f"  Training complete. {len(results)}/3 models trained successfully.")
    else:
        print("  WARNING: No models trained successfully.")
    divider()
    print()
    return results