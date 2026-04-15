# AI Code Mentor — Knowledge Base
# Sources: PEP 8, OWASP Top 10 for LLMs 2025, SOLID Principles (arXiv 2025)

---

## Section 1: PEP 8 — Python Style Guidelines

### Naming Conventions
- **Function names** must be `lowercase_with_underscores`. Never use `camelCase` or `PascalCase` for functions.
- **Variable names** must be `lowercase_with_underscores`. Names like `UserData`, `MyVar` are PEP 8 violations.
- **Class names** must use `PascalCase` (CapWords). Examples: `MyClass`, `DataProcessor`.
- **Constants** must be `ALL_CAPS_WITH_UNDERSCORES`. Example: `MAX_SIZE = 100`.
- **Private attributes** should be prefixed with a single underscore: `_private_var`.
- Avoid single-character variable names except for short loop counters (`i`, `j`, `x`).

### Whitespace Rules
- Surround top-level function and class definitions with **two blank lines**.
- Separate method definitions inside a class with **one blank line**.
- Do not use spaces around the `=` sign in keyword arguments: `func(key=value)` not `func(key = value)`.
- Do not use spaces immediately inside parentheses, brackets, or braces: `func(x, y)` not `func( x, y )`.
- Add a single space on both sides of binary operators: `x = a + b`, not `x=a+b`.
- Do not have trailing whitespace at end of lines.

### Imports
- Imports should be at the **top of the file**, after module docstrings.
- Import **one module per line**: `import os` and `import sys` on separate lines.
- Avoid wildcard imports (`from module import *`) as they pollute the namespace.
- Group imports in this order: (1) Standard Library, (2) Third-Party, (3) Local.

### Comments and Docstrings
- Write docstrings for all public modules, functions, classes, and methods.
- Use triple double-quotes for docstrings: `"""This is a docstring."""`
- Inline comments should be separated from the code by at least two spaces.
- Do not write obvious comments. Comment only non-obvious logic.

### Line Length
- Limit all lines to a maximum of **79 characters**.
- For long expressions, use Python's implied line continuation inside brackets, parentheses, or braces.

### Boolean Comparisons
- Never compare with `True`/`False`/`None` using `==`. Use `is` or `is not`.
- Bad: `if UserData != None:` — Good: `if user_data is not None:` or just `if user_data:`
- Bad: `if flag == True:` — Good: `if flag:`

---

## Section 2: Security Best Practices (OWASP)

### Injection Vulnerabilities
- **CRITICAL — eval():** Never use `eval()` or `exec()` on user-provided input. This allows Remote Code Execution (RCE) — an attacker can run any system command. Use `ast.literal_eval()` for safe parsing of literals.
- **CRITICAL — SQL Injection:** Never use string formatting to build SQL queries: `cursor.execute("SELECT * FROM users WHERE id = " + user_id)`. Always use parameterized queries: `cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))`.
- **CRITICAL — Path Traversal:** Never use raw user input as a file path. Validate paths with `os.path.abspath()` and ensure they stay within an allowed directory.
- **CRITICAL — Command Injection:** Never use `subprocess.run(shell=True)` with user input. Always pass commands as lists: `subprocess.run(["ls", user_dir])`.

### Hardcoded Credentials
- **CRITICAL — Hardcoded Secrets:** Never hardcode API keys, passwords, tokens, or database connection strings directly in source code. Examples of violating patterns: `api_key = "sk_live_..."`, `password = "mySecret123"`.
- Store secrets using environment variables (`os.environ.get('API_KEY')`) or secret management tools.
- Use regex to detect common secret patterns: keys starting with `sk_live_`, `ghp_`, `eyJ`, `AKIA`.

### Cryptography
- Never use weak hashing algorithms like `MD5` or `SHA1` for password storage.
- Use `bcrypt`, `argon2`, or `hashlib.sha256()` minimum.
- Never roll your own encryption library.

### Input Validation
- Always validate and sanitize all external inputs (user forms, API responses, file contents).
- Use allow-lists, not deny-lists.
- Validate data types, formats (email, URL), and length limits.

---

## Section 3: SOLID Design Principles & Clean Code

### Single Responsibility Principle (SRP)
- A function or class should have **one job and one reason to change**.
- **Warning:** Functions longer than 30 lines that perform multiple, unrelated tasks violate SRP. Split them into smaller, focused functions.
- **Warning:** Cyclomatic complexity (deeply nested `if/elif/else` chains with more than 3 levels) is a strong indicator of SRP violation. Extract sub-logic into helper functions.
- Example of violation: A single function that validates user input, queries a database, sends an email, and writes a log.

### Open/Closed Principle (OCP)
- Code should be open for extension, but closed for modification.
- Avoid using `if/elif` chains to check object types: use polymorphism and base classes instead.
- Prefer adding new classes or functions over modifying existing ones.

### Don't Repeat Yourself (DRY)
- **Warning:** Identical or near-identical code blocks appearing more than once should be extracted into a reusable function.
- Duplicated error-handling logic, validation, or formatting code is a DRY violation.

### Resource Management
- **CRITICAL — File Handles:** Always use the `with open(path) as f:` context manager when reading or writing files. Never use bare `open()` without a corresponding `close()`, as this causes resource leaks and file corruption.
- **CRITICAL — Database Connections:** Always close database connections in a `finally` block or use a context manager.

### Monolithic Functions (Complexity)
- **Warning:** Functions with more than 5 `if`, `elif`, or nested `for/while` blocks are considered highly complex.
- High cyclomatic complexity makes testing impossible and bugs hidden. Refactor by extracting branches into clearly named helper functions.
- Example of violation: a single function handling user authentication, authorization, profile updates, and email notifications all in one block.

### Error Handling
- **CRITICAL — Bare Except:** Never use a bare `except:` clause. It catches ALL exceptions, including system-exiting `SystemExit` and `KeyboardInterrupt`, hiding real bugs. Always specify the exception: `except ValueError:` or `except Exception as e:`.
- Always log or re-raise exceptions. Never silently swallow errors with a bare `pass` inside `except`.
- Use `finally` to ensure cleanup code (closing files, releasing locks) always runs.
