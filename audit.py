import os
import ast
import glob

def get_imports(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except Exception as e:
            return None, str(e)
            
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports, None

def main():
    root_dir = r"d:\study\lets do it\Project\seaBorgProject"
    
    # 1. Folder structure (already done via tree, but let's list it anyway)
    print("--- 1. Folder Structure Summary ---")
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if '.git' in dirpath or '__pycache__' in dirpath or '.gemini' in dirpath:
            continue
        rel_path = os.path.relpath(dirpath, root_dir)
        py_files = [f for f in filenames if f.endswith('.py')]
        if py_files:
            print(f"{rel_path}: {len(py_files)} python files")

    # 2. Python files audit
    print("\n--- 2. Python Files Audit ---")
    py_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        if '.git' in dirpath or '__pycache__' in dirpath or '.gemini' in dirpath:
            continue
        for f in filenames:
            if f.endswith('.py'):
                py_files.append(os.path.join(dirpath, f))
    
    all_imports = set()
    errors = []
    for f in py_files:
        imports, err = get_imports(f)
        rel_path = os.path.relpath(f, root_dir)
        if err:
            errors.append(f"{rel_path}: AST Parse Error: {err}")
        else:
            all_imports.update(imports)
    
    if errors:
        print("Errors in Python files:")
        for err in errors:
            print(err)
    else:
        print("All python files parsed successfully.")
    
    print("All unique imported modules:")
    print(", ".join(sorted(all_imports)))

    # 3. Check .env
    print("\n--- 3. Check .env ---")
    env_path = os.path.join(root_dir, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            content = f.read()
            print(".env found. Contains GROQ_API_KEY:", "GROQ_API_KEY" in content)
            print(".env found. Contains DATABASE_URL:", "DATABASE_URL" in content)
    else:
        print(".env NOT FOUND.")

    # 4. Check data/processed/
    print("\n--- 4. Check data/processed/argo.parquet ---")
    parquet_path = os.path.join(root_dir, 'data', 'processed', 'argo.parquet')
    if os.path.exists(parquet_path):
        try:
            import pandas as pd
            df = pd.read_parquet(parquet_path)
            print(f"argo.parquet exists. Rows: {len(df)}")
        except Exception as e:
            print(f"Error reading argo.parquet: {e}")
    else:
        print("argo.parquet NOT FOUND.")

    # 5. Check indexes/
    print("\n--- 5. Check indexes/argo.faiss ---")
    faiss_path = os.path.join(root_dir, 'indexes', 'argo.faiss')
    if os.path.exists(faiss_path):
        size = os.path.getsize(faiss_path)
        print(f"argo.faiss exists. Size: {size} bytes")
    else:
        print("argo.faiss NOT FOUND.")

    # 6. Check data/raw/
    print("\n--- 6. Check data/raw/ ---")
    raw_dir = os.path.join(root_dir, 'data', 'raw')
    if os.path.exists(raw_dir):
        nc_files = glob.glob(os.path.join(raw_dir, '*.nc'))
        print(f"Found {len(nc_files)} .nc files in data/raw/")
    else:
        print("data/raw/ NOT FOUND.")

if __name__ == "__main__":
    main()
