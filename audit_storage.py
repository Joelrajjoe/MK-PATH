import os

def check_dir(path):
    if not os.path.exists(path): return 0
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                try:
                    total += os.path.getsize(fp)
                except:
                    pass
    return total

print(f"E:/MKPATH: {check_dir('E:/MKPATH')}")
print(f"E:/MKPATH/.venv: {check_dir('E:/MKPATH/.venv')}")
print(f"E:/MKPATH/data: {check_dir('E:/MKPATH/data')}")
print(f"E:/MKPATH/models: {check_dir('E:/MKPATH/models')}")
print(f"E:/MKPATH/artifacts: {check_dir('E:/MKPATH/artifacts')}")
print(f"E:/MKPATH/logs: {check_dir('E:/MKPATH/logs')}")
print(f"E:/MKPATH/temp: {check_dir('E:/MKPATH/temp')}")
print(f"C:/Users/joelr/.cache/huggingface: {check_dir('C:/Users/joelr/.cache/huggingface')}")
print(f"C:/Users/joelr/AppData/Local/pip/cache: {check_dir('C:/Users/joelr/AppData/Local/pip/cache')}")
print(f"C:/Users/joelr/AppData/Local/npm-cache: {check_dir('C:/Users/joelr/AppData/Local/npm-cache')}")
