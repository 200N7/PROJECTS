# Personal AI Lab 🤖
### Automated Machine Learning Experiment Platform

> *"Most projects build a model. This project builds a tool that builds models."*

---

## What is this?

Personal AI Lab is an automated ML platform I built as part of my 2nd semester AIML course (CSAI2018 — Elements of Artificial Intelligence and Machine Learning) at UPES Dehradun.

The idea is simple: you give it any CSV dataset, and it automatically does everything —
- Analyses your data
- Cleans and preprocesses it
- Trains 3 ML models simultaneously
- Compares them and finds the best one
- Explains why that model won — in plain English
- Generates 6 visualizations automatically

No coding knowledge needed to use it. Just a CSV file.

---

## The Problem It Solves

Millions of people have valuable data — teachers with student records, doctors with patient logs, shop owners with sales data — but they can't analyse it because ML tools require programming knowledge they don't have.

This is called the **data-rich, insight-poor problem.**

Personal AI Lab solves this by automating the entire ML pipeline and explaining results in plain English so anyone can understand them.

---

## Features

- ✅ Works with **any CSV dataset** — not just one fixed dataset
- ✅ **Confirmation gates** — asks before every major step, never assumes
- ✅ **Auto detects** target column, problem type (classification/regression), and feature columns
- ✅ Trains **3 models simultaneously** and compares them
- ✅ **Plain English explanations** of why one model beat others
- ✅ **Feature importance** — tells you which factor matters most
- ✅ **6 automatic graphs** saved to output/graphs/
- ✅ Type **EXIT** at any prompt to quit safely
- ✅ Handles missing values, duplicates, encoding and scaling automatically
- ✅ Works on **Windows and Linux**

---

## Project Structure

```
personal_ai_lab/
│
├── main.py                    ← Entry point — run this
│
├── modules/
│   ├── loader.py              ← Module 0: Load data + confirmation gates
│   ├── analyzer.py            ← Module 1: Auto exploratory data analysis
│   ├── preprocessor.py        ← Module 2: Clean and prepare data
│   ├── trainer.py             ← Module 3: Train 3 ML models
│   ├── comparator.py          ← Module 4: Compare and evaluate models
│   ├── insights.py            ← Module 5: Plain English explanations
│   └── visualizer.py          ← Module 6: Generate 6 graphs
│
├── datasets/
│   └── sample.csv             ← Built-in student performance dataset
│
├── output/
│   └── graphs/                ← All generated graphs saved here
│
└── README.md
```

---

## How It Works — Pipeline

```
You run python main.py
        ↓
Select your CSV file (built-in or your own)
        ↓
System asks 3 confirmation questions:
  → Which column to predict?
  → Classification or Regression?
  → Which columns to use as features?
        ↓
Module 1: Analyses your data (rows, missing values, balance)
        ↓
Module 2: Cleans it (fills missing, removes duplicates, encodes, scales)
        ↓
Module 3: Trains 3 models simultaneously
        ↓
Module 4: Compares accuracy, precision, recall, F1
        ↓
Module 5: Explains results in plain English + meta warning
        ↓
Module 6: Saves 6 graphs to output/graphs/
```

---

## Models Used

| Problem Type | Models Trained |
|---|---|
| Classification | Logistic Regression, KNN Classifier, Decision Tree Classifier |
| Regression | Linear Regression, KNN Regressor, Decision Tree Regressor |

The system automatically detects which type your dataset needs.

---

## Graphs Generated

| Graph | What It Shows |
|---|---|
| graph1_correlation_heatmap.png | Correlation between all numeric features |
| graph2_missing_values.png | Missing value count per column |
| graph3_class_distribution.png | Balance between target classes |
| graph4_model_comparison.png | Accuracy of all 3 models side by side |
| graph5_feature_importance.png | Which feature influenced predictions most |
| graph6_confusion_matrix.png | Correct vs incorrect predictions |

---

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/personal-ai-lab.git
cd personal-ai-lab

# Install dependencies
pip install pandas numpy matplotlib seaborn scikit-learn
```

---

## Usage

```bash
# Run with built-in student dataset
python main.py

# Run with your own CSV file
python main.py path/to/your/dataset.csv
```

At any prompt, type `EXIT` to quit safely.

---

## Built-in Demo Dataset

The project includes a student performance dataset (60 records) with these features:

| Feature | Description |
|---|---|
| attendance | Attendance percentage |
| marks_prev | Previous semester marks |
| sleep_hours | Average daily sleep |
| study_hours | Daily self-study hours |
| stress_level | Low / Medium / High |
| part_time_job | Yes / No |
| result | **Pass / Fail** ← target column |

You can also test with any Kaggle dataset (Titanic, Iris, House Prices etc.)

---

## Sample Output

```
========================================================
          PERSONAL AI LAB
     Automated ML Experiment Platform
========================================================
  Making ML accessible to everyone.
  Load any CSV. Get full ML analysis.
  Type EXIT at any prompt to quit safely.
========================================================

  Training Logistic Regression...     done   Accuracy: 100.0%
  Training KNN Classifier...          done   Accuracy: 91.67%
  Training Decision Tree...           done   Accuracy: 100.0%

========================================================
  MODULE 5 — AI INSIGHTS
========================================================
  Best model     : Logistic Regression (100.0%)
  Why it won     : Linear model performed best which suggests
                   your data has a linear relationship between
                   features and target.
  Key factor     : Most influential feature is 'attendance' (43%)
  META WARNING   : This system carries its own uncertainty.
                   Always verify with domain knowledge.
========================================================
```

---

## What Makes This Different

Most ML projects:
- One fixed dataset
- One hardcoded model
- No explanation of results

This project:
- **Any** CSV dataset
- **Three** models trained and compared automatically
- **Plain English** explanation of every result
- **Confirmation gates** — never assumes, always asks
- **Honest** — acknowledges its own uncertainty with a meta warning

---

## Tech Stack

- Python 3.8+
- pandas, numpy
- scikit-learn
- matplotlib, seaborn

---

## Course Details

- **Course:** CSAI2018 — Elements of Artificial Intelligence and Machine Learning
- **Semester:** 2nd Semester
- **Programme:** B.Tech CSE (AI & ML)
- **Institution:** University of Petroleum & Energy Studies, Dehradun

---

## Limitations

- Supports CSV files only (Excel, JSON not yet supported)
- Limited to 3 algorithms per problem type
- No hyperparameter tuning
- Insight generator uses rule-based logic
- Small datasets (< 20 rows) may give unreliable results

---

## Future Work

- Add Random Forest and SVM
- Implement k-fold cross-validation
- Build a Flask web interface
- Auto PDF report generation
- Support Excel and JSON formats

---

## License

This project is for educational purposes.

---

*Built with curiosity and a lot of trial and error 🙂*
