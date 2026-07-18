# CodeRefine v2.0

> A console-based static code analyzer built in Python that detects the programming language, validates syntax, refines code quality, and generates beginner-friendly comments — all **without executing the code**.

---

## 📌 Overview

**CodeRefine** is a rule-based static code analysis tool that accepts **Python, Java, and C** source code and processes it through a structured analysis pipeline.

The tool performs:

- 🔍 Language Detection
- ✅ Syntax Validation
- 🔧 Automatic Syntax Fixes
- 📝 Variable Analysis
- 🎨 Code Formatting
- 💬 Comment Generation
- 📊 Quality Scoring
- 🗂 Persistent Analysis History

Unlike compilers or interpreters, **CodeRefine never executes the user's code**, making the analysis completely static and safe.

---

## ✨ Features

### 🔍 Language Detection

Automatically identifies whether the submitted code is:

- Python
- Java
- C

using keyword and syntax pattern matching.

---

### ✅ Syntax Validation

Detects common syntax mistakes without executing the program.

#### Python
- Missing colons (`:`)
- Python 2 `print` syntax
- Incorrect logical operators (`&&`, `||`)
- Invalid comparison operator (`<>`)
- Assignment (`=`) used instead of comparison (`==`) inside conditions
- Bad indentation
- Unbalanced brackets

#### C / Java
- Missing semicolons
- Incorrect logical operators (`and`, `or`, `not`)
- Unbalanced brackets and braces

---

### 🔧 Auto-Fix Engine

Automatically fixes many detected issues, including:

- Missing colons
- Missing semicolons
- Incorrect logical operators
- Unclosed brackets
- Unclosed braces
- Common syntax mistakes

---

### 📝 Variable Analysis

Performs basic static variable analysis by:

- Detecting unused variables
- Commenting out unused variables
- Inlining single-use expression variables
- Renaming unclear single-letter variables

> **Note:** Common loop variables such as `i`, `j`, `k`, `n`, and `m` are preserved.

---

### 🎨 Formatting Cleanup

Improves readability by:

- Normalizing spaces around operators
- Cleaning assignment formatting
- Preserving string literals while formatting

---

### 💬 Comment Generation

Automatically inserts beginner-friendly comments for:

- Functions
- Classes
- Imports
- Loops
- Conditional statements
- Input/Output statements
- Computed assignments

---

### 📊 Quality Scoring

Generates a quality score **out of 100** based on detected issues.

The report includes:

- Final score
- Individual deductions
- Detailed feedback for every issue found

---

### 🗂 Persistent History

Every analysis is automatically stored in a local SQLite database.

Database file:

```
coderefine.db
```

Stored information includes:

- Date
- Time
- Programming language
- Quality score
- Analysis history

---

### 🔐 Admin Panel

Password-protected admin mode provides:

- Total analyses
- Average quality score
- Complete analysis history
- History grouped by date

---

# 🛠 Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3 |
| Database | SQLite3 |
| Libraries | `re`, `sqlite3`, `datetime`, `collections` |
| Interface | Console (Menu Driven) |

> Only Python's Standard Library is used.

---

# 📂 Project Structure

```
CodeRefine/
│
├── coderefine.py
├── coderefine.db        # Auto-generated
└── README.md
```

---

# 🚀 Getting Started

## 1. Clone the Repository

```bash
git clone https://github.com/200N7/PROJECTS.git
```

---

## 2. Navigate to the Project Folder

```bash
cd PROJECTS/CodeRefine
```

---

## 3. Run the Program

```bash
python coderefine.py
```

---

## 4. Choose a Mode

### 👤 User Mode

- Paste source code
- Type `END`
- View:
  - Detected language
  - Errors
  - Auto-fixes
  - Quality score
  - Refined code

### 🔐 Admin Mode

Enter the admin password to access:

- Total analyses
- Average score
- Complete history
- Date-wise analysis logs

---

# ⚙ Analysis Pipeline

```
Input Code
     │
     ▼
Language Detection
     │
     ▼
Syntax Validation
     │
     ▼
Auto-Fix Engine
     │
     ▼
Variable Analysis
     │
     ▼
Formatting Cleanup
     │
     ▼
Comment Generation
     │
     ▼
Quality Scoring
     │
     ▼
SQLite History Storage
```

---

# 🎯 Learning Outcomes

This project helped me gain practical experience with:

- Regular Expressions (Regex)
- Rule-based static code analysis
- Multi-language syntax rule design
- SQLite database integration
- Safe string manipulation
- Code formatting techniques
- Static variable analysis
- Designing a structured analysis pipeline
- Building menu-driven console applications

---

# 🚀 Future Enhancements

Planned improvements include:

- Support for additional programming languages
- Export refined code to files
- PDF/HTML analysis reports
- GUI or web-based interface
- More advanced quality metrics
- Smarter variable naming suggestions
- Configurable analysis rules

---

# 🤝 Contributing

Suggestions, improvements, and feedback are always welcome.

Feel free to fork the repository, submit issues, or open pull requests.

---

# 📄 License

This project is intended for educational and learning purposes.

---

# 🙏 Acknowledgment

Built as part of my continuous learning journey in **Python**, **static code analysis**, and **software engineering fundamentals**.
