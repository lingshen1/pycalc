# CLI Calculator for Embedded Linux (Luckfox)

A robust, multi-mode terminal calculator built specifically for embedded Linux systems (like Luckfox Lyra) running standard Python and the `rich` library.

---

## Key Features

* **Four Modes:** Standard, Scientific, Programmer, and ASCII Graphing.
* **Zero Heavy Dependencies:** Uses only Python's standard libraries (`math`, `sys`) and `rich` for formatting.
* **Auto-Scaling ASCII Graphs:** Plots mathematical functions of $x$ directly in the terminal with dynamic Y-axis scaling.
* **Programmer Base Conversions:** Real-time translation between Decimal, Hexadecimal, Octal, and Binary.
* **Context-Aware Help:** Press `?` in any mode to view a dedicated help guide.
* **Memory Support:** Use the keyword `ans` to reference the previous result.

---

## Requirements

* Python 3.8+
* `rich` module (pre-installed on standard Luckfox image)

---

## How to Run

```bash
python3 calc.py
```

---

## Global Commands

| Command / Key | Action |
| :--- | :--- |
| **`?`** | Toggle context-aware help screen for the active mode |
| **`M`** | Cycle through calculator modes (Standard → Scientific → Programmer → Graph) |
| **`C`** | Clear history, reset memory, and return to default state |
| **`Q` / `Exit`** | Quit the calculator application |
| **`ans`** | Use the previous calculation result inside any expression |

---

## Mode Details

### 1. Standard Mode
Handles standard arithmetic operations using Python syntax:
* **Operators:** `+`, `-`, `*`, `/`, `**` (exponent), `//` (integer division), `%` (modulo)
* *Example:* `(15 + 25) / 2`

### 2. Scientific Mode
Unlocks Python's full built-in `math` library for advanced computations:
* **Functions & Constants:** `sin()`, `cos()`, `tan()`, `sqrt()`, `log()`, `pi`, `e`, `tau`
* *Example:* `sqrt(256) + sin(pi / 2)`

### 3. Programmer Mode
Designed for bitwise logic and base conversions:
* **Operators:** `&` (AND), `|` (OR), `^` (XOR), `~` (NOT), `<<` (Left Shift), `>>` (Right Shift)
* **Base Inputs:** Supports Hex (`0xFF`), Binary (`0b1010`), and Octal (`0o77`)
* **Breakdown:** Automatically outputs DEC, HEX, OCT, and BIN representations for integer results.

### 4. Graph Mode
Plots functions of $x$ using character-based plots with automatic range scaling:
* **Domain:** Fixed standard domain $x \in [-10, 10]$
* **Range:** Automatically calculates and fits the Y-axis boundaries based on evaluated function output values.
* *Examples:* 
  * `sin(x)`
  * `x**2 - 4`
  * `cos(x) * x`
