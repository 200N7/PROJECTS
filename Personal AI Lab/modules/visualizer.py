import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'output', 'graphs'
)

def divider():
    print("=" * 56)

def ensure_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def save(fig, filename):
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {filename}")

def graph1_correlation(df, feature_cols, analysis):
    try:
        cols = [c for c in analysis['numeric_cols'] if c in feature_cols]
        if len(cols) < 2:
            print("  Graph 1 skipped: need at least 2 numeric columns.")
            return
        fig, ax = plt.subplots(figsize=(max(6, len(cols)), max(5, len(cols) - 1)))
        sns.heatmap(df[cols].corr(), annot=True, fmt='.2f', cmap='coolwarm',
                    linewidths=0.5, square=True, ax=ax)
        ax.set_title('Feature Correlation Heatmap', fontsize=13, pad=12)
        fig.tight_layout()
        save(fig, 'graph1_correlation_heatmap.png')
    except Exception as e:
        print(f"  Graph 1 failed: {e}")

def graph2_missing(df_original, feature_cols):
    try:
        missing = df_original[feature_cols].isnull().sum()
        missing = missing[missing > 0]
        if len(missing) == 0:
            print("  Graph 2 skipped: no missing values.")
            return
        fig, ax = plt.subplots(figsize=(max(6, len(missing)), 5))
        colors = ['#e74c3c' if (v / len(df_original) * 100) > 10 else '#3498db'
                  for v in missing.values]
        bars = ax.bar(missing.index, missing.values, color=colors, edgecolor='white')
        for bar, val in zip(bars, missing.values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                    str(val), ha='center', va='bottom', fontsize=10)
        ax.set_title('Missing Values Per Column', fontsize=13)
        ax.set_xlabel('Column')
        ax.set_ylabel('Count')
        plt.xticks(rotation=30, ha='right')
        fig.tight_layout()
        save(fig, 'graph2_missing_values.png')
    except Exception as e:
        print(f"  Graph 2 failed: {e}")

def graph3_class_dist(df_original, target_col):
    try:
        counts = df_original[target_col].value_counts()
        fig, ax = plt.subplots(figsize=(7, 6))
        colors = sns.color_palette('Set2', len(counts))
        wedges, texts, autotexts = ax.pie(
            counts.values, labels=[str(c) for c in counts.index],
            autopct='%1.1f%%', colors=colors, startangle=90,
            pctdistance=0.80
        )
        for t in autotexts:
            t.set_fontsize(11)
        ax.set_title(f'Class Distribution — {target_col}', fontsize=13)
        fig.tight_layout()
        save(fig, 'graph3_class_distribution.png')
    except Exception as e:
        print(f"  Graph 3 failed: {e}")

def graph4_model_comparison(results, best_name, problem_type):
    try:
        names  = list(results.keys())
        scores = [results[n]['score'] for n in names]
        colors = ['#27ae60' if n == best_name else '#95a5a6' for n in names]

        fig, ax = plt.subplots(figsize=(max(7, len(names) * 2.5), 6))
        bars = ax.bar(names, scores, color=colors, edgecolor='white', width=0.5)
        for bar, score in zip(bars, scores):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    f'{score}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

        label = "Accuracy (%)" if problem_type == 'classification' else "R2 Score (%)"
        ax.set_title('Model Comparison', fontsize=13)
        ax.set_ylabel(label)
        ax.set_ylim(0, min(115, max(scores) + 20))
        plt.xticks(rotation=10, ha='right')
        fig.tight_layout()
        save(fig, 'graph4_model_comparison.png')
    except Exception as e:
        print(f"  Graph 4 failed: {e}")

def graph5_feature_importance(best_result, best_name, feature_cols):
    try:
        model = best_result['model']
        if not hasattr(model, 'feature_importances_'):
            print(f"  Graph 5 skipped: feature importance not available for {best_name}.")
            return
        imp = model.feature_importances_
        if len(imp) != len(feature_cols):
            print("  Graph 5 skipped: feature count mismatch.")
            return
        indices = np.argsort(imp)[::-1][:min(10, len(feature_cols))]
        feats   = [feature_cols[i] for i in indices]
        vals    = [imp[i] * 100 for i in indices]

        fig, ax = plt.subplots(figsize=(10, max(4, len(feats) * 0.6)))
        colors = sns.color_palette('Blues_r', len(feats))
        ax.barh(feats[::-1], vals[::-1], color=colors[::-1], edgecolor='white')
        for i, val in enumerate(vals[::-1]):
            ax.text(val + 0.3, i, f'{round(val, 1)}%', va='center', fontsize=9)
        ax.set_title('Feature Importance', fontsize=13)
        ax.set_xlabel('Importance (%)')
        fig.tight_layout()
        save(fig, 'graph5_feature_importance.png')
    except Exception as e:
        print(f"  Graph 5 failed: {e}")

def graph6_confusion_matrix(detail_metrics, best_name, problem_type):
    try:
        if problem_type != 'classification':
            print("  Graph 6 skipped: confusion matrix only for classification.")
            return
        cm = detail_metrics.get('confusion_matrix')
        if cm is None:
            print("  Graph 6 skipped: confusion matrix not available.")
            return
        fig, ax = plt.subplots(figsize=(7, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                    linewidths=0.5, square=True, ax=ax)
        ax.set_title(f'Confusion Matrix — {best_name}', fontsize=13)
        ax.set_ylabel('Actual')
        ax.set_xlabel('Predicted')
        fig.tight_layout()
        save(fig, 'graph6_confusion_matrix.png')
    except Exception as e:
        print(f"  Graph 6 failed: {e}")

def run_visualizer(df, df_original, target_col, feature_cols, analysis,
                   results, best_name, best_result, detail_metrics, problem_type):
    ensure_dir()
    divider()
    print("  MODULE 6 — GENERATING VISUALIZATIONS")
    divider()
    print()

    graph1_correlation(df, feature_cols, analysis)
    graph2_missing(df_original, feature_cols)
    graph3_class_dist(df_original, target_col)
    graph4_model_comparison(results, best_name, problem_type)
    graph5_feature_importance(best_result, best_name, feature_cols)
    graph6_confusion_matrix(detail_metrics, best_name, problem_type)

    print()
    divider()
    print(f"  Graphs saved to: output/graphs/")
    divider()
    print()