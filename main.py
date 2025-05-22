# main.py

from analyze import analyze_code
import sys

if len(sys.argv) != 2:
    print("Usage: python main.py <source-file.c>")
    sys.exit(1)

filename = sys.argv[1]

try:
    with open(filename, 'r') as f:
        your_code_string = f.read()
except FileNotFoundError:
    print(f"❌ File '{filename}' not found.")
    sys.exit(1)

# Run the analyzer
result = analyze_code(your_code_string)

# Display results
print(result)
