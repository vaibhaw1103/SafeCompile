# SafeCompile 🔐

**SafeCompile** is a compiler design project that performs lexical analysis, syntax analysis, 
and static rule-based vulnerability detection in C code.

---

## 📌 Features

- **Lexical Analyzer**: Tokenizes C code into keywords, identifiers, operators, etc.
- **Syntax Analyzer**: Parses C code for valid function declarations, assignments, and returns.
- **Static Rule Engine**: Detects security vulnerabilities such as:
  - Use of unsafe functions: `gets()`, `strcpy()`, `sprintf()`, etc.
  - Format string risks: `scanf("%s")`, `%n` usage
  - Hardcoded passwords
  - Unchecked `malloc()` returns
  - Command injection via `system()`
  - Usage of `eval()`

---

## ✅ How to Use

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/SafeCompile.git
   cd SafeCompile
   ```

2. Open `SafeCompile.ipynb` in **Jupyter Notebook** or **JupyterLab**.

3. Paste your C code in the provided input cell.

4. Run all cells to see token stream, parse structure, and vulnerability warnings.

---

## 📂 Project Structure

```
SafeCompile/
├── SafeCompile.ipynb         # Main notebook with lexer, parser, and rule engine
├── README.md                 # Project overview and usage instructions
```

---

## 👨‍💻 Team

- [Your Name] (Team Leader)
- [Member 2 Name]
- [Member 3 Name]
- [Member 4 Name]

> A B.Tech 3rd Year project submitted under Compiler Design subject.

---

## 📚 Technologies Used

- Python 3.x
- Jupyter Notebook
- Regex for lexical analysis

---

## 🛡️ Why This Project?

Secure coding is critical in modern software. This project addresses the gap between learning compilers and real-world code quality issues by identifying vulnerabilities during compilation, not post-deployment.