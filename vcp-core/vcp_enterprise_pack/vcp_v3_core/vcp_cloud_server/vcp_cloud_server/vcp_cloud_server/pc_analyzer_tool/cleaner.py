import os
import sys

def scan_downloads():
    target = os.path.expanduser("~/Downloads")
    print(f"\n🔍 対象フォルダ: {target}\n" + "="*50)
    
    if not os.path.exists(target):
        print("フォルダが見つかりません。")
        return

    large_files = []
    empty_dirs = []

    for root, dirs, files in os.walk(target):
        if not dirs and not files:
            empty_dirs.append(root)
        for f in files:
            fp = os.path.join(root, f)
            try:
                size = os.path.getsize(fp)
                if size > 100 * 1024 * 1024:  # 100MB以上
                    large_files.append((fp, size / (1024*1024)))
            except Exception:
                pass

    print(f"📦 100MB以上の大容量ファイル ({len(large_files)}件):")
    large_files.sort(key=lambda x: x[1], reverse=True)
    for path, size in large_files[:10]:
        print(f" - [{size:.1f} MB] {path}")

    print(f"\n📂 空のフォルダ ({len(empty_dirs)}件):")
    for ed in empty_dirs[:10]:
        print(f" - {ed}")

    print("\n" + "="*50)
    print("※ 検出のみ行いました。ファイルの自動削除は行いません。")

if __name__ == "__main__":
    scan_downloads()
