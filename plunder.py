import os

# --- CONFIGURATION ---
# Add the folder names you want to skip here
IGNORE_DIRS = {'.git', 'node_modules', 'venv', '__pycache__', 'dist', 'build', '.idea', '.vscode'}
# Add the file extensions you want to capture
INCLUDE_EXTS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.json', '.md', '.java', '.c', '.cpp', '.h', '.sql'}
# Output filename
OUTPUT_FILE = 'full_project_context.txt'

def bundle_files():
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out_f:
        # Walk through the directory
        for root, dirs, files in os.walk('.'):
            # Modify dirs in-place to skip ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in INCLUDE_EXTS:
                    file_path = os.path.join(root, file)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as in_f:
                            content = in_f.read()
                            
                            # Write a clearly defined separator and filename
                            out_f.write(f"\n{'='*50}\n")
                            out_f.write(f"FILE_PATH: {file_path}\n")
                            out_f.write(f"{'='*50}\n\n")
                            out_f.write(content)
                            out_f.write("\n")
                            print(f"Added: {file_path}")
                    except Exception as e:
                        print(f"Skipping {file_path} due to error: {e}")

    print(f"\nDone! All code bundled into: {OUTPUT_FILE}")

if __name__ == '__main__':
    bundle_files()