import re
import sqlite3
from datetime import datetime
from collections import defaultdict

# CONFIGURATION CONSTANTS
DB_FILE = "coderefine.db"
ADMIN_PASSWORD = "admin123"

# DATABASE PERSISTENCE MODULE
def init_db():
    """
    Initialize SQLite database with analyses table. Creates table if it doesn't exist - stores all analysis history.
    """
    con = sqlite3.connect(DB_FILE)
    con.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT    NOT NULL,
            language  TEXT    NOT NULL,
            score     INTEGER NOT NULL,
            issues    INTEGER NOT NULL
        )
    """)
    con.commit()
    con.close()
def load_history():
    """
    Load all analysis records from database.
    Returns: List of dictionaries with analysis data
    """
    init_db()
    con = sqlite3.connect(DB_FILE)
    rows = con.execute(
        "SELECT timestamp, language, score, issues FROM analyses ORDER BY id ASC"
    ).fetchall()
    con.close()
    
    return [
        {'timestamp': r[0], 'language': r[1], 'score': r[2], 'issues': r[3]}
        for r in rows
    ]

def save_entry(entry):
    """
    Save a single analysis record to database.
    Args: entry dict with timestamp, language, score, issues
    """
    init_db()
    try:
        con = sqlite3.connect(DB_FILE)
        con.execute(
            "INSERT INTO analyses (timestamp, language, score, issues) VALUES (?, ?, ?, ?)",
            (entry['timestamp'], entry['language'], entry['score'], entry['issues'])
        )
        con.commit()
        con.close()
    except sqlite3.Error as e:
        print(f"  Warning: Could not save record - {e}")

# LANGUAGE DETECTION MODULE
def detect_language(code):
    """
    Auto-detect programming language by analyzing keyword patterns.    
    Algorithm:
    - Counts occurrences of language-specific keywords
    - Scores each language (Python, Java, C)
    - Returns language with highest score    
    Returns: 'Python', 'Java', or 'C'
    """
    cl = code.lower()
    
    # Language-specific keywords
    python_kw = ['def ', 'elif ', 'print(', '__init__', 'self.', 'range(', 
                 'input(', 'import ', 'from ']
    java_kw = ['public class', 'public static void main', 'system.out', 
               'scanner ', 'string[]', 'throws ']
    c_kw = ['#include', 'printf(', 'scanf(', 'int main(', 'void main(', 
            'malloc(', 'sizeof(', '#define']
    
    # Count keyword matches
    py = sum(1 for kw in python_kw if kw in cl)
    jv = sum(1 for kw in java_kw if kw in cl)
    c = sum(1 for kw in c_kw if kw in cl)
    
    # Return highest scoring language
    if py >= jv and py >= c:
        return "Python"
    elif jv >= c:
        return "Java"
    else:
        return "C"

# STRING LITERAL PROTECTION
def strip_strings(line):
    """
    Replace all string literals with empty quotes. Prevents false variable detection inside strings.    
    Example: 'print("m value")' becomes 'print("")'. This prevents 'm' from being detected as a variable.
    """
    # Remove double-quoted strings
    line = re.sub(r'"(?:[^"\\]|\\.)*"', '""', line)
    # Remove single-quoted strings
    line = re.sub(r"'(?:[^'\\]|\\.)*'", "''", line)
    return line

def _strip_code_strings(code):
    """Strip string literals from entire multi-line code block."""
    code = re.sub(r'"(?:[^"\\]|\\.)*"', '""', code)
    code = re.sub(r"'(?:[^'\\]|\\.)*'", "''", code)
    return code

# CODE CLEANING UTILITIES
def strip_type_prefix(line, language):
    """
    Remove type declaration keywords to isolate variable names.    
    Example (C): 'int x = 5;' becomes 'x = 5;'
    Example (Java): 'String name = "test";' becomes 'name = "test";'
    """
    line = line.rstrip(';').strip()
    
    if language == "C":
        line = re.sub(r'^(int|float|double|char|void|long|short|unsigned)\s+', '', line)
    elif language == "Java":
        line = re.sub(r'^(int|float|double|char|void|long|short|String|boolean|var)\s+', '', line)
    
    return line

def extract_assignment(line, language):
    """
    Extract variable name and value from assignment statement.    
    Process:
    1. Remove strings (to avoid false matches)
    2. Remove type keywords
    3. Match pattern: variable = value    
    Returns: (var_name, value) or (None, None)
    """
    # Remove strings first
    clean = strip_strings(line)
    clean = strip_type_prefix(clean, language)
    
    # Match assignment (not ==, !=, <=, >=)
    m = re.match(r'^([a-zA-Z_]\w*)\s*=(?!=)\s*(.+)$', clean)
    if m:
        var_name = m.group(1)
        # Get original value (not cleaned version)
        orig = strip_type_prefix(line, language)
        om = re.match(r'^([a-zA-Z_]\w*)\s*=(?!=)\s*(.+)$', orig)
        if om:
            return var_name, om.group(2).strip().rstrip(';')
    
    return None, None

def is_literal(value):
    """
    Check if value is a literal constant.    
    Literal types:
    - Numbers: 42, 3.14, -5, 100L
    - Strings: "hello", 'world'
    - Booleans: true, false, True, False
    - Null: null, None
    """
    v = value.strip()
    
    # Number
    if re.match(r'^-?\d+\.?\d*[fFdDlL]?$', v):
        return True
    
    # String
    if re.match(r'^["\'].*["\']$', v):
        return True
    
    # Boolean/null
    if v.lower() in ('true', 'false', 'null', 'none'):
        return True
    
    return False

# COMPREHENSIVE SYNTAX VALIDATION
def check_syntax_errors(code, language):
    """
    Comprehensive static syntax checker for Python, Java, and C.
    Detects common syntax errors without executing code.    
    Python checks:
    - Missing colons after block statements
    - Python 2 print statements
    - Wrong logical operators (&&, ||)
    - Assignment in conditions (= instead of ==)
    - Indentation errors
    - Unbalanced parentheses/brackets    
    C/Java checks:
    - Missing semicolons
    - Wrong logical operators (and, or)
    - Unbalanced parentheses/brackets/braces    
    Returns: (has_errors: bool, error_list: list)
    """
    errors = []
    lines = code.split('\n')
    code_ns = _strip_code_strings(code)  # String-free version
    
    # ========== PYTHON SYNTAX CHECKS ==========
    if language == "Python":
        block_starters = ('def ', 'class ', 'if ', 'elif ', 'else', 'for ',
                          'while ', 'with ', 'try', 'except', 'finally')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            stripped_ns = strip_strings(stripped)
            
            if not stripped or stripped.startswith('#'):
                continue
            
            # Missing colon after block statement
            if stripped.startswith(block_starters) and not stripped.endswith(':'):
                errors.append(f"Line {i}: Missing ':' after block statement  →  {stripped[:60]}")
            
            # Python 2 print without parentheses
            if re.match(r'^print\s+[^(]', stripped):
                errors.append(f"Line {i}: Python 2 print - use print()  →  {stripped[:60]}")
            
            # C-style logical operators
            if re.search(r'&&|\|\|', stripped_ns):
                errors.append(f"Line {i}: Use 'and'/'or' instead of '&&'/'||'  →  {stripped[:60]}")
            
            # Python 2 not-equal operator
            if '<>' in stripped_ns:
                errors.append(f"Line {i}: Use '!=' instead of '<>'  →  {stripped[:60]}")
            
            # Assignment in condition
            if re.match(r'(?:if|elif|while)\b', stripped):
                cond_ns = re.sub(r'<=|>=|==|!=', '', stripped_ns)
                if re.search(r'(?<![=<>!])=(?!=)', cond_ns):
                    errors.append(f"Line {i}: Possible '=' instead of '==' in condition  →  {stripped[:60]}")
        
        # Check indentation
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if stripped.endswith(':'):
                cur_indent = len(line) - len(line.lstrip())
                for j in range(i + 1, len(lines)):
                    nxt = lines[j]
                    if nxt.strip() and not nxt.strip().startswith('#'):
                        if (len(nxt) - len(nxt.lstrip())) <= cur_indent:
                            errors.append(f"Line {j + 1}: Indentation error - expected indented block after '{stripped[:40]}'")
                        break
        
        # Check balanced parentheses and brackets
        for sym_o, sym_c, name in [('(', ')', 'parenthes'), ('[', ']', 'bracket')]:
            o = code_ns.count(sym_o)
            c = code_ns.count(sym_c)
            if o > c:
                errors.append(f"Unbalanced {name}es: {o} '{sym_o}' but {c} '{sym_c}' - missing closing '{sym_c}'")
            elif c > o:
                errors.append(f"Unbalanced {name}es: {c} '{sym_c}' but {o} '{sym_o}' - extra closing '{sym_c}'")
    
    # ========== C/JAVA SYNTAX CHECKS ==========
    elif language in ('C', 'Java'):
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            stripped_ns = strip_strings(stripped)
            
            if not stripped or stripped.startswith(('#', '//', '/*', '*')):
                continue
            
            # Missing semicolon
            is_control = re.match(
                r'^(if|else|for|while|do|switch|try|catch|finally|'
                r'class|public|private|protected|static|void|#)', stripped
            )
            ends_ok = stripped.endswith(('{', '}', ';', ',', '*/'))
            looks_like = bool(
                re.match(r'^(int|float|double|char|long|short|unsigned|String|boolean|var)\s+\w', stripped) or
                re.match(r'^\w[\w.]*\s*[\(\[=]', stripped) or
                stripped.startswith('return ')
            )
            if looks_like and not is_control and not ends_ok:
                errors.append(f"Line {i}: Possible missing ';'  →  {stripped[:60]}")
            
            # Python-style logical operators
            if re.search(r'\band\b|\bor\b|\bnot\b', stripped_ns):
                errors.append(f"Line {i}: Use '&&'/'||'/'!' instead of 'and'/'or'/'not'  →  {stripped[:60]}")
        
        # Check balanced parentheses, brackets, and braces
        for sym_o, sym_c, name in [('(', ')', 'parenthes'), ('[', ']', 'bracket'), ('{', '}', 'brace')]:
            o = code_ns.count(sym_o)
            c = code_ns.count(sym_c)
            if o > c:
                errors.append(f"Unbalanced {name}es: {o} '{sym_o}' but {c} '{sym_c}' - missing closing '{sym_c}'")
            elif c > o:
                errors.append(f"Unbalanced {name}es: {c} '{sym_c}' but {o} '{sym_o}' - extra closing '{sym_c}'")
    
    return len(errors) > 0, errors

# VARIABLE ANALYSIS MODULE
def analyze_variables(lines, language):
    """
    Two-pass variable analysis:    
    Pass 1: Find all variable assignments
    - Extracts variable name and value
    - Marks literals vs expressions    
    Pass 2: Track variable usage
    - Counts how many times each variable is used
    - Records line numbers of usage
    - Ignores variables inside strings    
    Returns: dict mapping var_name to:
        - line: declaration line number
        - value: assigned value
        - used_in: list of line numbers where used
        - is_literal: boolean flag
    """
    var_info = {}
    
    # Pass 1: Find assignments
    for line_num, line in enumerate(lines):
        var_name, value = extract_assignment(line, language)
        if var_name and value:
            var_info[var_name] = {
                'line': line_num,
                'value': value,
                'used_in': [],
                'is_literal': is_literal(value)
            }
    
    # Pass 2: Find usages
    for line_num, line in enumerate(lines):
        clean = strip_strings(line)  # Remove strings
        for var in var_info:
            pattern = r'\b' + re.escape(var) + r'\b'
            if re.search(pattern, clean) and line_num != var_info[var]['line']:
                var_info[var]['used_in'].append(line_num)
    
    return var_info

def find_redundant_variables(var_info):
    """
    Identify redundant variables:    
    Unused: Declared but never used
    Single-use: Used exactly once AND contains expression    
    Rules:
    - Never flag literals as redundant
    - Only inline expressions (with operators)
    - Don't inline simple variable references    
    Returns: (unused: list, single_use: list)
    """
    unused = []
    single_use = []
    
    for var, info in var_info.items():
        count = len(info['used_in'])
        
        # Skip literals
        if info['is_literal']:
            continue
        
        # Unused variable
        if count == 0:
            unused.append(var)
        
        # Single-use expression
        elif not info['is_literal'] and count == 1 and re.search(r'[\+\-\*/%\(\)]', info['value']):
            single_use.append(var)
    
    return unused, single_use

# CODE TRANSFORMATION MODULE
def remove_unused_variables(lines, var_info, unused, language):
    """
    Comment out unused variable declarations.
    Preserves original indentation.
    Uses language-appropriate comment syntax.
    """
    sym = "//" if language in ("C", "Java") else "#"
    for var in unused:
        n = var_info[var]['line']
        raw = lines[n].rstrip()
        indent = len(raw) - len(raw.lstrip())
        lines[n] = raw[:indent] + f"{sym} [UNUSED] {raw.lstrip()}"

def inline_single_use_variables(lines, var_info, single_use, language):
    """
    Inline single-use variables at their usage site.    
    Process:
    1. Find usage line
    2. Replace variable with (expression)
    3. Comment out declaration    
    Returns: List of inlined variable names
    """
    sym = "//" if language in ("C", "Java") else "#"
    inlined = []
    
    for var in single_use:
        info = var_info[var]
        decl = info['line']
        use = info['used_in'][0]
        value = info['value']
        pattern = r'\b' + re.escape(var) + r'\b'
        
        # Replace at usage site
        lines[use] = re.sub(pattern, f"({value})", lines[use])
        
        # Comment out declaration
        lines[decl] = f"{sym} [INLINED] {lines[decl].rstrip()}"
        inlined.append(var)
    
    return inlined

def rename_unclear_variables(lines, var_info, language):
    """
    Rename single-letter variables to descriptive names.    
    Rules:
    - Only rename single letters
    - Never rename i, j, k, n, m (common iterators)
    - Never rename loop variables (detected by for-loop check)
    - Rename format: x → x_value    
    Returns: List of (old_name, new_name) tuples
    """
    always_keep = {'i', 'j', 'k', 'n', 'm'}
    renamed = []
    
    for var in list(var_info.keys()):
        if len(var) != 1 or var.lower() in always_keep:
            continue
        
        # Check if used in for-loop
        used_as_loop_var = any(
            re.match(r'for\s*[\(\s]', line.strip()) and
            re.search(r'\b' + re.escape(var) + r'\b', line)
            for line in lines
        )
        if used_as_loop_var:
            continue
        
        # Rename
        new_name = f"{var}_value"
        pattern = r'\b' + re.escape(var) + r'\b'
        for idx in range(len(lines)):
            lines[idx] = re.sub(pattern, new_name, lines[idx])
        renamed.append((var, new_name))
    
    return renamed

# FORMATTING IMPROVEMENT
def _space_assignment_toplevel(s):
    """
    Add spaces around '=' only at top level (depth 0).
    Preserves keyword arguments like: function(x=5)    
    Algorithm:
    - Track nesting depth with parentheses/brackets
    - Only add spaces when depth = 0
    - Skip compound operators (==, !=, <=, >=)
    """
    result = []
    depth = 0
    i = 0
    
    while i < len(s):
        c = s[i]
        
        # Track depth
        if c in '([{':
            depth += 1
            result.append(c)
        elif c in ')]}':
            depth -= 1
            result.append(c)
        elif c == '=' and depth == 0:
            # Check for compound operators
            prev = s[i - 1] if i > 0 else ''
            nxt = s[i + 1] if i + 1 < len(s) else ''
            
            if prev not in '=<>!' and nxt != '=':
                # Add spaces around =
                while result and result[-1] == ' ':
                    result.pop()
                result.append(' = ')
                i += 1
                while i < len(s) and s[i] == ' ':
                    i += 1
                continue
            else:
                result.append(c)
        else:
            result.append(c)
        i += 1
    
    return ''.join(result)

def improve_formatting(lines, language):
    """
    Improve operator spacing and formatting.    
    Rules:
    - Space around = (only top-level, not in keyword args)
    - Space around arithmetic operators (+, -, *, /, %)
    - Space around comparison operators (<, >)
    - String contents never modified
    - Collapse multiple spaces    
    Returns: List of formatted lines
    """
    formatted = []
    
    for line in lines:
        stripped = line.strip()
        
        # Skip blank lines and comments
        if not stripped or stripped.startswith(('#', '//', '/*', '*')):
            formatted.append(line)
            continue
        
        indent = len(line) - len(line.lstrip())
        prefix = line[:indent]
        content = line[indent:]
        
        # Save string literals
        saved = []
        def _save(m):
            saved.append(m.group(0))
            return f"\x00STR{len(saved) - 1}\x00"
        safe = re.sub(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', _save, content)
        
        # Space around = (top-level only)
        safe = _space_assignment_toplevel(safe)
        
        # Space around arithmetic operators
        safe = re.sub(r'(?<![+\-*/<>=!])([+\-*/%])(?![+\-*/<>=])', r' \1 ', safe)
        
        # Space around < and >
        safe = re.sub(r'(?<![<>=!])<(?![<=])', ' < ', safe)
        safe = re.sub(r'(?<![<>=!])>(?![>=])', ' > ', safe)
        
        # Collapse multiple spaces
        safe = re.sub(r'  +', ' ', safe).strip()
        
        # Restore strings
        for idx, s in enumerate(saved):
            safe = safe.replace(f"\x00STR{idx}\x00", s)
        
        formatted.append(prefix + safe)
    
    return formatted

# CONTEXT-AWARE COMMENT INJECTION
def add_comments(lines, language):
    """
    Add beginner-friendly inline comments to code.    
    Features:
    - Context-aware (mentions variable/function names)
    - Never double-comments
    - Skips blank lines and existing comments
    - Uses appropriate syntax (# for Python, // for C/Java)    
    Comment categories:
    - Functions/methods
    - Classes
    - Imports/includes
    - Output statements (with variable names)
    - Input statements
    - Conditionals (with condition)
    - Loops (with details)
    - Returns
    - Assignments (computed vs simple)    
    Returns: List of commented lines
    """
    commented = []
    sym = "#" if language == "Python" else "//"
    
    for line in lines:
        stripped = line.strip()
        
        # Skip blank, comments, and braces
        if (not stripped or
                stripped.startswith(('#', '//', '/*', '*')) or
                stripped in ('{', '}')):
            commented.append(line)
            continue
        
        # Skip if already commented
        safe_check = strip_strings(stripped)
        if '#' in safe_check or '//' in safe_check:
            commented.append(line)
            continue
        
        note = None
        
        # Main function
        if re.match(r'(int main\s*\(|public static void main)', stripped):
            note = "Program entry point"
        
        # Function definition
        elif re.match(r'def |void |public .*(void|int|String|bool)', stripped):
            m = re.match(r'def (\w+)', stripped) or re.match(r'\w[\w\s]*\s+(\w+)\s*\(', stripped)
            note = f"Define '{m.group(1)}' function" if m else "Function definition"
        
        # Class
        elif stripped.startswith('class '):
            m = re.match(r'class (\w+)', stripped)
            note = f"Define '{m.group(1)}' class" if m else "Class definition"
        
        # Import
        elif re.match(r'import (\S+)', stripped):
            m = re.match(r'import (\S+)', stripped)
            note = f"Import '{m.group(1)}' module"
        elif re.match(r'from (\S+) import', stripped):
            m = re.match(r'from (\S+) import', stripped)
            note = f"Import from '{m.group(1)}'"
        
        # Include
        elif re.match(r'#include\s*[<"](.+?)[>"]', stripped):
            m = re.match(r'#include\s*[<"](.+?)[>"]', stripped)
            note = f"Include {m.group(1)}"
        
        # Output
        elif re.search(r'\b(print|printf|cout|System\.out\.print)\b', stripped):
            safe_line = strip_strings(stripped)
            skip = {'print', 'printf', 'cout', 'println', 'System', 'out', 'end', 'sep', 'f'}
            vars_used = [v for v in re.findall(r'\b([a-z_]\w*)\b', safe_line) if v not in skip]
            note = f"Display {', '.join(vars_used[:2])}" if vars_used else "Print output"
        
        # Input
        elif re.search(r'\b(input\(|scanf|cin)\b', stripped):
            note = "Read input from user"
        
        # Return
        elif stripped.startswith('return '):
            ret = stripped[7:].strip().rstrip(';')
            note = f"Return {ret}" if len(ret) <= 20 else "Return computed result"
        
        # If/elif
        elif re.match(r'(if|elif)\s*[\(\s]', stripped):
            m = re.match(r'(?:if|elif)\s*\(?(.*?)\)?\s*(?::|$)', stripped)
            cond = m.group(1).strip().rstrip(':').rstrip(')') if m else ''
            note = f"Check: {cond[:35]}" if cond else "Conditional check"
        
        # Else
        elif re.match(r'else\s*[:{]?$', stripped) or stripped == 'else:':
            note = "Otherwise"
        
        # For loop
        elif re.match(r'for\s*[\(\s]', stripped):
            r_match = re.search(r'range\((\d+)\)', stripped)
            note = f"Repeat {r_match.group(1)} times" if r_match else "Iterate over items"
        
        # While loop
        elif re.match(r'while\s*[\(\s]', stripped):
            m = re.match(r'while\s*\(?(.*?)\)?\s*(?::|{)?\s*$', stripped)
            cond = m.group(1).strip().rstrip(')').rstrip(':') if m else ''
            note = ("Loop until break" if cond in ('true', 'True', '1')
                    else (f"While {cond[:25]}" if cond else "While loop"))
        
        # Computed assignment
        elif '=' in stripped and '==' not in stripped:
            m = re.match(
                r'(?:(?:int|float|double|char|String|boolean|var)\s+)?'
                r'([a-zA-Z_]\w*)\s*=(?!=)\s*(.+)', stripped
            )
            if m:
                var = m.group(1)
                rhs = m.group(2).strip().rstrip(';')
                if re.search(r'[\+\-\*/%\(\)]', rhs):
                    note = f"Compute {var}"
        
        # Add comment
        if note:
            commented.append(f"{line}  {sym} {note}")
        else:
            commented.append(line)
    
    return commented

# QUALITY SCORING MODULE
def calculate_score(original_code, language, issues, syntax_errors):
    """
    Calculate quality score (0-100) based on issues found.    
    Deductions:
    - Syntax errors: -15
    - No comments: -10
    - Unused variables: -10
    - Inlined variables: -5
    - Renamed variables: -5
    - Formatting: -5
    - Each syntax fix type: variable (depends on fix)    
    Minimum score: 40
    Maximum score: 100    
    Returns: (score: int, feedback: list)
    """
    score = 100
    feedback = []
    
    # Syntax errors
    if syntax_errors:
        score -= 15
        feedback.append(f"Syntax issues detected: {len(syntax_errors)} potential problem(s)")
    
    # No comments
    if '#' not in original_code and '//' not in original_code:
        score -= 10
        feedback.append("No comments found - added beginner-friendly comments")
    
    # Unused variables
    if issues['unused']:
        score -= 10
        feedback.append(f"Removed {len(issues['unused'])} unused variable(s)")
    
    # Inlined variables
    if issues['inlined']:
        score -= 5
        feedback.append(f"Inlined {len(issues['inlined'])} single-use temporary variable(s)")
    
    # Renamed variables
    if issues['renamed']:
        score -= 5
        feedback.append(f"Renamed {len(issues['renamed'])} unclear single-letter variable(s)")
    
    # Formatting
    if issues['formatting_improved']:
        score -= 5
        feedback.append("Fixed operator spacing and formatting")
    
    # Syntax auto-fixes
    sfx = issues.get('syntax_fixes', {})
    fix_messages = {
        'print': lambda n: f"Converted {n} Python 2 print statement(s) to print()",
        'logical_ops': lambda n: f"Replaced {n} wrong logical operator(s) (&&/|| ↔ and/or)",
        'not_equal': lambda n: f"Replaced {n} '<>' with '!='",
        'colon': lambda n: f"Added missing ':' to {n} block statement(s)",
        'indent': lambda n: f"Fixed indentation on {n} line(s) after block statement",
        'parens': lambda n: f"Closed {n} unclosed parenthesis/parentheses",
        'brackets': lambda n: f"Closed {n} unclosed bracket(s)",
        'braces': lambda n: f"Closed {n} unclosed brace(s)",
        'semicolon': lambda n: f"Added missing ';' to {n} statement(s)",
    }
    
    for key, msg_fn in fix_messages.items():
        n = sfx.get(key, 0)
        if n > 0:
            feedback.append(msg_fn(n))
    
    # Clamp score
    score = max(40, min(100, score))
    
    if not feedback:
        feedback.append("Code quality looks solid - no major issues detected.")
    
    return score, feedback

# SYNTAX AUTO-FIXING MODULE
def _safe_transform(line, fn):
    """
    Apply transformation to line while protecting string contents.
    Strings are replaced with placeholders during transformation,
    then restored afterward.
    """
    saved = []
    def _save(m):
        saved.append(m.group(0))
        return f"\x00S{len(saved) - 1}\x00"
    safe = re.sub(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', _save, line)
    safe = fn(safe)
    for idx, s in enumerate(saved):
        safe = safe.replace(f"\x00S{idx}\x00", s)
    return safe

def fix_python_errors(lines):
    """
    Auto-fix Python syntax errors.    
    Fixes applied (in order):
    1. print x → print(x)
    2. && / || → and / or
    3. <> → !=
    4. Missing colons after if/for/while/def/class
    5. Indentation after block statements
    6. Unclosed parentheses
    7. Unclosed brackets    
    Returns: (fixed_lines, fixes_dict)
    """
    fixed = list(lines)
    fx = {
        'print': 0,
        'logical_ops': 0,
        'not_equal': 0,
        'colon': 0,
        'indent': 0,
        'parens': 0,
        'brackets': 0,
    }
    
    # 1. Python 2 print
    for i, line in enumerate(fixed):
        m = re.match(r'^(\s*)print\s+(?!\()(.+)$', line)
        if m:
            fixed[i] = f"{m.group(1)}print({m.group(2).strip()})"
            fx['print'] += 1
    
    # 2. Logical operators
    for i, line in enumerate(fixed):
        ns = strip_strings(line)
        if '&&' in ns or '||' in ns:
            fixed[i] = _safe_transform(
                fixed[i],
                lambda s: s.replace('&&', 'and').replace('||', 'or')
            )
            fx['logical_ops'] += 1
    
    # 3. Not-equal
    for i, line in enumerate(fixed):
        if '<>' in strip_strings(line):
            fixed[i] = _safe_transform(fixed[i], lambda s: s.replace('<>', '!='))
            fx['not_equal'] += 1
    
    # 4. Missing colons
    block_starters = ('def ', 'class ', 'if ', 'elif ', 'else', 'for ',
                      'while ', 'with ', 'try', 'except', 'finally')
    for i, line in enumerate(fixed):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped.startswith(block_starters) and not stripped.endswith(':'):
            fixed[i] = line.rstrip() + ':'
            fx['colon'] += 1
    
    # 5. Indentation
    for i, line in enumerate(fixed):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped.endswith(':'):
            cur_indent = len(line) - len(line.lstrip())
            for j in range(i + 1, len(fixed)):
                nxt = fixed[j]
                if nxt.strip() and not nxt.strip().startswith('#'):
                    if (len(nxt) - len(nxt.lstrip())) <= cur_indent:
                        fixed[j] = '    ' + nxt
                        fx['indent'] += 1
                    break
    
    # 6. Unclosed parentheses
    for i, line in enumerate(fixed):
        ns = strip_strings(line)
        diff = ns.count('(') - ns.count(')')
        if diff > 0:
            fixed[i] = line.rstrip() + ')' * diff
            fx['parens'] += 1
    
    # 7. Unclosed brackets
    for i, line in enumerate(fixed):
        ns = strip_strings(line)
        diff = ns.count('[') - ns.count(']')
        if diff > 0:
            fixed[i] = line.rstrip() + ']' * diff
            fx['brackets'] += 1
    
    return fixed, fx

def fix_c_java_errors(lines, language):
    """
    Auto-fix C/Java syntax errors.    
    Fixes applied (in order):
    1. and/or/not → &&/||/!
    2. Missing semicolons
    3. Unclosed parentheses
    4. Unclosed brackets
    5. Unclosed braces (file-level)    
    Returns: (fixed_lines, fixes_dict)
    """
    fixed = list(lines)
    fx = {
        'logical_ops': 0,
        'semicolon': 0,
        'parens': 0,
        'brackets': 0,
        'braces': 0,
    }
    
    # 1. Logical operators
    for i, line in enumerate(fixed):
        ns = strip_strings(line)
        if re.search(r'\band\b|\bor\b|\bnot\b', ns):
            def _fix_ops(s):
                s = re.sub(r'\band\b', '&&', s)
                s = re.sub(r'\bor\b', '||', s)
                s = re.sub(r'\bnot\b\s*', '!', s)
                return s
            fixed[i] = _safe_transform(fixed[i], _fix_ops)
            fx['logical_ops'] += 1
    
    # 2. Missing semicolons
    for i, line in enumerate(fixed):
        stripped = line.strip()
        if not stripped or stripped.startswith(('#', '//', '/*', '*')):
            continue
        is_control = re.match(
            r'^(if|else|for|while|do|switch|try|catch|finally|'
            r'class|public|private|protected|static|void|#)', stripped
        )
        ends_ok = stripped.endswith(('{', '}', ';', ',', '*/'))
        looks_like = bool(
            re.match(r'^(int|float|double|char|long|short|unsigned|String|boolean|var)\s+\w', stripped) or
            re.match(r'^\w[\w.]*\s*[\(\[=]', stripped) or
            stripped.startswith('return ')
        )
        if looks_like and not is_control and not ends_ok:
            fixed[i] = line.rstrip() + ';'
            fx['semicolon'] += 1
    
    # 3. Unclosed parentheses
    for i, line in enumerate(fixed):
        ns = strip_strings(line)
        diff = ns.count('(') - ns.count(')')
        if diff > 0:
            fixed[i] = line.rstrip() + ')' * diff
            fx['parens'] += 1
    
    # 4. Unclosed brackets
    for i, line in enumerate(fixed):
        ns = strip_strings(line)
        diff = ns.count('[') - ns.count(']')
        if diff > 0:
            fixed[i] = line.rstrip() + ']' * diff
            fx['brackets'] += 1
    
    # 5. Unclosed braces (file-level)
    all_code_ns = _strip_code_strings('\n'.join(fixed))
    brace_diff = all_code_ns.count('{') - all_code_ns.count('}')
    if brace_diff > 0:
        fixed.extend(['}'] * brace_diff)
        fx['braces'] += brace_diff
    
    return fixed, fx

# MAIN REFINEMENT PIPELINE
def refine_code(code, language):
    """
    Main code refinement pipeline.    
    Steps (in order):
    1. Check syntax (on original code)
    2. Auto-fix syntax errors
    3. Analyze variables
    4. Remove unused variables
    5. Inline single-use variables
    6. Rename unclear variables
    7. Improve formatting
    8. Add comments
    9. Calculate score    
    Returns: (refined_code, score, feedback, syntax_errors)
    """
    # Check original code for errors
    has_errors, syntax_errors = check_syntax_errors(code, language)
    
    lines = code.split('\n')
    original_code = code
    
    issues = {
        'unused': [],
        'inlined': [],
        'renamed': [],
        'formatting_improved': False,
        'syntax_fixes': {}
    }
    
    # Step 1: Auto-fix syntax
    if language == "Python":
        lines, issues['syntax_fixes'] = fix_python_errors(lines)
    elif language in ("C", "Java"):
        lines, issues['syntax_fixes'] = fix_c_java_errors(lines, language)
    
    # Step 2: Variable analysis
    var_info = analyze_variables(lines, language)
    unused, single_use = find_redundant_variables(var_info)
    
    if unused:
        remove_unused_variables(lines, var_info, unused, language)
        issues['unused'] = unused
    
    if single_use:
        issues['inlined'] = inline_single_use_variables(lines, var_info, single_use, language)
    
    renamed = rename_unclear_variables(lines, var_info, language)
    if renamed:
        issues['renamed'] = renamed
    
    # Step 3: Formatting
    formatted = improve_formatting(lines, language)
    if formatted != lines:
        issues['formatting_improved'] = True
    lines = formatted
    
    # Step 4: Comments
    lines = add_comments(lines, language)
    
    # Step 5: Score
    refined_code = '\n'.join(lines)
    score, feedback = calculate_score(original_code, language, issues, syntax_errors)
    
    return refined_code, score, feedback, syntax_errors

# ADMIN PANEL
def show_admin_panel(history):
    """
    Display admin statistics dashboard.
    Shows persistent analysis history grouped by date.
    """
    print("\n" + "=" * 70)
    print(" " * 27 + "ADMIN PANEL")
    print("=" * 70)
    
    if not history:
        print("  No analyses on record yet.")
        print("=" * 70)
        return
    
    total = len(history)
    avg_score = sum(e['score'] for e in history) / total
    last = history[-1]
    
    print(f"  Total Analyses  : {total}")
    print(f"  Average Score   : {avg_score:.1f} / 100")
    print(f"  Last Entry      : {last['language']}  Score {last['score']}/100"
          f"  [{last['timestamp']}]")
    
    print("\n" + "-" * 70)
    print("  Full History  (newest date first, newest entry first within each day)")
    print("-" * 70)
    
    # Group by date
    by_date = defaultdict(list)
    for entry in history:
        day = entry['timestamp'].split(' ')[0]
        by_date[day].append(entry)
    
    for day in sorted(by_date.keys(), reverse=True):
        print(f"\n  ── {day} ──")
        for entry in reversed(by_date[day]):
            time = entry['timestamp'].split(' ')[1]
            lang = entry['language'].ljust(8)
            sc = entry['score']
            iss = entry['issues']
            grade = ("Excellent" if sc >= 80 else "Good" if sc >= 60 else "Needs Work").ljust(13)
            print(f"    {time}  {lang}  Score: {sc:3}/100  {grade}  Issues found: {iss}")
    
    print("\n" + "=" * 70)

# USER INTERFACE
def print_banner():
    """Display welcome banner"""
    print("\n" + "=" * 70)
    print(" " * 22 + "CODE REFINE v2.0")
    print(" " * 17 + "Multi-Language Code Analyzer")
    print("=" * 70)
    print("  Supported: Python | Java | C")
    print("=" * 70)

def get_mode():
    """Get user/admin mode selection"""
    print("\n" + "-" * 70)
    print("  Select Mode:")
    print("    [1] User Mode  - Analyze and refine code")
    print("    [2] Admin Mode - View analysis history and statistics")
    print("-" * 70)
    choice = input("  Enter choice (1/2): ").strip()
    return "admin" if choice == "2" else "user"

def verify_admin():
    """Verify admin password"""
    print("\n  Admin Authentication")
    password = input("  Password: ").strip()
    return password == ADMIN_PASSWORD

def collect_code():
    """Collect multi-line code input"""
    print("\n" + "-" * 70)
    print("  Paste your code below.")
    print("  Type  END  on a new line when finished:")
    print("-" * 70)
    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        except EOFError:
            break
    return '\n'.join(lines)

def display_results(refined_code, score, feedback, syntax_errors, language):
    """Display analysis results"""
    print("\n" + "=" * 70)
    print(" " * 24 + "ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\n  Language Detected: {language}")
    
    # Syntax errors
    if syntax_errors:
        print("\n" + "-" * 70)
        print("  POTENTIAL SYNTAX ISSUES:")
        print("-" * 70)
        for err in syntax_errors:
            print(f"    !  {err}")
    
    # Refined code
    print("\n" + "-" * 70)
    print("  REFINED CODE:")
    print("-" * 70)
    print(refined_code)
    
    # Score
    print("\n" + "-" * 70)
    print("  QUALITY SCORE:")
    print("-" * 70)
    
    bar_len = 50
    filled = int((score / 100) * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    grade = "Excellent" if score >= 80 else "Good" if score >= 60 else "Needs Improvement"
    
    print(f"\n  Score : {score} / 100")
    print(f"  [{bar}]")
    print(f"  Grade : {grade}\n")
    
    # Feedback
    print("-" * 70)
    print("  FEEDBACK:")
    print("-" * 70)
    for item in feedback:
        print(f"    -  {item}")
    print()

def print_disclaimer():
    """Display disclaimer"""
    print("\n" + "=" * 70)
    print(" " * 28 + "DISCLAIMER")
    print("=" * 70)
    print("  CodeRefine performs static analysis only.")
    print("  It does NOT execute code or guarantee runtime correctness.")
    print("=" * 70)

# MAIN PROGRAM
def main():
    """Main program entry point"""
    
    # Load persistent history from database
    history = load_history()
    
    print_banner()
    mode = get_mode()
    
    # Admin mode
    if mode == "admin":
        if verify_admin():
            show_admin_panel(history)
        else:
            print("\n  Incorrect password. Access denied.")
        return
    
    # User mode
    while True:
        print("\n" + "=" * 70)
        print(" " * 27 + "CODE ANALYSIS")
        print("=" * 70)
        
        code = collect_code()
        if not code.strip():
            print("\n  No code entered. Exiting.")
            break
        
        language = detect_language(code)
        print(f"\n  Analyzing {language} code...")
        
        refined_code, score, feedback, syntax_errors = refine_code(code, language)
        display_results(refined_code, score, feedback, syntax_errors, language)
        
        # Save to database
        save_entry({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'language': language,
            'score': score,
            'issues': len(feedback)
        })
        
        print("-" * 70)
        again = input("  Analyze another snippet? (yes/no): ").strip().lower()
        if again not in ('yes', 'y'):
            break
    
    print("\n" + "=" * 70)
    print(" " * 19 + "Thank you for using CodeRefine!")
    print("=" * 70)
    print_disclaimer()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Goodbye.")