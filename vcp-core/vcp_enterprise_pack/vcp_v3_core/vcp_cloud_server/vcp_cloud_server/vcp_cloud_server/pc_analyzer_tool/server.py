import http.server
import socketserver
import json
import os
import sys
import ctypes
import platform
import subprocess

PORT = 8502

def get_disk_info():
    """WindowsのDrive C: のディスク使用量を直接取得"""
    try:
        free_bytes = ctypes.c_ulonglong(0)
        total_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p("C:\\"),
            None,
            ctypes.byref(total_bytes),
            ctypes.byref(free_bytes)
        )
        total_gb = round(total_bytes.value / (1024**3), 2)
        free_gb = round(free_bytes.value / (1024**3), 2)
        used_gb = round(total_gb - free_gb, 2)
        used_pct = round((used_gb / total_gb) * 100, 1) if total_gb > 0 else 0
        return {"total_gb": total_gb, "used_gb": used_gb, "free_gb": free_gb, "used_pct": used_pct}
    except Exception:
        return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "used_pct": 0}

def get_process_count():
    """実行中プロセスの個数を取得"""
    try:
        output = subprocess.check_output("tasklist", shell=True).decode('oem', errors='ignore')
        lines = output.strip().split('\n')
        return max(0, len(lines) - 3)
    except Exception:
        return 0

def find_large_files(target_dir, limit=10):
    """指定ディレクトリ内の大容量ファイルを検出"""
    files_list = []
    try:
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                try:
                    filepath = os.path.join(root, file)
                    size = os.path.getsize(filepath)
                    files_list.append({
                        "name": file,
                        "path": filepath,
                        "size_mb": round(size / (1024 * 1024), 2)
                    })
                except Exception:
                    continue
                if len(files_list) > 300: # 応答速度維持のため検索上限を設定
                    break
            if len(files_list) > 300:
                break
    except Exception:
        pass
    files_list.sort(key=lambda x: x["size_mb"], reverse=True)
    return files_list[:limit]

class AnalyzerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            
            disk = get_disk_info()
            procs = get_process_count()
            user_home = os.path.expanduser("~")
            large_files = find_large_files(os.path.join(user_home, "Downloads"), limit=8)
            
            payload = {
                "system": f"{platform.system()} {platform.release()}",
                "disk": disk,
                "process_count": procs,
                "user_home": user_home,
                "large_files": large_files
            }
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            
        elif self.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="UTF-8">
                <title>PC ローカル解析ツール [PROTOTYPE]</title>
                <style>
                    body { font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 24px; }
                    .container { max-width: 900px; margin: 0 auto; }
                    .banner { background: #854d0e; color: #fef08a; padding: 10px 16px; border-radius: 8px; font-weight: bold; margin-bottom: 20px; font-size: 14px; }
                    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
                    .card { background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 20px; }
                    h2 { font-size: 16px; color: #38bdf8; margin-top: 0; margin-bottom: 12px; }
                    .metric { font-size: 32px; font-weight: bold; color: #f8fafc; }
                    .sub { font-size: 13px; color: #94a3b8; margin-top: 4px; }
                    .progress-bg { background: #334155; height: 12px; border-radius: 6px; overflow: hidden; margin-top: 12px; }
                    .progress-fill { background: #0284c7; height: 100%; width: 0%; transition: width 0.5s ease; }
                    table { width: 100%; border-collapse: collapse; margin-top: 8px; }
                    th, td { padding: 10px; text-align: left; font-size: 13px; border-bottom: 1px solid #334155; }
                    th { color: #94a3b8; font-weight: 600; }
                    .path-cell { word-break: break-all; font-family: monospace; font-size: 11px; color: #94a3b8; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="banner">⚠️ 動作状態：ローカルPC解析プロトタイプ v1.0（手元のPC実データを直接取得中）</div>
                    
                    <div class="grid">
                        <div class="card">
                            <h2>Cドライブ空き容量 (実データ)</h2>
                            <div class="metric"><span id="used-gb">-</span> GB / <span id="total-gb">-</span> GB</div>
                            <div class="sub">使用率: <span id="used-pct">-</span>% (空き: <span id="free-gb">-</span> GB)</div>
                            <div class="progress-bg"><div class="progress-fill" id="bar"></div></div>
                        </div>
                        <div class="card">
                            <h2>システム＆プロセス状態</h2>
                            <div class="metric"><span id="procs">-</span> <span style="font-size:16px;">個のプロセス</span></div>
                            <div class="sub">OS: <span id="os-info">-</span></div>
                            <div class="sub" style="margin-top:8px;">対象パス: <span id="home-dir">-</span></div>
                        </div>
                    </div>

                    <div class="card">
                        <h2>Downloads フォルダー内の大容量ファイル TOP 8</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>ファイル名</th>
                                    <th>サイズ</th>
                                    <th>フルパス</th>
                                </tr>
                            </thead>
                            <tbody id="files-list">
                                <tr><td colspan="3">解析中...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <script>
                    async function loadData() {
                        try {
                            const res = await fetch('/api/data');
                            const data = await res.json();
                            
                            document.getElementById('used-gb').innerText = data.disk.used_gb;
                            document.getElementById('total-gb').innerText = data.disk.total_gb;
                            document.getElementById('free-gb').innerText = data.disk.free_gb;
                            document.getElementById('used-pct').innerText = data.disk.used_pct;
                            document.getElementById('bar').style.width = data.disk.used_pct + '%';
                            
                            document.getElementById('procs').innerText = data.process_count;
                            document.getElementById('os-info').innerText = data.system;
                            document.getElementById('home-dir').innerText = data.user_home;

                            const tbody = document.getElementById('files-list');
                            if (data.large_files.length === 0) {
                                tbody.innerHTML = '<tr><td colspan="3">大きなファイルは見つかりませんでした。</td></tr>';
                            } else {
                                tbody.innerHTML = data.large_files.map(f => `
                                    <tr>
                                        <td style="font-weight:bold; color:#f1f5f9;">${f.name}</td>
                                        <td style="color:#38bdf8; font-weight:bold;">${f.size_mb} MB</td>
                                        <td class="path-cell">${f.path}</td>
                                    </tr>
                                `).join('');
                            }
                        } catch(e) {
                            console.error(e);
                        }
                    }
                    loadData();
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))

print(f"⚡ 解析ツールプロトタイプ起動: http://localhost:{PORT}")
with socketserver.TCPServer(("", PORT), AnalyzerHandler) as httpd:
    httpd.serve_forever()
